"""
Service for syncing legal documents from GitHub.

Documents are synced from the nobodies-collective/legal repository.
Expected repo structure:

    legal/
    ├── privacy-policy/
    │   ├── metadata.json
    │   ├── es.md          # Spanish (canonical)
    │   └── en.md          # English translation
    ├── code-of-conduct/
    │   ├── metadata.json
    │   ├── es.md
    │   └── en.md
    └── ...

metadata.json format:
{
    "title": "Privacy Policy",
    "type": "PRIVACY_POLICY",
    "version": "1.0",
    "effective_date": "2026-01-01",
    "requires_re_consent": false,
    "re_consent_deadline": null,
    "description": "...",
    "required_for_roles": [],
    "changelog": "Initial version"
}
"""
import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

import httpx
from django.conf import settings
from django.utils import timezone

from .models import (
    DocumentTranslation,
    DocumentType,
    DocumentVersion,
    LegalDocument,
)

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


@dataclass
class DocumentMetadata:
    """Parsed document metadata."""
    title: str
    type: str
    version: str
    effective_date: date
    requires_re_consent: bool = False
    re_consent_deadline: Optional[date] = None
    description: str = ""
    required_for_roles: list = None
    changelog: str = ""

    def __post_init__(self):
        if self.required_for_roles is None:
            self.required_for_roles = []


