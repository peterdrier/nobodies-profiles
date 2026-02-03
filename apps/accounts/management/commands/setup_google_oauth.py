"""
Management command to set up Google OAuth from environment variables.

Usage:
    python manage.py setup_google_oauth

This command will:
1. Ensure the default Site is configured correctly
2. Create or update the Google SocialApp with credentials from environment
"""
import os

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError

from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = 'Set up Google OAuth from environment variables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            default='localhost:8000',
            help='Site domain (default: localhost:8000)',
        )
        parser.add_argument(
            '--name',
            default='Nobodies Profiles',
            help='Site display name (default: Nobodies Profiles)',
        )

    def handle(self, *args, **options):
        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')

        if not client_id or not client_secret:
            raise CommandError(
                'GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set in environment'
            )

        domain = options['domain']
        name = options['name']

        # Update or create the Site
        site, created = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={'domain': domain, 'name': name}
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'{action} Site: {site.domain}')

        # Create or update the Google SocialApp
        app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': client_secret,
            }
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'{action} Google SocialApp')

        # Link the app to the site
        if site not in app.sites.all():
            app.sites.add(site)
            self.stdout.write(f'Linked Google SocialApp to {site.domain}')

        self.stdout.write(self.style.SUCCESS('Google OAuth setup complete!'))
        self.stdout.write(f'Client ID: {client_id[:20]}...')
