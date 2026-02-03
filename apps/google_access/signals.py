"""
Signals for Google access provisioning and revocation.

Listens to membership status changes and team membership changes
to trigger appropriate Google Drive permission updates.
"""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.members.models import Profile, TeamMembership, MembershipStatus

logger = logging.getLogger(__name__)


# Store old status for comparison
_profile_old_status = {}


@receiver(pre_save, sender=Profile)
def capture_old_status(sender, instance, **kwargs):
    """Capture the old membership status before save."""
    if instance.pk:
        try:
            old_instance = Profile.objects.get(pk=instance.pk)
            _profile_old_status[instance.pk] = old_instance.membership_status
        except Profile.DoesNotExist:
            pass


@receiver(post_save, sender=Profile)
def handle_profile_status_change(sender, instance, created, **kwargs):
    """
    Handle membership status changes for Google access.

    - On status → ACTIVE: provision role-based access
    - On status → RESTRICTED/EXPIRED/REMOVED: revoke all access
    """
    from .tasks import provision_google_access, revoke_google_access

    current_status = instance.membership_status
    old_status = _profile_old_status.pop(instance.pk, None)

    if created:
        # New profile, check if they need access
        if current_status == MembershipStatus.ACTIVE:
            provision_google_access.delay(instance.pk, triggered_by='profile_created')
        return

    if old_status == current_status:
        # No status change
        return

    logger.info(
        f"Profile {instance} status changed: {old_status} → {current_status}"
    )

    # Provision on becoming active
    if current_status == MembershipStatus.ACTIVE:
        if old_status != MembershipStatus.ACTIVE:
            provision_google_access.delay(instance.pk, triggered_by='status_change')

    # Revoke on leaving active status
    if current_status in [
        MembershipStatus.RESTRICTED,
        MembershipStatus.EXPIRED,
        MembershipStatus.REMOVED,
        MembershipStatus.NONE,
    ]:
        if old_status == MembershipStatus.ACTIVE:
            revoke_google_access.delay(instance.pk, triggered_by='status_change')


@receiver(post_save, sender=TeamMembership)
def handle_team_membership_change(sender, instance, created, **kwargs):
    """
    Handle team membership changes for Google access.

    - On join team: provision team-based access
    - On leave team: revoke team-specific access
    """
    from .tasks import provision_team_google_access, revoke_team_google_access

    profile = instance.profile

    # Only process if profile is active
    if profile.membership_status != MembershipStatus.ACTIVE:
        return

    if created and instance.is_active:
        # New team membership
        provision_team_google_access.delay(
            profile.pk,
            instance.team.pk,
            triggered_by='team_join',
        )
    elif not instance.is_active:
        # Check if this was a deactivation (not a new inactive record)
        # We can check if left_at was just set
        if instance.left_at:
            revoke_team_google_access.delay(
                profile.pk,
                instance.team.pk,
                triggered_by='team_leave',
            )
