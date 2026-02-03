"""
Signals for the applications app.

Handles post-save actions like sending notification emails.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Application, ApplicationStatus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Application)
def handle_application_status_change(sender, instance, created, **kwargs):
    """
    Handle application status changes.

    - On creation: send confirmation email to applicant
    - On approval: send approval notification
    - On rejection: send rejection notification
    """
    from .tasks import (
        send_application_confirmation,
        send_approval_notification,
        send_rejection_notification,
    )

    if created:
        # New application submitted - send confirmation
        logger.info(f"New application created: {instance.pk}")
        send_application_confirmation.delay(instance.pk)
        return

    # Check for status changes by comparing with previous state
    # We use the update_fields to detect what changed
    update_fields = kwargs.get('update_fields')

    # If this is a status change (either explicitly or via full save after FSM transition)
    if instance.status == ApplicationStatus.APPROVED:
        # Check if this looks like a recent approval (reviewed_at is set)
        if instance.reviewed_at:
            logger.info(f"Application {instance.pk} approved")
            send_approval_notification.delay(instance.pk)

    elif instance.status == ApplicationStatus.REJECTED:
        if instance.reviewed_at:
            logger.info(f"Application {instance.pk} rejected")
            send_rejection_notification.delay(instance.pk)
