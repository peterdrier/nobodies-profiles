"""
Signals for the applications app.

Handles post-save actions like sending notification emails.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Application, ApplicationStatus


@receiver(post_save, sender=Application)
def handle_application_status_change(sender, instance, created, **kwargs):
    """
    Handle application status changes.

    - On creation: send confirmation email to applicant
    - On approval: send approval notification
    - On rejection: send rejection notification
    """
    if created:
        # New application submitted
        # TODO: Implement send_application_confirmation task in Phase 1.7
        pass

    # Check if status changed to approved or rejected
    # This will be enhanced with Celery tasks in Phase 1.7
