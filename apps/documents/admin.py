"""Admin configuration for documents app."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    ConsentRecord,
    ConsentRevocation,
    DocumentTranslation,
    DocumentVersion,
    LegalDocument,
)


class DocumentVersionInline(admin.TabularInline):
    """Inline admin for document versions."""
    model = DocumentVersion
    extra = 0
    readonly_fields = ('content_hash', 'created_at', 'synced_at')
    fields = (
        'version_number', 'effective_date', 'is_current',
        'requires_re_consent', 're_consent_deadline', 'created_at'
    )
    show_change_link = True


class DocumentTranslationInline(admin.TabularInline):
    """Inline admin for translations."""
    model = DocumentTranslation
    extra = 0
    fields = ('language_code', 'is_machine_translated', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    """Admin for LegalDocument model."""
    list_display = (
        'title', 'slug', 'document_type', 'is_required_for_activation',
        'current_version_display', 'is_active', 'display_order'
    )
    list_filter = ('document_type', 'is_required_for_activation', 'is_active')
    search_fields = ('title', 'slug', 'description')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('display_order', 'title')
    inlines = [DocumentVersionInline]

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'document_type', 'description')
        }),
        (_('Requirements'), {
            'fields': ('is_required_for_activation', 'required_for_roles', 'display_order')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
    )

    @admin.display(description=_('Current Version'))
    def current_version_display(self, obj):
        version = obj.current_version
        if version:
            return f"v{version.version_number}"
        return '-'


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    """Admin for DocumentVersion model."""
    list_display = (
        'document', 'version_number', 'effective_date', 'is_current',
        'requires_re_consent', 're_consent_deadline', 'consent_count'
    )
    list_filter = ('document', 'is_current', 'requires_re_consent', 'effective_date')
    search_fields = ('document__title', 'version_number', 'changelog')
    readonly_fields = ('content_hash', 'synced_at', 'created_at')
    raw_id_fields = ('created_by',)
    inlines = [DocumentTranslationInline]

    fieldsets = (
        (None, {
            'fields': ('document', 'version_number', 'effective_date', 'is_current')
        }),
        (_('Content'), {
            'fields': ('spanish_content', 'content_hash', 'changelog'),
            'classes': ('collapse',),
        }),
        (_('Git Provenance'), {
            'fields': ('git_commit_sha', 'git_file_path', 'synced_at'),
            'classes': ('collapse',),
        }),
        (_('Re-consent'), {
            'fields': ('requires_re_consent', 're_consent_deadline')
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('Consents'))
    def consent_count(self, obj):
        active = obj.consents.filter(is_active=True).count()
        total = obj.consents.count()
        return f"{active} / {total}"

    actions = ['mark_as_current', 'trigger_re_consent']

    @admin.action(description=_('Mark selected as current version'))
    def mark_as_current(self, request, queryset):
        for version in queryset:
            version.is_current = True
            version.save()
        self.message_user(request, f'{queryset.count()} version(s) marked as current.')

    @admin.action(description=_('Trigger re-consent campaign'))
    def trigger_re_consent(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta

        count = 0
        for version in queryset:
            if not version.requires_re_consent:
                version.requires_re_consent = True
                version.re_consent_deadline = timezone.now().date() + timedelta(days=30)
                version.save()
                count += 1
                # TODO: Trigger notification task

        self.message_user(request, f'{count} version(s) set to require re-consent.')


@admin.register(DocumentTranslation)
class DocumentTranslationAdmin(admin.ModelAdmin):
    """Admin for DocumentTranslation model."""
    list_display = ('document_version', 'language_code', 'is_machine_translated', 'updated_at')
    list_filter = ('language_code', 'is_machine_translated')
    search_fields = ('document_version__document__title',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    """Admin for ConsentRecord model (read-only for immutability)."""
    list_display = (
        'profile', 'document_version', 'consented_at',
        'language_viewed', 'is_active', 'status_badge'
    )
    list_filter = ('is_active', 'language_viewed', 'document_version__document', 'consented_at')
    search_fields = ('profile__legal_name', 'profile__user__email')
    readonly_fields = (
        'profile', 'document_version', 'consented_at', 'ip_address',
        'user_agent', 'consent_text_shown', 'language_viewed', 'is_active'
    )
    date_hierarchy = 'consented_at'

    def has_add_permission(self, request):
        return False  # Consents created via UI only

    def has_change_permission(self, request, obj=None):
        return False  # Immutable

    def has_delete_permission(self, request, obj=None):
        return False  # Never delete

    @admin.display(description=_('Status'))
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green;">Active</span>'
            )
        if hasattr(obj, 'revocation'):
            return format_html(
                '<span style="color: red;">Revoked</span>'
            )
        return format_html(
            '<span style="color: orange;">Superseded</span>'
        )


@admin.register(ConsentRevocation)
class ConsentRevocationAdmin(admin.ModelAdmin):
    """Admin for ConsentRevocation model."""
    list_display = ('consent_record', 'revoked_at', 'revoked_by', 'reason_preview')
    list_filter = ('revoked_at',)
    search_fields = ('consent_record__profile__legal_name', 'reason')
    readonly_fields = ('consent_record', 'revoked_at')
    raw_id_fields = ('revoked_by',)

    @admin.display(description=_('Reason'))
    def reason_preview(self, obj):
        if len(obj.reason) > 50:
            return f"{obj.reason[:50]}..."
        return obj.reason
