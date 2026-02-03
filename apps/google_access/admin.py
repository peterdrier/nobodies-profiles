"""
Admin interface for Google access management.
"""
from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    GoogleResource,
    RoleGoogleAccess,
    TeamGoogleAccess,
    GooglePermission,
    GooglePermissionLog,
)


@admin.register(GoogleResource)
class GoogleResourceAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'resource_type', 'google_id_short', 'is_active', 'created_at']
    list_filter = ['resource_type', 'is_active']
    search_fields = ['name', 'google_id', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('name', 'resource_type', 'google_id', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def google_id_short(self, obj):
        """Show truncated Google ID."""
        if len(obj.google_id) > 20:
            return f"{obj.google_id[:20]}..."
        return obj.google_id
    google_id_short.short_description = 'Google ID'


@admin.register(RoleGoogleAccess)
class RoleGoogleAccessAdmin(SimpleHistoryAdmin):
    list_display = ['role', 'resource', 'permission_role', 'is_active']
    list_filter = ['role', 'permission_role', 'is_active']
    search_fields = ['resource__name']
    autocomplete_fields = ['resource']


@admin.register(TeamGoogleAccess)
class TeamGoogleAccessAdmin(SimpleHistoryAdmin):
    list_display = ['team', 'resource', 'permission_role', 'is_active']
    list_filter = ['permission_role', 'is_active']
    search_fields = ['team__name', 'resource__name']
    autocomplete_fields = ['team', 'resource']


@admin.register(GooglePermission)
class GooglePermissionAdmin(admin.ModelAdmin):
    list_display = [
        'profile',
        'resource',
        'permission_role',
        'granted_via',
        'is_active',
        'granted_at',
    ]
    list_filter = ['permission_role', 'granted_via', 'is_active']
    search_fields = ['profile__legal_name', 'profile__user__email', 'resource__name']
    readonly_fields = [
        'profile',
        'resource',
        'permission_id',
        'permission_role',
        'granted_via',
        'team',
        'granted_at',
        'revoked_at',
    ]
    date_hierarchy = 'granted_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(GooglePermissionLog)
class GooglePermissionLogAdmin(admin.ModelAdmin):
    list_display = [
        'profile',
        'resource',
        'operation',
        'status_badge',
        'triggered_by',
        'created_at',
    ]
    list_filter = ['operation', 'status', 'triggered_by']
    search_fields = ['profile__legal_name', 'profile__user__email', 'resource__name']
    readonly_fields = [
        'profile',
        'resource',
        'operation',
        'permission_role',
        'status',
        'permission_id',
        'error_message',
        'retry_count',
        'triggered_by',
        'created_at',
        'completed_at',
    ]
    date_hierarchy = 'created_at'

    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'SUCCESS': 'green',
            'FAILED': 'red',
            'RETRYING': 'blue',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.status,
        )
    status_badge.short_description = 'Status'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
