"""Admin configuration for applications app."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Application, ApplicationBatch, ApplicationStatus


class ApplicationResource(resources.ModelResource):
    """Import/Export resource for Application model."""

    class Meta:
        model = Application
        fields = (
            'id', 'user__email', 'legal_name', 'country_of_residence',
            'role_requested', 'status', 'submitted_at', 'reviewed_at'
        )
        export_order = fields


class ApplicationInline(admin.TabularInline):
    """Inline view of applications in a batch."""
    model = Application
    extra = 0
    readonly_fields = ('legal_name', 'role_requested', 'status', 'submitted_at')
    fields = ('legal_name', 'role_requested', 'status', 'submitted_at')
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ApplicationBatch)
class ApplicationBatchAdmin(admin.ModelAdmin):
    """Admin interface for ApplicationBatch model."""
    list_display = ('name', 'status', 'application_count', 'created_at', 'created_by')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'notes')
    readonly_fields = ('created_at',)
    inlines = [ApplicationInline]

    @admin.display(description=_('Applications'))
    def application_count(self, obj):
        return obj.applications.count()


@admin.register(Application)
class ApplicationAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    """Admin interface for Application model."""
    resource_class = ApplicationResource

    list_display = (
        'legal_name', 'user_email', 'role_requested', 'status_badge',
        'batch', 'submitted_at', 'reviewed_by'
    )
    list_filter = ('status', 'role_requested', 'batch', 'submitted_at', 'country_of_residence')
    search_fields = ('legal_name', 'user__email', 'motivation', 'skills')
    readonly_fields = (
        'submitted_at', 'reviewed_at', 'data_processing_consent_at',
        'data_processing_consent_ip'
    )
    raw_id_fields = ('user', 'batch', 'reviewed_by')
    date_hierarchy = 'submitted_at'

    fieldsets = (
        (_('Applicant'), {
            'fields': ('user', 'legal_name', 'preferred_name', 'country_of_residence', 'preferred_language')
        }),
        (_('Application'), {
            'fields': ('role_requested', 'motivation', 'skills', 'how_heard')
        }),
        (_('Event History'), {
            'fields': ('attended_before', 'attended_years'),
            'classes': ('collapse',),
        }),
        (_('Review'), {
            'fields': ('status', 'batch', 'reviewed_by', 'reviewed_at', 'review_notes')
        }),
        (_('GDPR Consent'), {
            'fields': ('data_processing_consent', 'data_processing_consent_at', 'data_processing_consent_ip'),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('submitted_at',),
            'classes': ('collapse',),
        }),
    )

    actions = ['assign_to_batch', 'start_review', 'approve_selected', 'reject_selected']

    @admin.display(description=_('Email'))
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description=_('Status'))
    def status_badge(self, obj):
        colors = {
            ApplicationStatus.SUBMITTED: '#6c757d',
            ApplicationStatus.UNDER_REVIEW: '#ffc107',
            ApplicationStatus.APPROVED: '#28a745',
            ApplicationStatus.REJECTED: '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.action(description=_('Start review for selected applications'))
    def start_review(self, request, queryset):
        count = 0
        for app in queryset.filter(status=ApplicationStatus.SUBMITTED):
            app.start_review(reviewer=request.user)
            app.save()
            count += 1
        self.message_user(request, f'{count} application(s) moved to review.')

    @admin.action(description=_('Approve selected applications'))
    def approve_selected(self, request, queryset):
        count = 0
        for app in queryset.filter(status=ApplicationStatus.UNDER_REVIEW):
            app.approve(reviewer=request.user)
            app.save()
            count += 1
        self.message_user(request, f'{count} application(s) approved.')

    @admin.action(description=_('Reject selected applications'))
    def reject_selected(self, request, queryset):
        count = 0
        for app in queryset.filter(status=ApplicationStatus.UNDER_REVIEW):
            app.reject(reviewer=request.user)
            app.save()
            count += 1
        self.message_user(request, f'{count} application(s) rejected.')

    @admin.action(description=_('Assign to new batch'))
    def assign_to_batch(self, request, queryset):
        # Create a new batch and assign selected applications
        batch = ApplicationBatch.objects.create(created_by=request.user)
        count = queryset.update(batch=batch)
        self.message_user(request, f'{count} application(s) assigned to {batch}.')
