"""Views for the documents app."""
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from apps.members.models import Profile

from .forms import ConsentForm
from .models import (
    ConsentRecord,
    DocumentTranslation,
    DocumentVersion,
    LegalDocument,
    get_pending_documents_for_profile,
)

logger = logging.getLogger(__name__)


class PendingDocumentsView(LoginRequiredMixin, ListView):
    """
    List of documents that require the user's consent.
    """
    template_name = 'documents/pending_list.html'
    context_object_name = 'pending_documents'

    def get_queryset(self):
        profile = getattr(self.request.user, 'profile', None)
        if not profile:
            return []
        return get_pending_documents_for_profile(profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Documents Requiring Signature')
        return context


class DocumentDetailView(LoginRequiredMixin, DetailView):
    """
    View a document with option to consent.
    """
    template_name = 'documents/document_detail.html'
    context_object_name = 'document'

    def get_object(self):
        slug = self.kwargs.get('slug')
        document = get_object_or_404(LegalDocument, slug=slug, is_active=True)
        return document

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object
        version = document.current_version

        if not version:
            raise Http404("No current version available")

        context['version'] = version
        context['page_title'] = document.title

        # Get requested language (default to Spanish)
        lang = self.request.GET.get('lang', 'es')
        context['current_language'] = lang

        if lang == 'es':
            context['content'] = version.spanish_content
            context['is_translation'] = False
        else:
            translation = DocumentTranslation.objects.filter(
                document_version=version,
                language_code=lang,
            ).first()
            if translation:
                context['content'] = translation.content
                context['is_translation'] = True
                context['is_machine_translated'] = translation.is_machine_translated
            else:
                # Fallback to Spanish
                context['content'] = version.spanish_content
                context['is_translation'] = False
                context['current_language'] = 'es'

        # Get available languages
        context['available_languages'] = [('es', _('Spanish (Legal)'))]
        for trans in version.translations.all():
            context['available_languages'].append(
                (trans.language_code, trans.get_language_code_display())
            )

        # Check if user has already consented
        profile = getattr(self.request.user, 'profile', None)
        if profile:
            context['has_consented'] = ConsentRecord.objects.filter(
                profile=profile,
                document_version=version,
                is_active=True,
            ).exists()

            # Check if this document is required for the user
            pending = get_pending_documents_for_profile(profile)
            context['is_required'] = any(
                item['document'].pk == document.pk for item in pending
            )
        else:
            context['has_consented'] = False
            context['is_required'] = False

        return context


class ConsentView(LoginRequiredMixin, FormView):
    """
    View for recording consent to a document.
    """
    template_name = 'documents/consent_form.html'
    form_class = ConsentForm

    def dispatch(self, request, *args, **kwargs):
        # Ensure user has a profile
        if not hasattr(request.user, 'profile'):
            messages.error(request, _('You need an approved membership to sign documents.'))
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_document_and_version(self):
        slug = self.kwargs.get('slug')
        document = get_object_or_404(LegalDocument, slug=slug, is_active=True)
        version = document.current_version
        if not version:
            raise Http404("No current version available")
        return document, version

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        document, version = self.get_document_and_version()
        kwargs['document'] = document
        kwargs['version'] = version
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document, version = self.get_document_and_version()
        context['document'] = document
        context['version'] = version
        context['page_title'] = _('Sign Document: {}').format(document.title)

        # Get language from query param or session
        lang = self.request.GET.get('lang', 'es')
        context['language_viewed'] = lang

        return context

    def form_valid(self, form):
        document, version = self.get_document_and_version()
        profile = self.request.user.profile

        # Check if already consented
        existing = ConsentRecord.objects.filter(
            profile=profile,
            document_version=version,
            is_active=True,
        ).exists()

        if existing:
            messages.info(self.request, _('You have already signed this document.'))
            return redirect('documents:detail', slug=document.slug)

        # Get language viewed
        lang = self.request.GET.get('lang', 'es')

        # Create consent record
        ConsentRecord.objects.create(
            profile=profile,
            document_version=version,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:500],
            consent_text_shown=form.get_consent_text(),
            language_viewed=lang,
        )

        logger.info(f"Consent recorded: {profile} signed {document.slug} v{version.version_number}")

        messages.success(
            self.request,
            _('Thank you for signing "{}". Your consent has been recorded.').format(document.title)
        )

        # Check if there are more documents to sign
        pending = get_pending_documents_for_profile(profile)
        if pending:
            return redirect('documents:pending')

        return redirect('dashboard')

    def get_client_ip(self):
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def get_success_url(self):
        return reverse('dashboard')


class ConsentHistoryView(LoginRequiredMixin, ListView):
    """
    View user's consent history.
    """
    template_name = 'documents/consent_history.html'
    context_object_name = 'consents'
    paginate_by = 20

    def get_queryset(self):
        profile = getattr(self.request.user, 'profile', None)
        if not profile:
            return ConsentRecord.objects.none()
        return ConsentRecord.objects.filter(profile=profile).select_related(
            'document_version__document'
        ).order_by('-consented_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('My Consent History')
        return context
