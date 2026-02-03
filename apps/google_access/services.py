"""
Google Drive API service for permission management.

Handles granting and revoking access to Google Drive resources.
"""
import json
import logging
import time
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class GoogleDriveError(Exception):
    """Base exception for Google Drive operations."""
    pass


class RateLimitError(GoogleDriveError):
    """Raised when Google API rate limit is hit."""
    pass


class GoogleDriveService:
    """
    Service for managing Google Drive permissions.

    Uses a service account with domain-wide delegation to manage
    permissions on behalf of the organization.
    """

    def __init__(self):
        self._service = None
        self._credentials = None

    def _get_credentials(self):
        """Get Google service account credentials."""
        if self._credentials:
            return self._credentials

        from google.oauth2 import service_account

        # Get credentials from environment
        creds_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        if not creds_json:
            raise GoogleDriveError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

        try:
            creds_info = json.loads(creds_json)
        except json.JSONDecodeError as e:
            raise GoogleDriveError(f"Invalid service account JSON: {e}")

        scopes = ['https://www.googleapis.com/auth/drive']
        self._credentials = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=scopes,
        )
        return self._credentials

    def _get_service(self):
        """Get or create the Drive API service."""
        if self._service:
            return self._service

        from googleapiclient.discovery import build

        credentials = self._get_credentials()
        self._service = build('drive', 'v3', credentials=credentials)
        return self._service

    def grant_permission(
        self,
        resource_id: str,
        email: str,
        role: str,
        send_notification: bool = False,
    ) -> dict[str, Any]:
        """
        Grant permission to a Google Drive resource.

        Args:
            resource_id: Google Drive resource ID
            email: Email address to grant access to
            role: Permission role (reader, commenter, writer, etc.)
            send_notification: Whether to send email notification

        Returns:
            dict with permission_id and details

        Raises:
            GoogleDriveError: If the operation fails
            RateLimitError: If rate limited by Google
        """
        service = self._get_service()

        permission_body = {
            'type': 'user',
            'role': role,
            'emailAddress': email,
        }

        try:
            result = service.permissions().create(
                fileId=resource_id,
                body=permission_body,
                sendNotificationEmail=send_notification,
                supportsAllDrives=True,  # Required for Shared Drives
                fields='id,emailAddress,role',
            ).execute()

            logger.info(
                f"Granted {role} access to {email} on resource {resource_id}. "
                f"Permission ID: {result['id']}"
            )

            return {
                'permission_id': result['id'],
                'email': result['emailAddress'],
                'role': result['role'],
            }

        except Exception as e:
            error_str = str(e)
            if 'Rate Limit Exceeded' in error_str or 'rateLimitExceeded' in error_str:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            if 'userRateLimitExceeded' in error_str:
                raise RateLimitError(f"User rate limit exceeded: {e}")
            raise GoogleDriveError(f"Failed to grant permission: {e}")

    def revoke_permission(
        self,
        resource_id: str,
        permission_id: str,
    ) -> bool:
        """
        Revoke a permission from a Google Drive resource.

        Args:
            resource_id: Google Drive resource ID
            permission_id: Permission ID to revoke

        Returns:
            True if successful

        Raises:
            GoogleDriveError: If the operation fails
            RateLimitError: If rate limited by Google
        """
        service = self._get_service()

        try:
            service.permissions().delete(
                fileId=resource_id,
                permissionId=permission_id,
                supportsAllDrives=True,
            ).execute()

            logger.info(
                f"Revoked permission {permission_id} from resource {resource_id}"
            )
            return True

        except Exception as e:
            error_str = str(e)
            if 'Rate Limit Exceeded' in error_str or 'rateLimitExceeded' in error_str:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            if 'userRateLimitExceeded' in error_str:
                raise RateLimitError(f"User rate limit exceeded: {e}")
            if 'notFound' in error_str or '404' in error_str:
                # Permission already revoked
                logger.warning(
                    f"Permission {permission_id} not found on resource {resource_id} "
                    "(may have been already revoked)"
                )
                return True
            raise GoogleDriveError(f"Failed to revoke permission: {e}")

    def list_permissions(
        self,
        resource_id: str,
    ) -> list[dict[str, Any]]:
        """
        List all permissions on a resource.

        Args:
            resource_id: Google Drive resource ID

        Returns:
            List of permission dicts with id, email, role

        Raises:
            GoogleDriveError: If the operation fails
        """
        service = self._get_service()

        try:
            permissions = []
            page_token = None

            while True:
                result = service.permissions().list(
                    fileId=resource_id,
                    supportsAllDrives=True,
                    fields='permissions(id,emailAddress,role,type),nextPageToken',
                    pageToken=page_token,
                    pageSize=100,
                ).execute()

                permissions.extend(result.get('permissions', []))
                page_token = result.get('nextPageToken')

                if not page_token:
                    break

            return [
                {
                    'permission_id': p['id'],
                    'email': p.get('emailAddress', ''),
                    'role': p['role'],
                    'type': p['type'],
                }
                for p in permissions
            ]

        except Exception as e:
            raise GoogleDriveError(f"Failed to list permissions: {e}")

    def get_resource_info(self, resource_id: str) -> dict[str, Any]:
        """
        Get information about a Google Drive resource.

        Args:
            resource_id: Google Drive resource ID

        Returns:
            dict with name, mimeType, etc.

        Raises:
            GoogleDriveError: If the operation fails
        """
        service = self._get_service()

        try:
            result = service.files().get(
                fileId=resource_id,
                supportsAllDrives=True,
                fields='id,name,mimeType,driveId',
            ).execute()

            return result

        except Exception as e:
            raise GoogleDriveError(f"Failed to get resource info: {e}")


