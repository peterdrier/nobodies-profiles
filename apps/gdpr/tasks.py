"""
Celery tasks for GDPR operations.

Handles data export generation, anonymization execution,
and scheduled cleanup jobs.
"""
import hashlib
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import (
    AuditCategory,
    DataAccessRequest,
    DataAccessRequestStatus,
    DataDeletionRequest,
    DeletionRequestStatus,
    log_audit,
)
from .services import AnonymizationService, DataExportService


@shared_task(bind=True, max_retries=3)
def generate_data_export(self, request_id: int):
    """
    Generate data export ZIP file for a DataAccessRequest.

    Args:
        request_id: ID of the DataAccessRequest
    """
    try:
        request = DataAccessRequest.objects.select_related('profile', 'profile__user').get(
            id=request_id
        )
    except DataAccessRequest.DoesNotExist:
        return {'error': 'Request not found'}

    if request.status != DataAccessRequestStatus.PENDING:
        return {'error': f'Request in invalid state: {request.status}'}

    try:
        # Update status to processing
        request.status = DataAccessRequestStatus.PROCESSING
        request.celery_task_id = self.request.id
        request.save()

        # Generate the export
        service = DataExportService(request.profile)
        zip_buffer = service.generate_export()
        zip_content = zip_buffer.getvalue()

        # Calculate checksum
        checksum = hashlib.sha256(zip_content).hexdigest()

        # Save the file
        filename = f"export_{request.profile.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
        request.export_file.save(filename, ContentFile(zip_content))
        request.export_file_size = len(zip_content)
        request.export_checksum = checksum
        request.expires_at = timezone.now() + timedelta(days=settings.GDPR_EXPORT_EXPIRY_DAYS)
        request.status = DataAccessRequestStatus.COMPLETED
        request.completed_at = timezone.now()
        request.save()

        # Log the action
        log_audit(
            action='export_generated',
            description=f'Data export generated for {request.profile.legal_name}',
            category=AuditCategory.DATA_EXPORT,
            user=request.requested_by,
            profile=request.profile,
            content_object=request,
            extra_data={'file_size': len(zip_content), 'checksum': checksum},
        )

        # Send notification email
        send_data_export_ready_email.delay(request_id)

        return {
            'success': True,
            'request_id': request_id,
            'file_size': len(zip_content),
        }

    except Exception as e:
        request.status = DataAccessRequestStatus.FAILED
        request.error_message = str(e)
        request.save()

        # Log the failure
        log_audit(
            action='export_failed',
            description=f'Data export failed for {request.profile.legal_name}: {e}',
            category=AuditCategory.DATA_EXPORT,
            profile=request.profile,
            content_object=request,
            extra_data={'error': str(e)},
        )

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_data_export_ready_email(request_id: int):
    """
    Send email notification that data export is ready.

    Args:
        request_id: ID of the DataAccessRequest
    """
    try:
        request = DataAccessRequest.objects.select_related('profile', 'profile__user').get(
            id=request_id
        )
    except DataAccessRequest.DoesNotExist:
        return {'error': 'Request not found'}

    user = request.profile.user

    # Build download URL
    download_url = reverse('gdpr:download_export', kwargs={'token': str(request.download_token)})

    context = {
        'user': user,
        'profile': request.profile,
        'download_url': download_url,
        'expires_at': request.expires_at,
        'expiry_days': settings.GDPR_EXPORT_EXPIRY_DAYS,
    }

    subject = 'Your data export is ready'
    html_message = render_to_string('emails/data_export_ready.html', context)
    plain_message = render_to_string('emails/data_export_ready.txt', context)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )

    return {'success': True, 'email': user.email}


