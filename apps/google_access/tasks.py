"""
Celery tasks for Google access management.

Handles async provisioning, revocation, and reconciliation of Google Drive permissions.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def provision_google_access(self, profile_id: int, triggered_by: str = 'manual'):
    """
    Provision all role-based Google access for a profile.

    Args:
        profile_id: Profile ID
        triggered_by: What triggered this task
    """
    from apps.members.models import Profile
    from .services import PermissionManager

    try:
        profile = Profile.objects.get(pk=profile_id)
    except Profile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found")
        return

    manager = PermissionManager()
    results = manager.provision_role_access(profile, triggered_by=triggered_by)

    logger.info(
        f"Provisioned Google access for {profile}: "
        f"{results['granted']} granted, {results['failed']} failed, "
        f"{results['skipped']} skipped"
    )

    return results


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def revoke_google_access(self, profile_id: int, triggered_by: str = 'manual'):
    """
    Revoke all Google access for a profile.

    Args:
        profile_id: Profile ID
        triggered_by: What triggered this task
    """
    from apps.members.models import Profile
    from .services import PermissionManager

    try:
        profile = Profile.objects.get(pk=profile_id)
    except Profile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found")
        return

    manager = PermissionManager()
    results = manager.revoke_all_access(profile, triggered_by=triggered_by)

    logger.info(
        f"Revoked Google access for {profile}: "
        f"{results['revoked']} revoked, {results['failed']} failed"
    )

    return results


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def provision_team_google_access(
    self,
    profile_id: int,
    team_id: int,
    triggered_by: str = 'manual',
):
    """
    Provision team-based Google access for a profile.

    Args:
        profile_id: Profile ID
        team_id: Team ID
        triggered_by: What triggered this task
    """
    from apps.members.models import Profile, Team
    from .services import PermissionManager

    try:
        profile = Profile.objects.get(pk=profile_id)
        team = Team.objects.get(pk=team_id)
    except Profile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found")
        return
    except Team.DoesNotExist:
        logger.error(f"Team {team_id} not found")
        return

    manager = PermissionManager()
    results = manager.provision_team_access(profile, team, triggered_by=triggered_by)

    logger.info(
        f"Provisioned team '{team.name}' access for {profile}: "
        f"{results['granted']} granted, {results['failed']} failed, "
        f"{results['skipped']} skipped"
    )

    return results


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def revoke_team_google_access(
    self,
    profile_id: int,
    team_id: int,
    triggered_by: str = 'manual',
):
    """
    Revoke team-specific Google access for a profile.

    Args:
        profile_id: Profile ID
        team_id: Team ID
        triggered_by: What triggered this task
    """
    from apps.members.models import Profile, Team
    from .services import PermissionManager

    try:
        profile = Profile.objects.get(pk=profile_id)
        team = Team.objects.get(pk=team_id)
    except Profile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found")
        return
    except Team.DoesNotExist:
        logger.error(f"Team {team_id} not found")
        return

    manager = PermissionManager()
    results = manager.revoke_team_access(profile, team, triggered_by=triggered_by)

    logger.info(
        f"Revoked team '{team.name}' access for {profile}: "
        f"{results['revoked']} revoked, {results['failed']} failed"
    )

    return results


@shared_task
def reconcile_google_permissions():
    """
    Daily reconciliation of Google Drive permissions.

    For each active resource, compares desired state with actual state
    and makes corrections.
    """
    from .models import GoogleResource
    from .services import PermissionManager

    logger.info("Starting Google permissions reconciliation")

    resources = GoogleResource.objects.filter(is_active=True)
    manager = PermissionManager()

    total_results = {'granted': 0, 'revoked': 0, 'errors': 0}

    for resource in resources:
        logger.info(f"Reconciling permissions for {resource.name}")

        results = manager.reconcile_permissions(resource)

        total_results['granted'] += results['granted']
        total_results['revoked'] += results['revoked']
        total_results['errors'] += results['errors']

        logger.info(
            f"Reconciled {resource.name}: "
            f"+{results['granted']} -{results['revoked']} errors:{results['errors']}"
        )

    logger.info(
        f"Reconciliation complete: "
        f"+{total_results['granted']} -{total_results['revoked']} "
        f"errors:{total_results['errors']}"
    )

    return total_results


@shared_task
def check_expiring_memberships():
    """
    Check for expiring memberships and send reminders.

    Sends reminders at 60, 30, 7, and 0 days before expiry.
    On expiry day, deactivates the role and revokes access.
    """
    from apps.members.models import RoleAssignment
    from .tasks import revoke_google_access

    today = timezone.now().date()

    # Check for memberships expiring at reminder intervals
    reminder_days = [60, 30, 7, 0]

    for days in reminder_days:
        target_date = today + timedelta(days=days)

        expiring = RoleAssignment.objects.filter(
            is_active=True,
            end_date=target_date,
        ).select_related('profile', 'profile__user')

        for assignment in expiring:
            if days == 0:
                # Expiry day - deactivate and revoke
                logger.info(
                    f"Membership expired for {assignment.profile}: "
                    f"deactivating role and revoking access"
                )
                assignment.is_active = False
                assignment.notes = f"{assignment.notes}\nExpired on {today}"
                assignment.save()

                # Revoke Google access
                revoke_google_access.delay(
                    assignment.profile.pk,
                    triggered_by='membership_expired',
                )

                # Send expiry email
                send_membership_expired_email.delay(assignment.profile.pk)
            else:
                # Send reminder
                logger.info(
                    f"Sending {days}-day expiry reminder to {assignment.profile}"
                )
                send_membership_expiring_email.delay(
                    assignment.profile.pk,
                    days_remaining=days,
                )


@shared_task
def send_membership_expiring_email(profile_id: int, days_remaining: int):
    """Send membership expiring reminder email."""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from apps.members.models import Profile

    try:
        profile = Profile.objects.select_related('user').get(pk=profile_id)
    except Profile.DoesNotExist:
        return

    context = {
        'profile': profile,
        'days_remaining': days_remaining,
    }

    subject = f"Your Nobodies Collective membership expires in {days_remaining} days"
    text_content = render_to_string('emails/membership_expiring.txt', context)
    html_content = render_to_string('emails/membership_expiring.html', context)

    send_mail(
        subject=subject,
        message=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[profile.user.email],
        html_message=html_content,
        fail_silently=False,
    )


@shared_task
def send_membership_expired_email(profile_id: int):
    """Send membership expired email."""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from apps.members.models import Profile

    try:
        profile = Profile.objects.select_related('user').get(pk=profile_id)
    except Profile.DoesNotExist:
        return

    context = {
        'profile': profile,
    }

    subject = "Your Nobodies Collective membership has expired"
    text_content = render_to_string('emails/membership_expired.txt', context)
    html_content = render_to_string('emails/membership_expired.html', context)

    send_mail(
        subject=subject,
        message=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[profile.user.email],
        html_message=html_content,
        fail_silently=False,
    )


@shared_task
def retry_failed_operations():
    """
    Retry failed Google permission operations.

    Picks up operations that failed or are marked as RETRYING
    and attempts them again.
    """
    from .models import GooglePermissionLog, OperationStatus, OperationType
    from .services import PermissionManager, GoogleDriveError, RateLimitError

    # Get failed operations from the last 24 hours with retry_count < 5
    cutoff = timezone.now() - timedelta(hours=24)

    failed_ops = GooglePermissionLog.objects.filter(
        status__in=[OperationStatus.FAILED, OperationStatus.RETRYING],
        created_at__gte=cutoff,
        retry_count__lt=5,
    ).select_related('profile', 'resource')

    manager = PermissionManager()
    retried = 0
    succeeded = 0
    failed = 0

    for log in failed_ops:
        if not log.profile or not log.resource:
            continue

        log.retry_count += 1
        log.status = OperationStatus.RETRYING
        log.save()

        retried += 1

        try:
            if log.operation in [OperationType.GRANT, OperationType.RECONCILE_GRANT]:
                result = manager.drive_service.grant_permission(
                    resource_id=log.resource.google_id,
                    email=log.profile.user.email,
                    role=log.permission_role,
                )
                log.permission_id = result['permission_id']
                log.status = OperationStatus.SUCCESS
                log.completed_at = timezone.now()
                succeeded += 1

            elif log.operation in [OperationType.REVOKE, OperationType.RECONCILE_REVOKE]:
                # Need the permission_id from the GooglePermission record
                from .models import GooglePermission
                perm = GooglePermission.objects.filter(
                    profile=log.profile,
                    resource=log.resource,
                    is_active=True,
                ).first()

                if perm:
                    manager.drive_service.revoke_permission(
                        resource_id=log.resource.google_id,
                        permission_id=perm.permission_id,
                    )
                    perm.is_active = False
                    perm.revoked_at = timezone.now()
                    perm.save()

                log.status = OperationStatus.SUCCESS
                log.completed_at = timezone.now()
                succeeded += 1

        except RateLimitError as e:
            log.error_message = f"Retry {log.retry_count}: {e}"
            log.status = OperationStatus.RETRYING
            failed += 1

        except GoogleDriveError as e:
            log.error_message = f"Retry {log.retry_count}: {e}"
            if log.retry_count >= 5:
                log.status = OperationStatus.FAILED
            failed += 1

        log.save()

    logger.info(
        f"Retry task complete: {retried} retried, "
        f"{succeeded} succeeded, {failed} failed"
    )

    return {'retried': retried, 'succeeded': succeeded, 'failed': failed}
