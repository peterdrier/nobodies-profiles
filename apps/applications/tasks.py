"""Celery tasks for the applications app."""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import activate, gettext as _

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_application_confirmation(self, application_id: int):
    """
    Send confirmation email when an application is submitted.

    Args:
        application_id: The ID of the Application
    """
    from .models import Application

    try:
        application = Application.objects.select_related('user').get(pk=application_id)
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found")
        return

    # Activate the user's preferred language
    activate(application.preferred_language)

    subject = _("Application Received - Nobodies Collective")
    context = {
        'application': application,
        'user': application.user,
    }

    html_message = render_to_string('emails/application_received.html', context)
    plain_message = render_to_string('emails/application_received.txt', context)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent application confirmation to {application.user.email}")
    except Exception as exc:
        logger.error(f"Failed to send application confirmation: {exc}")
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_approval_notification(self, application_id: int):
    """
    Send notification when an application is approved.

    Args:
        application_id: The ID of the Application
    """
    from .models import Application

    try:
        application = Application.objects.select_related('user').get(pk=application_id)
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found")
        return

    activate(application.preferred_language)

    subject = _("Your Application Has Been Approved - Nobodies Collective")
    context = {
        'application': application,
        'user': application.user,
    }

    html_message = render_to_string('emails/application_approved.html', context)
    plain_message = render_to_string('emails/application_approved.txt', context)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent approval notification to {application.user.email}")
    except Exception as exc:
        logger.error(f"Failed to send approval notification: {exc}")
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_rejection_notification(self, application_id: int):
    """
    Send notification when an application is rejected.

    Args:
        application_id: The ID of the Application
    """
    from .models import Application

    try:
        application = Application.objects.select_related('user').get(pk=application_id)
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found")
        return

    activate(application.preferred_language)

    subject = _("Update on Your Application - Nobodies Collective")
    context = {
        'application': application,
        'user': application.user,
    }

    html_message = render_to_string('emails/application_rejected.html', context)
    plain_message = render_to_string('emails/application_rejected.txt', context)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent rejection notification to {application.user.email}")
    except Exception as exc:
        logger.error(f"Failed to send rejection notification: {exc}")
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
