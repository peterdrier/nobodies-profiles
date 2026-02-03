"""
GDPR models for data access requests, deletion requests, and audit logging.

Implements GDPR Articles 15 (right of access) and 17 (right to erasure).
"""
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from viewflow.fsm import State


class DataAccessRequestStatus(models.TextChoices):
    """Status values for data access requests."""
    PENDING = 'PENDING', _('Pending')
    PROCESSING = 'PROCESSING', _('Processing')
    COMPLETED = 'COMPLETED', _('Completed')
    FAILED = 'FAILED', _('Failed')
    EXPIRED = 'EXPIRED', _('Expired')


class DataAccessRequest(models.Model):
    """
    GDPR Article 15 - Right of Access request.

    Tracks requests for personal data export.
    """
    profile = models.ForeignKey(
        'members.Profile',
        on_delete=models.CASCADE,
        related_name='data_access_requests',
        verbose_name=_('profile'),
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='data_access_requests_made',
        verbose_name=_('requested by'),
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=DataAccessRequestStatus.choices,
        default=DataAccessRequestStatus.PENDING,
    )

    # Export file details
    export_file = models.FileField(
        _('export file'),
        upload_to='gdpr_exports/%Y/%m/',
        blank=True,
        null=True,
    )
    export_file_size = models.PositiveIntegerField(
        _('file size'),
        null=True,
        blank=True,
        help_text=_('Size in bytes'),
    )
    export_checksum = models.CharField(
        _('checksum'),
        max_length=64,
        blank=True,
        help_text=_('SHA-256 hash of the export file'),
    )

    # Download tracking
    download_token = models.UUIDField(
        _('download token'),
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    download_count = models.PositiveIntegerField(
        _('download count'),
        default=0,
    )
    first_downloaded_at = models.DateTimeField(
        _('first downloaded'),
        null=True,
        blank=True,
    )
    expires_at = models.DateTimeField(
        _('expires at'),
        null=True,
        blank=True,
    )

    # Processing tracking
    celery_task_id = models.CharField(
        _('celery task ID'),
        max_length=255,
        blank=True,
    )
    error_message = models.TextField(
        _('error message'),
        blank=True,
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('data access request')
        verbose_name_plural = _('data access requests')
        ordering = ['-created_at']

    def __str__(self):
        return f"Export request for {self.profile.legal_name} ({self.status})"

    @property
    def is_expired(self) -> bool:
        """Check if the export has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_downloadable(self) -> bool:
        """Check if the export is ready for download."""
        return (
            self.status == DataAccessRequestStatus.COMPLETED and
            self.export_file and
            not self.is_expired
        )


class DeletionRequestStatus(models.TextChoices):
    """Status values for data deletion requests."""
    REQUESTED = 'REQUESTED', _('Requested')
    PENDING_CONFIRMATION = 'PENDING_CONFIRMATION', _('Pending Confirmation')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
    APPROVED = 'APPROVED', _('Approved')
    DENIED = 'DENIED', _('Denied')
    EXECUTING = 'EXECUTING', _('Executing')
    EXECUTED = 'EXECUTED', _('Executed')
    FAILED = 'FAILED', _('Failed')


class DataDeletionRequest(models.Model):
    """
    GDPR Article 17 - Right to Erasure request.

    Tracks requests for personal data deletion/anonymization.
    Uses FSM for workflow: REQUESTED → UNDER_REVIEW → APPROVED/DENIED → EXECUTING → EXECUTED
    """
    profile = models.ForeignKey(
        'members.Profile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='data_deletion_requests',
        verbose_name=_('profile'),
    )
    profile_snapshot = models.JSONField(
        _('profile snapshot'),
        blank=True,
        default=dict,
        help_text=_('JSON backup of profile data before deletion'),
    )

    # Status tracking with FSM
    status = models.CharField(
        _('status'),
        max_length=25,
        choices=DeletionRequestStatus.choices,
        default=DeletionRequestStatus.REQUESTED,
    )
    state = State(DeletionRequestStatus, default=DeletionRequestStatus.REQUESTED)

    # Request details
    request_reason = models.TextField(
        _('reason'),
        blank=True,
        help_text=_('Why the user wants their data deleted'),
    )
    confirmation_token = models.UUIDField(
        _('confirmation token'),
        default=uuid.uuid4,
        unique=True,
    )
    confirmed_at = models.DateTimeField(
        _('confirmed at'),
        null=True,
        blank=True,
    )

    # Review details
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deletion_requests_reviewed',
        verbose_name=_('reviewed by'),
    )
    reviewed_at = models.DateTimeField(
        _('reviewed at'),
        null=True,
        blank=True,
    )
    review_notes = models.TextField(
        _('review notes'),
        blank=True,
    )
    denial_reason = models.TextField(
        _('denial reason'),
        blank=True,
    )

    # Execution details
    executed_at = models.DateTimeField(
        _('executed at'),
        null=True,
        blank=True,
    )
    anonymization_log = models.JSONField(
        _('anonymization log'),
        blank=True,
        default=dict,
        help_text=_('JSON log of what was anonymized'),
    )
    celery_task_id = models.CharField(
        _('celery task ID'),
        max_length=255,
        blank=True,
    )
    error_message = models.TextField(
        _('error message'),
        blank=True,
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('data deletion request')
        verbose_name_plural = _('data deletion requests')
        ordering = ['-created_at']

    def __str__(self):
        profile_name = self.profile.legal_name if self.profile else '[Deleted]'
        return f"Deletion request for {profile_name} ({self.status})"

    # FSM Transitions
    @state.transition(source=DeletionRequestStatus.REQUESTED, target=DeletionRequestStatus.PENDING_CONFIRMATION)
    def send_confirmation(self):
        """Send confirmation email to user."""
        pass

    @state.transition(source=DeletionRequestStatus.PENDING_CONFIRMATION, target=DeletionRequestStatus.UNDER_REVIEW)
    def confirm(self):
        """User confirmed the deletion request."""
        self.confirmed_at = timezone.now()

    @state.transition(source=DeletionRequestStatus.UNDER_REVIEW, target=DeletionRequestStatus.APPROVED)
    def approve(self, reviewer, notes=''):
        """Board approves the deletion request."""
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes

    @state.transition(source=DeletionRequestStatus.UNDER_REVIEW, target=DeletionRequestStatus.DENIED)
    def deny(self, reviewer, reason):
        """Board denies the deletion request."""
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.denial_reason = reason

    @state.transition(source=DeletionRequestStatus.APPROVED, target=DeletionRequestStatus.EXECUTING)
    def start_execution(self, task_id):
        """Begin executing the deletion."""
        self.celery_task_id = task_id

    @state.transition(source=DeletionRequestStatus.EXECUTING, target=DeletionRequestStatus.EXECUTED)
    def complete_execution(self, anonymization_log):
        """Mark deletion as complete."""
        self.executed_at = timezone.now()
        self.anonymization_log = anonymization_log

    @state.transition(source=DeletionRequestStatus.EXECUTING, target=DeletionRequestStatus.FAILED)
    def fail_execution(self, error_message):
        """Mark deletion as failed."""
        self.error_message = error_message

    @property
    def can_be_approved(self) -> bool:
        """Check if this request can be approved."""
        return self.status == DeletionRequestStatus.UNDER_REVIEW

    @property
    def can_be_denied(self) -> bool:
        """Check if this request can be denied."""
        return self.status == DeletionRequestStatus.UNDER_REVIEW


class AuditCategory(models.TextChoices):
    """Categories for audit log entries."""
    AUTH = 'AUTH', _('Authentication')
    DATA_ACCESS = 'DATA_ACCESS', _('Data Access')
    DATA_EXPORT = 'DATA_EXPORT', _('Data Export')
    DATA_DELETION = 'DATA_DELETION', _('Data Deletion')
    CONSENT = 'CONSENT', _('Consent')
    PROFILE = 'PROFILE', _('Profile')
    APPLICATION = 'APPLICATION', _('Application')
    ROLE = 'ROLE', _('Role')
    TEAM = 'TEAM', _('Team')
    GOOGLE_ACCESS = 'GOOGLE_ACCESS', _('Google Access')
    ADMIN = 'ADMIN', _('Admin')
    OTHER = 'OTHER', _('Other')


class AuditLog(models.Model):
    """
    Immutable audit log for GDPR compliance.

    Tracks all significant actions in the system.
    Cannot be modified or deleted after creation.
    """
    # Who did the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('user'),
        help_text=_('User who performed the action'),
    )

    # What profile was affected (if applicable)
    profile = models.ForeignKey(
        'members.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('profile'),
        help_text=_('Profile affected by the action'),
    )

    # Action details
    category = models.CharField(
        _('category'),
        max_length=20,
        choices=AuditCategory.choices,
        db_index=True,
    )
    action = models.CharField(
        _('action'),
        max_length=100,
        help_text=_('Short action identifier (e.g., "login", "export_requested")'),
    )
    description = models.TextField(
        _('description'),
        help_text=_('Human-readable description of what happened'),
    )

    # Request context
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        _('user agent'),
        blank=True,
    )
    extra_data = models.JSONField(
        _('extra data'),
        blank=True,
        default=dict,
        help_text=_('Additional structured data about the action'),
    )

    # Generic relation to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('content type'),
    )
    object_id = models.PositiveIntegerField(
        _('object ID'),
        null=True,
        blank=True,
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # Timestamp
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['profile', 'timestamp']),
            models.Index(fields=['category', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else 'System'
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {user_str}: {self.action}"

    def save(self, *args, **kwargs):
        """Prevent modification of existing audit log entries."""
        if self.pk:
            raise ValueError(_("Audit log entries cannot be modified."))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of audit log entries."""
        raise ValueError(_("Audit log entries cannot be deleted."))


def log_audit(
    action: str,
    description: str,
    category: str = AuditCategory.OTHER,
    user=None,
    profile=None,
    request=None,
    content_object=None,
    extra_data: dict = None,
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        action: Short action identifier (e.g., "login", "export_requested")
        description: Human-readable description
        category: AuditCategory value
        user: User who performed the action
        profile: Profile affected by the action
        request: HTTP request (for IP/user agent)
        content_object: Related model instance
        extra_data: Additional structured data

    Returns:
        The created AuditLog instance
    """
    log_entry = AuditLog(
        action=action,
        description=description,
        category=category,
        user=user,
        profile=profile,
        extra_data=extra_data or {},
    )

    # Extract request context
    if request:
        log_entry.ip_address = get_client_ip(request)
        log_entry.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

    # Set generic relation
    if content_object:
        log_entry.content_type = ContentType.objects.get_for_model(content_object)
        log_entry.object_id = content_object.pk

    log_entry.save()
    return log_entry


def get_client_ip(request) -> str | None:
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
