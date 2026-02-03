"""
Management command to sync legal documents from GitHub.

Usage:
    python manage.py sync_legal_documents
    python manage.py sync_legal_documents --repo nobodies-collective/legal
    python manage.py sync_legal_documents --document privacy-policy
"""
from django.core.management.base import BaseCommand, CommandError

from apps.documents.services import GitHubSyncService


class Command(BaseCommand):
    help = 'Sync legal documents from GitHub repository'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repo',
            help='GitHub repository (owner/repo format)',
        )
        parser.add_argument(
            '--branch',
            default='main',
            help='Branch to sync from (default: main)',
        )
        parser.add_argument(
            '--document',
            help='Sync only a specific document by slug',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )

    def handle(self, *args, **options):
        repo = options.get('repo')
        branch = options.get('branch')
        document = options.get('document')
        dry_run = options.get('dry_run')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run mode - no changes will be made'))

        service = GitHubSyncService(
            repo=repo,
            branch=branch,
        )

        self.stdout.write(f"Syncing from {service.repo} ({service.branch})")

        if document:
            # Sync single document
            try:
                if not dry_run:
                    result = service.sync_document(document)
                    self.stdout.write(f"  {document}: {result}")
                else:
                    self.stdout.write(f"  Would sync: {document}")
            except Exception as e:
                raise CommandError(f"Failed to sync {document}: {e}")
        else:
            # Sync all documents
            try:
                if not dry_run:
                    summary = service.sync_all_documents()
                else:
                    # Just list what's available
                    contents = service._get_directory_contents()
                    summary = {
                        'created': [],
                        'updated': [],
                        'unchanged': [
                            item['name'] for item in contents
                            if item['type'] == 'dir'
                        ],
                        'errors': [],
                    }

                if summary['created']:
                    self.stdout.write(self.style.SUCCESS(
                        f"Created: {', '.join(summary['created'])}"
                    ))
                if summary['updated']:
                    self.stdout.write(self.style.SUCCESS(
                        f"Updated: {', '.join(summary['updated'])}"
                    ))
                if summary['unchanged']:
                    self.stdout.write(
                        f"Unchanged: {', '.join(summary['unchanged'])}"
                    )
                if summary['errors']:
                    for error in summary['errors']:
                        self.stdout.write(self.style.ERROR(f"Error: {error}"))

            except Exception as e:
                raise CommandError(f"Sync failed: {e}")

        self.stdout.write(self.style.SUCCESS('Sync complete'))
