"""Celery tasks for the documents app."""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import activate, gettext as _

from .models import ConsentRecord, DocumentVersion, get_pending_documents_for_profile
from .services import sync_legal_documents

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_documents_from_git(self):
    """
    Sync legal documents from the git repository.

    Scheduled to run daily via celery-beat.
    """
    logger.info("Starting document sync from git")

    try:
        summary = sync_legal_documents()
        logger.info(f"Document sync complete: {summary}")
        return summary
    except Exception as exc:
        logger.error(f"Document sync failed: {exc}")
        self.retry(exc=exc, countdown=300)  # Retry in 5 minutes


@shared_task(bind=True, max_retries=3)
def send_consent_required_notification(self, profile_id: int, document_version_id: int):
    """
    Send notification that a new document version requires consent.
    """
    from apps.members.models import Profile

    try:
        profile = Profile.objects.select_related('user').get(pk=profile_id)
        version = DocumentVersion.objects.select_related('document').get(pk=document_version_id)
    except (Profile.DoesNotExist, DocumentVersion.DoesNotExist) as e:
        logger.error(f"Profile or DocumentVersion not found: {e}")
        return

    activate(profile.user.preferred_language)

    subject = _("Action Required: New Document Version - Nobodies Collective")
    context = {
        'profile': profile,
        'user': profile.user,
        'document': version.document,
        'version': version,
    }

    html_message = render_to_string('emails/consent_required.html', context)
    plain_message = render_to_string('emails/consent_required.txt', context)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[profile.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent consent required notification to {profile.user.email}")
    except Exception as exc:
        logger.error(f"Failed to send consent notification: {exc}")
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_consent_reminder(self, profile_id: int, days_until_deadline: int):
    """
    Send reminder about upcoming consent deadline.
    """
    from apps.members.models import Profile

    try:
        profile = Profile.objects.select_related('user').get(pk=profile_id)
    except Profile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found")
        return

    pending_docs = get_pending_documents_for_profile(profile)
    if not pending_docs:
        return  # No pending documents

    activate(profile.user.preferred_language)

    subject = _("Reminder: Documents Require Your Signature - Nobodies Collective")
    context = {
        'profile': profile,
        'user': profile.user,
        'pending_documents': pending_docs,
        'days_until_deadline': days_until_deadline,
    }

    html_message = render_to_string('emails/consent_reminder.html', context)
    plain_message = render_to_string('emails/consent_reminder.txt', context)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[profile.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent consent reminder to {profile.user.email}")
    except Exception as exc:
        logger.error(f"Failed to send consent reminder: {exc}")
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def enforce_consent_deadlines():
    """
    Check for members past re-consent deadlines and update their status.

    Scheduled to run daily via celery-beat.
    """
    from django.utils import timezone
    from apps.members.models import Profile, MembershipStatus

    logger.info("Checking consent deadlines")

    today = timezone.now().date()
    affected_count = 0

    # Find all active profiles
    active_profiles = Profile.objects.filter(
        role_assignments__is_active=True,
    ).distinct()

    for profile in active_profiles:
        pending = get_pending_documents_for_profile(profile)

        for item in pending:
            version = item['version']
            if version.requires_re_consent and version.re_consent_deadline:
                if version.re_consent_deadline < today:
                    # This profile has an overdue re-consent
                    affected_count += 1
                    logger.info(
                        f"Profile {profile.pk} is past re-consent deadline for "
                        f"{version.document.slug}"
                    )
                    # Status is computed dynamically, but we could send notification here
                    # send_consent_overdue_notification.delay(profile.pk)
                    break

    logger.info(f"Found {affected_count} profiles with overdue consents")
    return affected_count


@shared_task
def send_consent_reminders_batch():
    """
    Send reminders to members with upcoming consent deadlines.

    Scheduled to run daily via celery-beat.
    Sends reminders at 7 days and 1 day before deadline.
    """
    from django.utils import timezone
    from apps.members.models import Profile

    logger.info("Sending consent reminder batch")

    today = timezone.now().date()
    reminder_days = [7, 1]  # Days before deadline to send reminders

    active_profiles = Profile.objects.filter(
        role_assignments__is_active=True,
    ).distinct()

    reminders_sent = 0

    for profile in active_profiles:
        pending = get_pending_documents_for_profile(profile)

        for item in pending:
            version = item['version']
            if version.requires_re_consent and version.re_consent_deadline:
                days_until = (version.re_consent_deadline - today).days

                if days_until in reminder_days:
                    send_consent_reminder.delay(profile.pk, days_until)
                    reminders_sent += 1
                    break  # One reminder per profile per day

    logger.info(f"Queued {reminders_sent} consent reminders")
    return reminders_sent