class GitHubSyncService:
    """
    Service for syncing legal documents from GitHub.

    Uses GitHub's REST API to fetch repository contents.
    """

    def __init__(self, repo: str = None, branch: str = None, token: str = None):
        self.repo = repo or settings.LEGAL_DOCS_REPO
        self.branch = branch or settings.LEGAL_DOCS_BRANCH
        self.token = token or settings.GITHUB_TOKEN

        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, url: str) -> dict:
        """Make a GET request to the GitHub API."""
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def _get_file_content(self, path: str) -> str:
        """Get the content of a file from the repository."""
        url = f"{GITHUB_API_BASE}/repos/{self.repo}/contents/{path}?ref={self.branch}"
        data = self._get(url)

        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")

        return data.get("content", "")

    def _get_directory_contents(self, path: str = "") -> list:
        """Get the contents of a directory from the repository."""
        url = f"{GITHUB_API_BASE}/repos/{self.repo}/contents/{path}?ref={self.branch}"
        return self._get(url)

    def _get_latest_commit_sha(self) -> str:
        """Get the SHA of the latest commit on the branch."""
        url = f"{GITHUB_API_BASE}/repos/{self.repo}/commits/{self.branch}"
        data = self._get(url)
        return data.get("sha", "")

    def sync_all_documents(self, created_by=None) -> dict:
        """
        Sync all documents from the repository.

        Returns a summary of what was synced.
        """
        summary = {
            "created": [],
            "updated": [],
            "unchanged": [],
            "errors": [],
        }

        try:
            commit_sha = self._get_latest_commit_sha()
            contents = self._get_directory_contents()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch repo contents: {e}")
            summary["errors"].append(f"Failed to fetch repository: {e}")
            return summary

        for item in contents:
            if item["type"] != "dir":
                continue

            doc_slug = item["name"]
            try:
                result = self.sync_document(doc_slug, commit_sha, created_by)
                if result == "created":
                    summary["created"].append(doc_slug)
                elif result == "updated":
                    summary["updated"].append(doc_slug)
                else:
                    summary["unchanged"].append(doc_slug)
            except Exception as e:
                logger.error(f"Failed to sync document {doc_slug}: {e}")
                summary["errors"].append(f"{doc_slug}: {e}")

        return summary

    def sync_document(self, slug: str, commit_sha: str = None, created_by=None) -> str:
        """
        Sync a single document from the repository.

        Returns: 'created', 'updated', or 'unchanged'
        """
        if not commit_sha:
            commit_sha = self._get_latest_commit_sha()

        # Get metadata
        try:
            metadata_json = self._get_file_content(f"{slug}/metadata.json")
            metadata_dict = json.loads(metadata_json)
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            logger.warning(f"No valid metadata.json for {slug}: {e}")
            return "unchanged"

        metadata = self._parse_metadata(metadata_dict)

        # Get Spanish content (required)
        try:
            spanish_content = self._get_file_content(f"{slug}/es.md")
        except httpx.HTTPError:
            logger.error(f"No Spanish content for {slug}")
            return "unchanged"

        content_hash = hashlib.sha256(spanish_content.encode("utf-8")).hexdigest()

        # Get or create LegalDocument
        document, doc_created = LegalDocument.objects.get_or_create(
            slug=slug,
            defaults={
                "title": metadata.title,
                "document_type": metadata.type,
                "description": metadata.description,
                "required_for_roles": metadata.required_for_roles,
            }
        )

        if not doc_created:
            # Update existing document metadata
            document.title = metadata.title
            document.description = metadata.description
            document.required_for_roles = metadata.required_for_roles
            document.save()

        # Check if this version already exists
        existing_version = DocumentVersion.objects.filter(
            document=document,
            version_number=metadata.version,
        ).first()

        if existing_version:
            # Check if content changed
            if existing_version.content_hash == content_hash:
                return "unchanged"

            # Content changed - this shouldn't happen for the same version
            logger.warning(
                f"Content changed for {slug} v{metadata.version} without version bump"
            )
            return "unchanged"

        # Create new version
        version = DocumentVersion.objects.create(
            document=document,
            version_number=metadata.version,
            effective_date=metadata.effective_date,
            spanish_content=spanish_content,
            content_hash=content_hash,
            git_commit_sha=commit_sha,
            git_file_path=f"{slug}/es.md",
            synced_at=timezone.now(),
            requires_re_consent=metadata.requires_re_consent,
            re_consent_deadline=metadata.re_consent_deadline,
            changelog=metadata.changelog,
            created_by=created_by,
            is_current=True,  # New versions are current by default
        )

        # Sync translations
        self._sync_translations(slug, version)

        return "created" if doc_created else "updated"

    def _sync_translations(self, slug: str, version: DocumentVersion):
        """Sync translations for a document version."""
        translation_codes = ["en", "fr", "de", "pt"]

        for lang_code in translation_codes:
            try:
                content = self._get_file_content(f"{slug}/{lang_code}.md")
                DocumentTranslation.objects.update_or_create(
                    document_version=version,
                    language_code=lang_code,
                    defaults={
                        "content": content,
                        "is_machine_translated": False,  # Assume human translated in repo
                    }
                )
            except httpx.HTTPError:
                # Translation doesn't exist - that's OK
                pass

    def _parse_metadata(self, data: dict) -> DocumentMetadata:
        """Parse metadata dictionary into DocumentMetadata."""
        effective_date = data.get("effective_date")
        if isinstance(effective_date, str):
            effective_date = date.fromisoformat(effective_date)

        re_consent_deadline = data.get("re_consent_deadline")
        if isinstance(re_consent_deadline, str):
            re_consent_deadline = date.fromisoformat(re_consent_deadline)

        doc_type = data.get("type", "OTHER")
        if doc_type not in DocumentType.values:
            doc_type = DocumentType.OTHER

        return DocumentMetadata(
            title=data.get("title", "Untitled"),
            type=doc_type,
            version=data.get("version", "1.0"),
            effective_date=effective_date or date.today(),
            requires_re_consent=data.get("requires_re_consent", False),
            re_consent_deadline=re_consent_deadline,
            description=data.get("description", ""),
            required_for_roles=data.get("required_for_roles", []),
            changelog=data.get("changelog", ""),
        )


def sync_legal_documents(created_by=None) -> dict:
    """
    Convenience function to sync all legal documents.

    Can be called from management commands or Celery tasks.
    """
    service = GitHubSyncService()
    return service.sync_all_documents(created_by=created_by)
