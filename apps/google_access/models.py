"""
Google Access models for managing Drive permissions.

Tracks Google Drive resources, permission mappings, and audit logs.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class ResourceType(models.TextChoices):
    """Types of Google Drive resources."""
    SHARED_DRIVE = 'SHARED_DRIVE', _('Shared Drive')
    FOLDER = 'FOLDER', _('Folder')
    FILE = 'FILE', _('File')


class PermissionRole(models.TextChoices):
    """Google Drive permission roles."""
    READER = 'reader', _('Reader')
    COMMENTER = 'commenter', _('Commenter')
    WRITER = 'writer', _('Writer')
    ORGANIZER = 'organizer', _('Organizer')  # Shared Drive only
    FILE_ORGANIZER = 'fileOrganizer', _('File Organizer')  # Shared Drive only


class GoogleResource(models.Model):
    """
    Represents a Google Drive resource that can be shared.

    Can be a Shared Drive, folder, or file.
    """
    name = models.CharField(
        _('name'),
        max_length=255,
        help_text=_('Human-readable name for this resource'),
    )
    resource_type = models.CharField(
        _('resource type'),
        max_length=20,
        choices=ResourceType.choices,
    )
    google_id = models.CharField(
        _('Google ID'),
        max_length=255,
        unique=True,
        help_text=_('Google Drive ID (from the URL or API)'),
    )
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('What this resource is used for'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Inactive resources are not included in provisioning'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Google resource')
        verbose_name_plural = _('Google resources')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_resource_type_display()})"


class RoleGoogleAccess(models.Model):
    """
    Maps membership roles to Google resources.

    All active members with a given role will receive access to
    the specified resource with the specified permission level.
    """
    role = models.CharField(
        _('role'),
        max_length=20,
        help_text=_('Membership role that grants this access'),
    )
    resource = models.ForeignKey(
        GoogleResource,
        on_delete=models.CASCADE,
        related_name='role_access_rules',
        verbose_name=_('resource'),
    )
    permission_role = models.CharField(
        _('permission role'),
        max_length=20,
        choices=PermissionRole.choices,
        default=PermissionRole.READER,
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('role Google access')
        verbose_name_plural = _('role Google access rules')
        unique_together = ['role', 'resource']

    def __str__(self):
        return f"{self.role} → {self.resource.name} ({self.permission_role})"


class TeamGoogleAccess(models.Model):
    """
    Maps teams to Google resources.

    All active members of a team will receive access to
    the specified resource with the specified permission level.
    """
    team = models.ForeignKey(
        'members.Team',
        on_delete=models.CASCADE,
        related_name='google_access_rules',
        verbose_name=_('team'),
    )
    resource = models.ForeignKey(
        GoogleResource,
        on_delete=models.CASCADE,
        related_name='team_access_rules',
        verbose_name=_('resource'),
    )
    permission_role = models.CharField(
        _('permission role'),
        max_length=20,
        choices=PermissionRole.choices,
        default=PermissionRole.READER,
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('team Google access')
        verbose_name_plural = _('team Google access rules')
        unique_together = ['team', 'resource']

    def __str__(self):
        return f"{self.team.name} → {self.resource.name} ({self.permission_role})"


class GooglePermission(models.Model):
    """
    Tracks a granted Google Drive permission.

    Stores the permission ID returned by Google for later revocation.
    """
    profile = models.ForeignKey(
        'members.Profile',
        on_delete=models.CASCADE,
        related_name='google_permissions',
        verbose_name=_('profile'),
    )
    resource = models.ForeignKey(
        GoogleResource,
        on_delete=models.CASCADE,
        related_name='permissions',
        verbose_name=_('resource'),
    )
    permission_id = models.CharField(
        _('Google permission ID'),
        max_length=255,
        help_text=_('Permission ID returned by Google API'),
    )
    permission_role = models.CharField(
        _('permission role'),
        max_length=20,
        choices=PermissionRole.choices,
    )
    granted_via = models.CharField(
        _('granted via'),
        max_length=20,
        choices=[
            ('ROLE', _('Role-based')),
            ('TEAM', _('Team-based')),
            ('MANUAL', _('Manual')),
        ],
        default='ROLE',
    )
    team = models.ForeignKey(
        'members.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions',
        verbose_name=_('team'),
        help_text=_('If granted via team, which team'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
    )
    granted_at = models.DateTimeField(_('granted at'), auto_now_add=True)
    revoked_at = models.DateTimeField(_('revoked at'), null=True, blank=True)

    class Meta:
        verbose_name = _('Google permission')
        verbose_name_plural = _('Google permissions')
        ordering = ['-granted_at']

    def __str__(self):
        status = 'active' if self.is_active else 'revoked'
        return f"{self.profile.legal_name} → {self.resource.name} ({status})"


class OperationType(models.TextChoices):
    """Types of permission operations."""
    GRANT = 'GRANT', _('Grant')
    REVOKE = 'REVOKE', _('Revoke')
    RECONCILE_GRANT = 'RECONCILE_GRANT', _('Reconcile Grant')
    RECONCILE_REVOKE = 'RECONCILE_REVOKE', _('Reconcile Revoke')


class OperationStatus(models.TextChoices):
    """Status of a permission operation."""
    PENDING = 'PENDING', _('Pending')
    SUCCESS = 'SUCCESS', _('Success')
    FAILED = 'FAILED', _('Failed')
    RETRYING = 'RETRYING', _('Retrying')


class GooglePermissionLog(models.Model):
    """
    Audit log for Google permission operations.

    Records all grant/revoke attempts for compliance and debugging.
    """
    profile = models.ForeignKey(
        'members.Profile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='google_permission_logs',
        verbose_name=_('profile'),
    )
    resource = models.ForeignKey(
        GoogleResource,
        on_delete=models.SET_NULL,
        null=True,
        related_name='permission_logs',
        verbose_name=_('resource'),
    )
    operation = models.CharField(
        _('operation'),
        max_length=20,
        choices=OperationType.choices,
    )
    permission_role = models.CharField(
        _('permission role'),
        max_length=20,
        choices=PermissionRole.choices,
        null=True,
        blank=True,
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=OperationStatus.choices,
        default=OperationStatus.PENDING,
    )
    permission_id = models.CharField(
        _('permission ID'),
        max_length=255,
        blank=True,
        help_text=_('Permission ID if operation succeeded'),
    )
    error_message = models.TextField(
        _('error message'),
        blank=True,
    )
    retry_count = models.PositiveIntegerField(
        _('retry count'),
        default=0,
    )
    triggered_by = models.CharField(
        _('triggered by'),
        max_length=50,
        blank=True,
        help_text=_('What triggered this operation (e.g., "status_change", "reconciliation")'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)

    class Meta:
        verbose_name = _('Google permission log')
        verbose_name_plural = _('Google permission logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['profile', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        profile_name = self.profile.legal_name if self.profile else 'Unknown'
        resource_name = self.resource.name if self.resource else 'Unknown'
        return f"{self.operation} {profile_name} → {resource_name} ({self.status})"