@shared_task(bind=True, max_retries=3)
def execute_data_anonymization(self, request_id: int):
    """
    Execute data anonymization for a DataDeletionRequest.

    Args:
        request_id: ID of the DataDeletionRequest
    """
    try:
        request = DataDeletionRequest.objects.select_related('profile', 'profile__user').get(
            id=request_id
        )
    except DataDeletionRequest.DoesNotExist:
        return {'error': 'Request not found'}

    if request.status != DeletionRequestStatus.APPROVED:
        return {'error': f'Request in invalid state: {request.status}'}

    profile = request.profile
    original_email = profile.user.email

    try:
        # Update status to executing
        request.start_execution(task_id=self.request.id)
        request.save()

        # First, revoke all Google access
        revoke_google_access_for_deletion.delay(profile.id)

        # Perform anonymization
        service = AnonymizationService(profile)
        anonymization_log = service.anonymize()

        # Update request with results
        request.complete_execution(anonymization_log=anonymization_log)
        request.save()

        # Log the action
        log_audit(
            action='data_anonymized',
            description=f'Data anonymized for profile #{profile.id}',
            category=AuditCategory.DATA_DELETION,
            profile=profile,
            content_object=request,
            extra_data=anonymization_log,
        )

        # Send confirmation email to original email
        send_deletion_executed_email.delay(original_email)

        return {
            'success': True,
            'request_id': request_id,
            'anonymization_log': anonymization_log,
        }

    except Exception as e:
        request.fail_execution(error_message=str(e))
        request.save()

        # Log the failure
        log_audit(
            action='anonymization_failed',
            description=f'Data anonymization failed for profile #{profile.id}: {e}',
            category=AuditCategory.DATA_DELETION,
            profile=profile,
            content_object=request,
            extra_data={'error': str(e)},
        )

        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def revoke_google_access_for_deletion(profile_id: int):
    """
    Revoke all Google access before data deletion.

    Args:
        profile_id: ID of the Profile
    """
    from apps.google_access.models import GooglePermission

    # This will be handled by the existing google_access revocation system
    # Mark all permissions for revocation
    GooglePermission.objects.filter(
        profile_id=profile_id,
        is_active=True,
    ).update(is_active=False, revoked_at=timezone.now())

    return {'profile_id': profile_id}


@shared_task
def send_deletion_executed_email(original_email: str):
    """
    Send confirmation that account deletion was executed.

    Args:
        original_email: The user's original email before anonymization
    """
    context = {
        'email': original_email,
    }

    subject = 'Your account has been deleted'
    html_message = render_to_string('emails/deletion_executed.html', context)
    plain_message = render_to_string('emails/deletion_executed.txt', context)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[original_email],
        html_message=html_message,
        fail_silently=False,
    )

    return {'success': True, 'email': original_email}


@shared_task
def cleanup_gdpr_exports():
    """
    Daily task to clean up expired GDPR exports.

    Deletes export files that have passed their expiry date.
    """
    expired_requests = DataAccessRequest.objects.filter(
        status=DataAccessRequestStatus.COMPLETED,
        expires_at__lt=timezone.now(),
    ).exclude(export_file='')

    cleaned = 0
    for request in expired_requests:
        # Delete the file
        if request.export_file:
            request.export_file.delete(save=False)

        request.status = DataAccessRequestStatus.EXPIRED
        request.save()
        cleaned += 1

        log_audit(
            action='export_expired',
            description=f'Expired export cleaned up for profile #{request.profile_id}',
            category=AuditCategory.DATA_EXPORT,
            profile=request.profile,
            content_object=request,
        )

    return {'cleaned': cleaned}


@shared_task
def cleanup_rejected_applications():
    """
    Daily task to anonymize rejected applications after retention period.

    Anonymizes applications that were rejected more than
    GDPR_REJECTED_APP_RETENTION_DAYS days ago.
    """
    from apps.applications.models import Application, ApplicationStatus

    retention_days = settings.GDPR_REJECTED_APP_RETENTION_DAYS
    cutoff_date = timezone.now() - timedelta(days=retention_days)

    # Find rejected applications past retention period
    old_rejected = Application.objects.filter(
        status=ApplicationStatus.REJECTED,
        reviewed_at__lt=cutoff_date,
    ).exclude(legal_name='[REDACTED]')

    anonymized = 0
    for app in old_rejected:
        app.legal_name = '[REDACTED]'
        app.preferred_name = ''
        app.motivation = '[REDACTED]'
        app.skills = '[REDACTED]'
        app.how_heard = '[REDACTED]'
        app.save()
        anonymized += 1

        log_audit(
            action='application_anonymized',
            description=f'Rejected application #{app.id} anonymized after {retention_days} days',
            category=AuditCategory.APPLICATION,
            user=app.user,
            content_object=app,
        )

    return {'anonymized': anonymized}
