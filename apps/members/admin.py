"""Admin configuration for members app."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Profile, RoleAssignment, Team, TeamMembership


class ProfileResource(resources.ModelResource):
    """Import/Export resource for Profile model."""

    class Meta:
        model = Profile
        fields = ('id', 'user__email', 'legal_name', 'country_of_residence', 'created_at')
        export_order = fields


class RoleAssignmentInline(admin.TabularInline):
    """Inline admin for role assignments."""
    model = RoleAssignment
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('role', 'start_date', 'end_date', 'is_active', 'assigned_by', 'notes', 'created_at')


@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    """Admin interface for Profile model."""
    resource_class = ProfileResource
    list_display = ('legal_name', 'user_email', 'country_of_residence', 'current_role', 'status', 'created_at')
    list_filter = ('country_of_residence', 'created_at')
    search_fields = ('legal_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'membership_status')
    inlines = [RoleAssignmentInline]

    fieldsets = (
        (None, {
            'fields': ('user', 'legal_name', 'country_of_residence')
        }),
        (_('Status'), {
            'fields': ('membership_status',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('Email'))
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description=_('Current Role'))
    def current_role(self, obj):
        return obj.current_role or '-'

    @admin.display(description=_('Status'))
    def status(self, obj):
        return obj.membership_status


class RoleAssignmentResource(resources.ModelResource):
    """Import/Export resource for RoleAssignment model."""

    class Meta:
        model = RoleAssignment
        fields = ('id', 'profile__legal_name', 'role', 'start_date', 'end_date', 'is_active')


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    """Admin interface for RoleAssignment model."""
    resource_class = RoleAssignmentResource
    list_display = ('profile', 'role', 'start_date', 'end_date', 'is_active', 'days_remaining')
    list_filter = ('role', 'is_active', 'start_date', 'end_date')
    search_fields = ('profile__legal_name', 'profile__user__email')
    readonly_fields = ('created_at',)
    raw_id_fields = ('profile', 'assigned_by')

    @admin.display(description=_('Days Remaining'))
    def days_remaining(self, obj):
        days = obj.days_until_expiry
        if days is None:
            return '-'
        if days <= 30:
            return f'⚠️ {days}'
        return days


class TeamMembershipInline(admin.TabularInline):
    """Inline admin for team memberships."""
    model = TeamMembership
    extra = 0
    readonly_fields = ('joined_at', 'left_at')
    fields = ('profile', 'role_in_team', 'is_active', 'added_by', 'joined_at', 'left_at')
    raw_id_fields = ('profile', 'added_by')


@admin.register(Team)
class TeamAdmin(SimpleHistoryAdmin):
    """Admin interface for Team model."""
    list_display = ('name', 'slug', 'member_count', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TeamMembershipInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('Members'))
    def member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


@admin.register(TeamMembership)
class TeamMembershipAdmin(SimpleHistoryAdmin):
    """Admin interface for TeamMembership model."""
    list_display = ('profile', 'team', 'role_in_team', 'is_active', 'joined_at')
    list_filter = ('team', 'role_in_team', 'is_active')
    search_fields = ('profile__legal_name', 'profile__user__email', 'team__name')
    raw_id_fields = ('profile', 'added_by')
    readonly_fields = ('joined_at', 'left_at')
