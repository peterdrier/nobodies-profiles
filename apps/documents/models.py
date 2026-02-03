"""
Legal document models for consent tracking.

Documents are synced from the nobodies-collective/legal GitHub repository.
Spanish content is legally binding; translations are for reference only.

CRITICAL: ConsentRecord is IMMUTABLE - never update or delete these records.
"""
import hashlib

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.members.models import Profile, Role


class DocumentType(models.TextChoices):
    """Types of legal documents."""
    PRIVACY_POLICY = 'PRIVACY_POLICY', _('Privacy Policy')
    GDPR_DATA_PROCESSING = 'GDPR_DATA_PROCESSING', _('GDPR Data Processing Agreement')
    CONFIDENTIALITY = 'CONFIDENTIALITY', _('Confidentiality Commitment')
    CODE_OF_CONDUCT = 'CODE_OF_CONDUCT', _('Code of Conduct')
    INTERNAL_REGULATIONS = 'INTERNAL_REGULATIONS', _('Internal Regulations')
    OTHER = 'OTHER', _('Other')


class LegalDocument(models.Model):
    """
    A type of legal document (e.g., Privacy Policy, Code of Conduct).

    Each document can have multiple versions over time.
    """
    slug = models.SlugField(
        _('slug'),
        unique=True,
        help_text=_('URL-friendly identifier (e.g., "privacy-policy")'),
    )
    title = models.CharField(
        _('title'),
        max_length=255,
        help_text=_('Display name of the document'),
    )
    document_type = models.CharField(
        _('document type'),
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Brief description of what this document covers'),
    )
    is_required_for_activation = models.BooleanField(
        _('required for activation'),
        default=True,
        help_text=_('Must be signed before membership becomes ACTIVE'),
    )
    required_for_roles = models.JSONField(
        _('required for roles'),
        default=list,
        blank=True,
        help_text=_('List of roles that must sign this document (empty = all roles)'),
    )
    display_order = models.PositiveIntegerField(
        _('display order'),
        default=0,
        help_text=_('Order in which documents are displayed'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Whether this document is currently in use'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('legal document')
        verbose_name_plural = _('legal documents')
        ordering = ['display_order', 'title']

    def __str__(self):
        return self.title

    @property
    def current_version(self):
        """Get the current active version of this document."""
        return self.versions.filter(is_current=True).first()

    def is_required_for_role(self, role: str) -> bool:
        """Check if this document is required for a given role."""
        if not self.required_for_roles:
            return True  # Empty list means required for all
        return role in self.required_for_roles


class DocumentVersion(models.Model):
    """
    A specific version of a legal document.

    Spanish content is the legally binding text.
    Content is synced from the nobodies-collective/legal GitHub repository.
    """
    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name=_('document'),
    )
    version_number = models.CharField(
        _('version number'),
        max_length=20,
        help_text=_('Semantic version (e.g., "1.0", "2.1")'),
    )
    effective_date = models.DateField(
        _('effective date'),
        help_text=_('Date this version becomes effective'),
    )

    # Content (Spanish is legally binding)
    spanish_content = models.TextField(
        _('Spanish content'),
        help_text=_('The legally binding Spanish text (Markdown or HTML)'),
    )
    content_hash = models.CharField(
        _('content hash'),
        max_length=64,
        help_text=_('SHA-256 hash of spanish_content for integrity verification'),
    )

    # Git provenance
    git_commit_sha = models.CharField(
        _('git commit SHA'),
        max_length=40,
        blank=True,
        help_text=_('Git commit from which this version was synced'),
    )
    git_file_path = models.CharField(
        _('git file path'),
        max_length=255,
        blank=True,
        help_text=_('Path to the file in the legal repo'),
    )
    synced_at = models.DateTimeField(
        _('synced at'),
        null=True,
        blank=True,
        help_text=_('When this version was last synced from git'),
    )

    # Re-consent settings
    requires_re_consent = models.BooleanField(
        _('requires re-consent'),
        default=False,
        help_text=_('If True, existing consents to previous versions are invalidated'),
    )
    re_consent_deadline = models.DateField(
        _('re-consent deadline'),
        null=True,
        blank=True,
        help_text=_('Deadline for members to re-consent to this version'),
    )

    # Metadata
    changelog = models.TextField(
        _('changelog'),
        blank=True,
        help_text=_('Summary of changes from the previous version'),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_document_versions',
        verbose_name=_('created by'),
    )
    is_current = models.BooleanField(
        _('is current version'),
        default=False,
        help_text=_('Only one version per document should be current'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('document version')
        verbose_name_plural = _('document versions')
        ordering = ['-effective_date', '-version_number']
        unique_together = ['document', 'version_number']

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"

    def save(self, *args, **kwargs):
        # Auto-compute content hash if not provided
        if self.spanish_content and not self.content_hash:
            self.content_hash = self.compute_hash()

        # If marking as current, unmark other versions
        if self.is_current:
            DocumentVersion.objects.filter(
                document=self.document,
                is_current=True
            ).exclude(pk=self.pk).update(is_current=False)

        super().save(*args, **kwargs)

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the Spanish content."""
        return hashlib.sha256(self.spanish_content.encode('utf-8')).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify that the content hasn't been tampered with."""
        return self.compute_hash() == self.content_hash


class DocumentTranslation(models.Model):
    """
    Non-binding reference translation of a document version.

    These are provided for convenience but the Spanish version is always legally binding.
    """
    LANGUAGE_CHOICES = [
        ('en', _('English')),
        ('fr', _('French')),
        ('de', _('German')),
        ('pt', _('Portuguese')),
    ]

    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        related_name='translations',
        verbose_name=_('document version'),
    )
    language_code = models.CharField(
        _('language code'),
        max_length=5,
        choices=LANGUAGE_CHOICES,
    )
    content = models.TextField(
        _('translated content'),
        help_text=_('Reference translation (non-binding)'),
    )
    is_machine_translated = models.BooleanField(
        _('machine translated'),
        default=True,
        help_text=_('Whether this was machine-translated'),
    )
    translator_notes = models.TextField(
        _('translator notes'),
        blank=True,
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('document translation')
        verbose_name_plural = _('document translations')
        unique_together = ['document_version', 'language_code']

    def __str__(self):
        return f"{self.document_version} ({self.get_language_code_display()})"


class ConsentRecord(models.Model):
    """
    Immutable record of a person's consent to a document version.

    CRITICAL: This model is APPEND-ONLY. Never update or delete these records.
    Revocations create separate ConsentRevocation records.
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='consents',
        verbose_name=_('profile'),
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.PROTECT,  # Never delete versions with consents
        related_name='consents',
        verbose_name=_('document version'),
    )
    consented_at = models.DateTimeField(
        _('consented at'),
        auto_now_add=True,
    )
    ip_address = models.GenericIPAddressField(
        _('IP address'),
    )
    user_agent = models.TextField(
        _('user agent'),
    )
    consent_text_shown = models.TextField(
        _('consent text shown'),
        help_text=_('The exact text of the "I agree" statement that was displayed'),
    )
    language_viewed = models.CharField(
        _('language viewed'),
        max_length=5,
        help_text=_('Which language version the user viewed'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('False if superseded by new version consent or revoked'),
    )

    class Meta:
        verbose_name = _('consent record')
        verbose_name_plural = _('consent records')
        ordering = ['-consented_at']
        indexes = [
            models.Index(fields=['profile', 'is_active']),
            models.Index(fields=['document_version', 'is_active']),
        ]

    def __str__(self):
        return f"{self.profile} consented to {self.document_version}"

    def save(self, *args, **kwargs):
        # Prevent updates to existing records (append-only)
        if self.pk:
            # Only allow is_active to be changed (for superseding)
            allowed_fields = kwargs.get('update_fields')
            if allowed_fields and set(allowed_fields) <= {'is_active'}:
                super().save(*args, **kwargs)
                return
            raise ValueError("ConsentRecord is immutable. Only is_active can be updated.")
        super().save(*args, **kwargs)


class ConsentRevocation(models.Model):
    """
    Records when and why a consent was revoked.

    Revocations are separate from ConsentRecord to maintain immutability.
    """
    consent_record = models.OneToOneField(
        ConsentRecord,
        on_delete=models.PROTECT,
        related_name='revocation',
        verbose_name=_('consent record'),
    )
    revoked_at = models.DateTimeField(
        _('revoked at'),
        auto_now_add=True,
    )
    reason = models.TextField(
        _('reason'),
        help_text=_('Reason for revocation'),
    )
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='consent_revocations',
        verbose_name=_('revoked by'),
        help_text=_('User who revoked (self or admin)'),
    )

    class Meta:
        verbose_name = _('consent revocation')
        verbose_name_plural = _('consent revocations')

    def __str__(self):
        return f"Revocation of {self.consent_record}"

    def save(self, *args, **kwargs):
        # When creating a revocation, mark the consent as inactive
        if not self.pk:
            self.consent_record.is_active = False
            self.consent_record.save(update_fields=['is_active'])
        super().save(*args, **kwargs)


# Helper functions for consent checking

def get_required_documents_for_profile(profile: Profile) -> list:
    """
    Get all documents that a profile must consent to.

    Based on the profile's current role and document requirements.
    """
    role = profile.current_role
    if not role:
        return []

    documents = LegalDocument.objects.filter(
        is_active=True,
        is_required_for_activation=True,
    )

    required = []
    for doc in documents:
        if doc.is_required_for_role(role):
            required.append(doc)

    return required


def get_pending_documents_for_profile(profile: Profile) -> list:
    """
    Get documents that a profile needs to consent to.

    Returns documents where the profile either:
    - Has no consent to the current version
    - Has an inactive consent (superseded or revoked)
    """
    required_docs = get_required_documents_for_profile(profile)
    pending = []

    for doc in required_docs:
        current_version = doc.current_version
        if not current_version:
            continue

        # Check for active consent to current version
        has_consent = ConsentRecord.objects.filter(
            profile=profile,
            document_version=current_version,
            is_active=True,
        ).exists()

        if not has_consent:
            pending.append({
                'document': doc,
                'version': current_version,
            })

    return pending


def has_all_required_consents(profile: Profile) -> bool:
    """Check if a profile has all required active consents."""
    return len(get_pending_documents_for_profile(profile)) == 0


def has_overdue_reconsent(profile: Profile) -> bool:
    """Check if a profile has any overdue re-consent deadlines."""
    pending = get_pending_documents_for_profile(profile)
    today = timezone.now().date()

    for item in pending:
        version = item['version']
        if version.requires_re_consent and version.re_consent_deadline:
            if version.re_consent_deadline < today:
                return True

    return False