class PermissionManager:
    """
    High-level manager for Google Drive permissions.

    Coordinates between the database models and the Google Drive API.
    """

    def __init__(self):
        self.drive_service = GoogleDriveService()

    def provision_role_access(
        self,
        profile,
        triggered_by: str = 'manual',
    ) -> dict[str, Any]:
        """
        Provision all role-based Google access for a profile.

        Args:
            profile: Profile instance
            triggered_by: What triggered this (for logging)

        Returns:
            dict with counts of granted, failed, skipped permissions
        """
        from .models import (
            RoleGoogleAccess,
            GooglePermission,
            GooglePermissionLog,
            OperationType,
            OperationStatus,
        )

        results = {'granted': 0, 'failed': 0, 'skipped': 0}

        # Get the profile's current role
        current_role = profile.current_role
        if not current_role:
            logger.warning(f"Profile {profile} has no active role")
            return results

        # Get all role-based access rules for this role
        access_rules = RoleGoogleAccess.objects.filter(
            role=current_role,
            is_active=True,
            resource__is_active=True,
        ).select_related('resource')

        for rule in access_rules:
            # Check if permission already exists
            existing = GooglePermission.objects.filter(
                profile=profile,
                resource=rule.resource,
                is_active=True,
            ).first()

            if existing:
                results['skipped'] += 1
                continue

            # Create log entry
            log = GooglePermissionLog.objects.create(
                profile=profile,
                resource=rule.resource,
                operation=OperationType.GRANT,
                permission_role=rule.permission_role,
                triggered_by=triggered_by,
            )

            try:
                # Grant permission via API
                result = self.drive_service.grant_permission(
                    resource_id=rule.resource.google_id,
                    email=profile.user.email,
                    role=rule.permission_role,
                )

                # Create permission record
                GooglePermission.objects.create(
                    profile=profile,
                    resource=rule.resource,
                    permission_id=result['permission_id'],
                    permission_role=rule.permission_role,
                    granted_via='ROLE',
                )

                # Update log
                log.status = OperationStatus.SUCCESS
                log.permission_id = result['permission_id']
                log.completed_at = timezone.now()
                log.save()

                results['granted'] += 1

            except RateLimitError as e:
                log.status = OperationStatus.RETRYING
                log.error_message = str(e)
                log.save()
                results['failed'] += 1
                # Could re-queue for later here

            except GoogleDriveError as e:
                log.status = OperationStatus.FAILED
                log.error_message = str(e)
                log.completed_at = timezone.now()
                log.save()
                results['failed'] += 1
                logger.error(f"Failed to grant access for {profile}: {e}")

        return results

    def provision_team_access(
        self,
        profile,
        team,
        triggered_by: str = 'manual',
    ) -> dict[str, Any]:
        """
        Provision all team-based Google access for a profile.

        Args:
            profile: Profile instance
            team: Team instance
            triggered_by: What triggered this (for logging)

        Returns:
            dict with counts of granted, failed, skipped permissions
        """
        from .models import (
            TeamGoogleAccess,
            GooglePermission,
            GooglePermissionLog,
            OperationType,
            OperationStatus,
        )

        results = {'granted': 0, 'failed': 0, 'skipped': 0}

        # Get all team-based access rules for this team
        access_rules = TeamGoogleAccess.objects.filter(
            team=team,
            is_active=True,
            resource__is_active=True,
        ).select_related('resource')

        for rule in access_rules:
            # Check if permission already exists
            existing = GooglePermission.objects.filter(
                profile=profile,
                resource=rule.resource,
                is_active=True,
            ).first()

            if existing:
                results['skipped'] += 1
                continue

            # Create log entry
            log = GooglePermissionLog.objects.create(
                profile=profile,
                resource=rule.resource,
                operation=OperationType.GRANT,
                permission_role=rule.permission_role,
                triggered_by=triggered_by,
            )

            try:
                # Grant permission via API
                result = self.drive_service.grant_permission(
                    resource_id=rule.resource.google_id,
                    email=profile.user.email,
                    role=rule.permission_role,
                )

                # Create permission record
                GooglePermission.objects.create(
                    profile=profile,
                    resource=rule.resource,
                    permission_id=result['permission_id'],
                    permission_role=rule.permission_role,
                    granted_via='TEAM',
                    team=team,
                )

                # Update log
                log.status = OperationStatus.SUCCESS
                log.permission_id = result['permission_id']
                log.completed_at = timezone.now()
                log.save()

                results['granted'] += 1

            except RateLimitError as e:
                log.status = OperationStatus.RETRYING
                log.error_message = str(e)
                log.save()
                results['failed'] += 1

            except GoogleDriveError as e:
                log.status = OperationStatus.FAILED
                log.error_message = str(e)
                log.completed_at = timezone.now()
                log.save()
                results['failed'] += 1
                logger.error(f"Failed to grant team access for {profile}: {e}")

        return results

    def revoke_all_access(
        self,
        profile,
        triggered_by: str = 'manual',
    ) -> dict[str, Any]:
        """
        Revoke all Google access for a profile.

        Args:
            profile: Profile instance
            triggered_by: What triggered this (for logging)

        Returns:
            dict with counts of revoked, failed permissions
        """
        from .models import (
            GooglePermission,
            GooglePermissionLog,
            OperationType,
            OperationStatus,
        )

        results = {'revoked': 0, 'failed': 0}

        # Get all active permissions for this profile
        permissions = GooglePermission.objects.filter(
            profile=profile,
            is_active=True,
        ).select_related('resource')

        for perm in permissions:
            # Create log entry
            log = GooglePermissionLog.objects.create(
                profile=profile,
                resource=perm.resource,
                operation=OperationType.REVOKE,
                permission_role=perm.permission_role,
                triggered_by=triggered_by,
            )

            try:
                # Revoke permission via API
                self.drive_service.revoke_permission(
                    resource_id=perm.resource.google_id,
                    permission_id=perm.permission_id,
                )

                # Mark permission as revoked
                perm.is_active = False
                perm.revoked_at = timezone.now()
                perm.save()

                # Update log
                log.status = OperationStatus.SUCCESS
                log.completed_at = timezone.now()
                log.save()

                results['revoked'] += 1

            except RateLimitError as e:
                log.status = OperationStatus.RETRYING
                log.error_message = str(e)
                log.save()
                results['failed'] += 1

            except GoogleDriveError as e:
                log.status = OperationStatus.FAILED
                log.error_message = str(e)
                log.completed_at = timezone.now()
                log.save()
                results['failed'] += 1
                logger.error(f"Failed to revoke access for {profile}: {e}")

        return results

    def revoke_team_access(
        self,
        profile,
        team,
        triggered_by: str = 'manual',
    ) -> dict[str, Any]:
        """
        Revoke team-specific Google access for a profile.

        Only revokes permissions that were granted via this specific team.

        Args:
            profile: Profile instance
            team: Team instance
            triggered_by: What triggered this (for logging)

        Returns:
            dict with counts of revoked, failed permissions
        """
        from .models import (
            GooglePermission,
            GooglePermissionLog,
            OperationType,
            OperationStatus,
        )

        results = {'revoked': 0, 'failed': 0}

        # Get permissions granted via this team
        permissions = GooglePermission.objects.filter(
            profile=profile,
            team=team,
            granted_via='TEAM',
            is_active=True,
        ).select_related('resource')

        for perm in permissions:
            # Check if user still has access via another team or role
            # If so, don't revoke from Google, just mark our record
            other_active = GooglePermission.objects.filter(
                profile=profile,
                resource=perm.resource,
                is_active=True,
            ).exclude(pk=perm.pk).exists()

            log = GooglePermissionLog.objects.create(
                profile=profile,
                resource=perm.resource,
                operation=OperationType.REVOKE,
                permission_role=perm.permission_role,
                triggered_by=triggered_by,
            )

            if other_active:
                # Don't revoke from Google, just mark our record
                perm.is_active = False
                perm.revoked_at = timezone.now()
                perm.save()

                log.status = OperationStatus.SUCCESS
                log.completed_at = timezone.now()
                log.error_message = "Skipped API call - user has access via other source"
                log.save()

                results['revoked'] += 1
                continue

            try:
                # Revoke permission via API
                self.drive_service.revoke_permission(
                    resource_id=perm.resource.google_id,
                    permission_id=perm.permission_id,
                )

                # Mark permission as revoked
                perm.is_active = False
                perm.revoked_at = timezone.now()
                perm.save()

                # Update log
                log.status = OperationStatus.SUCCESS
                log.completed_at = timezone.now()
                log.save()

                results['revoked'] += 1

            except RateLimitError as e:
                log.status = OperationStatus.RETRYING
                log.error_message = str(e)
                log.save()
                results['failed'] += 1

            except GoogleDriveError as e:
                log.status = OperationStatus.FAILED
                log.error_message = str(e)
                log.completed_at = timezone.now()
                log.save()
                results['failed'] += 1
                logger.error(f"Failed to revoke team access for {profile}: {e}")

        return results

    def reconcile_permissions(self, resource) -> dict[str, Any]:
        """
        Reconcile permissions for a resource.

        Compares desired state (from DB) with actual state (from Google API)
        and makes corrections.

        Args:
            resource: GoogleResource instance

        Returns:
            dict with counts of grants, revokes, and errors
        """
        from .models import (
            GooglePermission,
            GooglePermissionLog,
            RoleGoogleAccess,
            TeamGoogleAccess,
            OperationType,
            OperationStatus,
        )
        from apps.members.models import Profile, MembershipStatus

        results = {'granted': 0, 'revoked': 0, 'errors': 0}

        # Get actual permissions from Google
        try:
            actual_permissions = self.drive_service.list_permissions(
                resource.google_id
            )
        except GoogleDriveError as e:
            logger.error(f"Failed to list permissions for {resource}: {e}")
            return {'granted': 0, 'revoked': 0, 'errors': 1}

        # Build set of emails that currently have access
        actual_emails = {
            p['email'].lower()
            for p in actual_permissions
            if p['type'] == 'user' and p.get('email')
        }

        # Build set of emails that SHOULD have access
        desired_emails = set()

        # Get all active profiles
        active_profiles = Profile.objects.filter(
            role_assignments__is_active=True,
        ).distinct()

        for profile in active_profiles:
            if profile.membership_status != MembershipStatus.ACTIVE:
                continue

            email = profile.user.email.lower()

            # Check role-based access
            role = profile.current_role
            if role:
                has_role_access = RoleGoogleAccess.objects.filter(
                    role=role,
                    resource=resource,
                    is_active=True,
                ).exists()
                if has_role_access:
                    desired_emails.add(email)

            # Check team-based access
            team_ids = profile.team_memberships.filter(
                is_active=True
            ).values_list('team_id', flat=True)

            has_team_access = TeamGoogleAccess.objects.filter(
                team_id__in=team_ids,
                resource=resource,
                is_active=True,
            ).exists()
            if has_team_access:
                desired_emails.add(email)

        # Find missing permissions (should have but don't)
        missing = desired_emails - actual_emails
        for email in missing:
            try:
                profile = Profile.objects.get(user__email__iexact=email)
            except Profile.DoesNotExist:
                continue

            # Determine what role to grant
            role_access = RoleGoogleAccess.objects.filter(
                role=profile.current_role,
                resource=resource,
                is_active=True,
            ).first()

            if role_access:
                permission_role = role_access.permission_role
            else:
                # Must be team-based
                team_access = TeamGoogleAccess.objects.filter(
                    team__memberships__profile=profile,
                    team__memberships__is_active=True,
                    resource=resource,
                    is_active=True,
                ).first()
                if team_access:
                    permission_role = team_access.permission_role
                else:
                    continue

            log = GooglePermissionLog.objects.create(
                profile=profile,
                resource=resource,
                operation=OperationType.RECONCILE_GRANT,
                permission_role=permission_role,
                triggered_by='reconciliation',
            )

            try:
                result = self.drive_service.grant_permission(
                    resource_id=resource.google_id,
                    email=email,
                    role=permission_role,
                )

                GooglePermission.objects.create(
                    profile=profile,
                    resource=resource,
                    permission_id=result['permission_id'],
                    permission_role=permission_role,
                    granted_via='ROLE',  # Could be more specific
                )

                log.status = OperationStatus.SUCCESS
                log.permission_id = result['permission_id']
                log.completed_at = timezone.now()
                log.save()

                results['granted'] += 1

            except GoogleDriveError as e:
                log.status = OperationStatus.FAILED
                log.error_message = str(e)
                log.completed_at = timezone.now()
                log.save()
                results['errors'] += 1

        # Find extra permissions (have but shouldn't)
        # Note: We only revoke permissions we track in our DB
        extra = actual_emails - desired_emails

        for email in extra:
            # Find our permission record
            try:
                perm = GooglePermission.objects.get(
                    profile__user__email__iexact=email,
                    resource=resource,
                    is_active=True,
                )
            except GooglePermission.DoesNotExist:
                # We don't track this permission, skip it
                continue

            log = GooglePermissionLog.objects.create(
                profile=perm.profile,
                resource=resource,
                operation=OperationType.RECONCILE_REVOKE,
                permission_role=perm.permission_role,
                triggered_by='reconciliation',
            )

            try:
                self.drive_service.revoke_permission(
                    resource_id=resource.google_id,
                    permission_id=perm.permission_id,
                )

                perm.is_active = False
                perm.revoked_at = timezone.now()
                perm.save()

                log.status = OperationStatus.SUCCESS
                log.completed_at = timezone.now()
                log.save()

                results['revoked'] += 1

            except GoogleDriveError as e:
                log.status = OperationStatus.FAILED
                log.error_message = str(e)
                log.completed_at = timezone.now()
                log.save()
                results['errors'] += 1

        return results
