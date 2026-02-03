"""Admin configuration for GDPR app."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from .models import AuditLog, DataAccessRequest, DataDeletionRequest


@admin.register(DataAccessRequest)
class DataAccessRequestAdmin(SimpleHistoryAdmin):
    """Admin interface for DataAccessRequest model."""

    list_display = (
        'profile',
        'status_badge',
        'requested_by',
        'created_at',
        'expires_at',
        'download_count',
        'file_size_display',
    )
    list_filter = ('status', 'created_at', 'expires_at')
    search_fields = ('profile__legal_name', 'profile__user__email')
    readonly_fields = (
        'download_token',
        'download_count',
        'first_downloaded_at',
        'export_checksum',
        'celery_task_id',
        'created_at',
        'completed_at',
    )
    raw_id_fields = ('profile', 'requested_by')

    fieldsets = (
        (None, {
            'fields': ('profile', 'requested_by', 'status')
        }),
        (_('Export Details'), {
            'fields': (
                'export_file',
                'export_file_size',
                'export_checksum',
                'expires_at',
            ),
        }),
        (_('Download Tracking'), {
            'fields': (
                'download_token',
                'download_count',
                'first_downloaded_at',
            ),
        }),
        (_('Processing'), {
            'fields': ('celery_task_id', 'error_message'),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('Status'))
    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'PROCESSING': 'blue',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'EXPIRED': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.display(description=_('File Size'))
    def file_size_display(self, obj):
        if not obj.export_file_size:
            return '-'
        size = obj.export_file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(SimpleHistoryAdmin):
    """Admin interface for DataDeletionRequest model."""

    list_display = (
        'profile_display',
        'status_badge',
        'created_at',
        'confirmed_at',
        'reviewed_by',
        'reviewed_at',
        'executed_at',
    )
    list_filter = ('status', 'created_at', 'reviewed_at', 'executed_at')
    search_fields = ('profile__legal_name', 'profile__user__email')
    readonly_fields = (
        'profile_snapshot',
        'confirmation_token',
        'confirmed_at',
        'reviewed_at',
        'executed_at',
        'anonymization_log',
        'celery_task_id',
        'created_at',
        'updated_at',
    )
    raw_id_fields = ('profile', 'reviewed_by')

    fieldsets = (
        (None, {
            'fields': ('profile', 'status', 'request_reason')
        }),
        (_('Confirmation'), {
            'fields': ('confirmation_token', 'confirmed_at'),
        }),
        (_('Review'), {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes', 'denial_reason'),
        }),
        (_('Execution'), {
            'fields': ('executed_at', 'anonymization_log', 'celery_task_id', 'error_message'),
            'classes': ('collapse',),
        }),
        (_('Backup'), {
            'fields': ('profile_snapshot',),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['approve_selected', 'deny_selected']

    @admin.display(description=_('Profile'))
    def profile_display(self, obj):
        if obj.profile:
            return obj.profile.legal_name
        return '[Deleted]'

    @admin.display(description=_('Status'))
    def status_badge(self, obj):
        colors = {
            'REQUESTED': 'orange',
            'PENDING_CONFIRMATION': 'yellow',
            'UNDER_REVIEW': 'blue',
            'APPROVED': 'green',
            'DENIED': 'red',
            'EXECUTING': 'purple',
            'EXECUTED': 'darkgreen',
            'FAILED': 'darkred',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.action(description=_('Approve selected deletion requests'))
    def approve_selected(self, request, queryset):
        approved = 0
        for obj in queryset.filter(status='UNDER_REVIEW'):
            obj.approve(reviewer=request.user, notes='Approved via admin bulk action')
            obj.save()
            approved += 1
        self.message_user(request, f'{approved} request(s) approved.')

    @admin.action(description=_('Deny selected deletion requests'))
    def deny_selected(self, request, queryset):
        denied = 0
        for obj in queryset.filter(status='UNDER_REVIEW'):
            obj.deny(reviewer=request.user, reason='Denied via admin bulk action')
            obj.save()
            denied += 1
        self.message_user(request, f'{denied} request(s) denied.')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for AuditLog model.

    Read-only for compliance - audit logs cannot be modified or deleted.
    """

    list_display = (
        'timestamp',
        'user_display',
        'profile_display',
        'category',
        'action',
        'description_preview',
        'ip_address',
    )
    list_filter = ('category', 'action', 'timestamp')
    search_fields = (
        'user__email',
        'profile__legal_name',
        'action',
        'description',
        'ip_address',
    )
    readonly_fields = (
        'user',
        'profile',
        'category',
        'action',
        'description',
        'ip_address',
        'user_agent',
        'extra_data',
        'content_type',
        'object_id',
        'timestamp',
    )
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        """Audit logs are created by the system, not via admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs are immutable."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs cannot be deleted."""
        return False

    @admin.display(description=_('User'))
    def user_display(self, obj):
        if obj.user:
            return obj.user.email
        return 'System'

    @admin.display(description=_('Profile'))
    def profile_display(self, obj):
        if obj.profile:
            return obj.profile.legal_name
        return '-'

    @admin.display(description=_('Description'))
    def description_preview(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
