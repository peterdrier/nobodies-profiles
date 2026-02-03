"""Views for the GDPR app."""
import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from .forms import (
    ConfirmDeletionForm,
    RequestDeletionForm,
    RequestExportForm,
    ReviewDeletionForm,
)
from .models import (
    AuditCategory,
    AuditLog,
    DataAccessRequest,
    DataAccessRequestStatus,
    DataDeletionRequest,
    DeletionRequestStatus,
    log_audit,
)
from .tasks import execute_data_anonymization, generate_data_export


class BoardMemberRequiredMixin(UserPassesTestMixin):
    """Mixin that requires the user to be a board member."""

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        profile = getattr(self.request.user, 'profile', None)
        return profile and profile.is_board_member


# =============================================================================
# Member Self-Service Views
# =============================================================================


class MyDataView(LoginRequiredMixin, TemplateView):
    """GDPR dashboard for members to manage their data."""

    template_name = 'gdpr/my_data.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('My Data')
        profile = getattr(self.request.user, 'profile', None)
        context['profile'] = profile

        if profile:
            # Get recent export requests
            context['export_requests'] = DataAccessRequest.objects.filter(
                profile=profile
            ).order_by('-created_at')[:5]

            # Get any pending deletion request
            context['deletion_request'] = DataDeletionRequest.objects.filter(
                profile=profile
            ).exclude(
                status__in=[DeletionRequestStatus.EXECUTED, DeletionRequestStatus.DENIED]
            ).first()

            # Check if user can request a new export (rate limiting)
            recent_export = DataAccessRequest.objects.filter(
                profile=profile,
                created_at__gte=timezone.now() - timedelta(hours=settings.GDPR_EXPORT_RATE_LIMIT_HOURS),
            ).exists()
            context['can_request_export'] = not recent_export
            context['export_rate_limit_hours'] = settings.GDPR_EXPORT_RATE_LIMIT_HOURS

        return context


class RequestExportView(LoginRequiredMixin, FormView):
    """View for requesting a data export."""

    template_name = 'gdpr/request_export.html'
    form_class = RequestExportForm
    success_url = reverse_lazy('gdpr:my_data')

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'profile'):
            messages.error(request, _('You need a profile to request a data export.'))
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Request Data Export')
        context['expiry_days'] = settings.GDPR_EXPORT_EXPIRY_DAYS
        return context

    def form_valid(self, form):
        profile = self.request.user.profile

        # Check rate limiting
        recent_export = DataAccessRequest.objects.filter(
            profile=profile,
            created_at__gte=timezone.now() - timedelta(hours=settings.GDPR_EXPORT_RATE_LIMIT_HOURS),
        ).exists()

        if recent_export:
            messages.error(
                self.request,
                _('You can only request one data export every %(hours)s hours.') % {
                    'hours': settings.GDPR_EXPORT_RATE_LIMIT_HOURS
                }
            )
            return redirect('gdpr:my_data')

        # Create the request
        export_request = DataAccessRequest.objects.create(
            profile=profile,
            requested_by=self.request.user,
        )

        # Log the action
        log_audit(
            action='export_requested',
            description=f'Data export requested by {profile.legal_name}',
            category=AuditCategory.DATA_EXPORT,
            user=self.request.user,
            profile=profile,
            request=self.request,
            content_object=export_request,
        )

        # Queue the export generation
        generate_data_export.delay(export_request.id)

        messages.success(
            self.request,
            _('Your data export has been requested. You will receive an email when it is ready.')
        )
        return super().form_valid(form)


class DownloadExportView(LoginRequiredMixin, View):
    """View for downloading a data export."""

    def get(self, request, token):
        export_request = get_object_or_404(
            DataAccessRequest,
            download_token=token,
            profile__user=request.user,
        )

        if not export_request.is_downloadable:
            if export_request.is_expired:
                messages.error(request, _('This export has expired.'))
            else:
                messages.error(request, _('This export is not ready for download.'))
            return redirect('gdpr:my_data')

        # Update download tracking
        if export_request.download_count == 0:
            export_request.first_downloaded_at = timezone.now()
        export_request.download_count += 1
        export_request.save()

        # Log the download
        log_audit(
            action='export_downloaded',
            description=f'Data export downloaded by {export_request.profile.legal_name}',
            category=AuditCategory.DATA_EXPORT,
            user=request.user,
            profile=export_request.profile,
            request=request,
            content_object=export_request,
            extra_data={'download_count': export_request.download_count},
        )

        # Serve the file
        response = FileResponse(
            export_request.export_file.open('rb'),
            as_attachment=True,
            filename=f'data_export_{export_request.profile.id}.zip',
        )
        return response


class RequestDeletionView(LoginRequiredMixin, FormView):
    """View for requesting account deletion."""

    template_name = 'gdpr/request_deletion.html'
    form_class = RequestDeletionForm
    success_url = reverse_lazy('gdpr:my_data')

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'profile'):
            messages.error(request, _('You need a profile to request account deletion.'))
            return redirect('dashboard')

        # Check for existing pending request
        existing = DataDeletionRequest.objects.filter(
            profile=request.user.profile
        ).exclude(
            status__in=[DeletionRequestStatus.EXECUTED, DeletionRequestStatus.DENIED]
        ).first()

        if existing:
            messages.warning(
                request,
                _('You already have a pending deletion request.')
            )
            return redirect('gdpr:my_data')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Request Account Deletion')
        context['profile'] = self.request.user.profile
        return context

    def form_valid(self, form):
        profile = self.request.user.profile

        # Create profile snapshot before deletion
        snapshot = {
            'legal_name': profile.legal_name,
            'country_of_residence': profile.country_of_residence,
            'email': self.request.user.email,
            'created_at': profile.created_at.isoformat(),
        }

        # Create the request
        deletion_request = DataDeletionRequest.objects.create(
            profile=profile,
            profile_snapshot=snapshot,
            request_reason=form.cleaned_data.get('reason', ''),
        )

        # Send confirmation email
        deletion_request.send_confirmation()
        deletion_request.save()

        # Log the action
        log_audit(
            action='deletion_requested',
            description=f'Account deletion requested by {profile.legal_name}',
            category=AuditCategory.DATA_DELETION,
            user=self.request.user,
            profile=profile,
            request=self.request,
            content_object=deletion_request,
        )

        messages.success(
            self.request,
            _('Your deletion request has been submitted. Please check your email to confirm.')
        )
        return super().form_valid(form)


class ConfirmDeletionView(LoginRequiredMixin, FormView):
    """View for confirming deletion via email token."""

    template_name = 'gdpr/confirm_deletion.html'
    form_class = ConfirmDeletionForm
    success_url = reverse_lazy('gdpr:my_data')

    def dispatch(self, request, *args, **kwargs):
        self.deletion_request = get_object_or_404(
            DataDeletionRequest,
            confirmation_token=kwargs['token'],
            profile__user=request.user,
            status=DeletionRequestStatus.PENDING_CONFIRMATION,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Confirm Account Deletion')
        context['deletion_request'] = self.deletion_request
        return context

    def form_valid(self, form):
        self.deletion_request.confirm()
        self.deletion_request.save()

        # Log the action
        log_audit(
            action='deletion_confirmed',
            description=f'Deletion request confirmed by {self.deletion_request.profile.legal_name}',
            category=AuditCategory.DATA_DELETION,
            user=self.request.user,
            profile=self.deletion_request.profile,
            request=self.request,
            content_object=self.deletion_request,
        )

        messages.success(
            self.request,
            _('Your deletion request has been confirmed and is now under review by the board.')
        )
        return super().form_valid(form)


# =============================================================================
# Board Dashboard Views
# =============================================================================


class GDPRDashboardView(BoardMemberRequiredMixin, TemplateView):
    """GDPR dashboard for board members."""

    template_name = 'gdpr/board_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('GDPR Dashboard')

        # Pending deletion requests
        context['pending_deletions'] = DataDeletionRequest.objects.filter(
            status=DeletionRequestStatus.UNDER_REVIEW
        ).select_related('profile').order_by('created_at')

        # Recent export requests
        context['recent_exports'] = DataAccessRequest.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('profile').order_by('-created_at')[:10]

        # Statistics
        context['stats'] = {
            'total_exports': DataAccessRequest.objects.count(),
            'exports_this_month': DataAccessRequest.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
            'pending_deletions': context['pending_deletions'].count(),
            'executed_deletions': DataDeletionRequest.objects.filter(
                status=DeletionRequestStatus.EXECUTED
            ).count(),
        }

        return context


class DeletionRequestListView(BoardMemberRequiredMixin, ListView):
    """List view of all deletion requests for board members."""

    template_name = 'gdpr/deletion_request_list.html'
    context_object_name = 'deletion_requests'
    paginate_by = 20

    def get_queryset(self):
        queryset = DataDeletionRequest.objects.select_related(
            'profile', 'reviewed_by'
        ).order_by('-created_at')

        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Deletion Requests')
        context['status_choices'] = DeletionRequestStatus.choices
        context['current_status'] = self.request.GET.get('status', '')
        return context


class DeletionRequestDetailView(BoardMemberRequiredMixin, DetailView):
    """Detail view of a deletion request for board review."""

    template_name = 'gdpr/deletion_request_detail.html'
    context_object_name = 'deletion_request'

    def get_queryset(self):
        return DataDeletionRequest.objects.select_related('profile', 'reviewed_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Deletion Request Details')
        context['form'] = ReviewDeletionForm()
        return context


class ReviewDeletionView(BoardMemberRequiredMixin, FormView):
    """View for board members to approve or deny deletion requests."""

    template_name = 'gdpr/review_deletion.html'
    form_class = ReviewDeletionForm

    def dispatch(self, request, *args, **kwargs):
        self.deletion_request = get_object_or_404(
            DataDeletionRequest,
            pk=kwargs['pk'],
            status=DeletionRequestStatus.UNDER_REVIEW,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Review Deletion Request')
        context['deletion_request'] = self.deletion_request
        return context

    def form_valid(self, form):
        decision = form.cleaned_data['decision']
        notes = form.cleaned_data.get('notes', '')
        denial_reason = form.cleaned_data.get('denial_reason', '')

        if decision == 'approve':
            self.deletion_request.approve(
                reviewer=self.request.user,
                notes=notes,
            )
            self.deletion_request.save()

            # Queue the anonymization task
            execute_data_anonymization.delay(self.deletion_request.id)

            log_audit(
                action='deletion_approved',
                description=f'Deletion request approved for {self.deletion_request.profile.legal_name}',
                category=AuditCategory.DATA_DELETION,
                user=self.request.user,
                profile=self.deletion_request.profile,
                request=self.request,
                content_object=self.deletion_request,
            )

            messages.success(
                self.request,
                _('Deletion request approved. Anonymization will be executed.')
            )
        else:
            self.deletion_request.deny(
                reviewer=self.request.user,
                reason=denial_reason,
            )
            self.deletion_request.save()

            log_audit(
                action='deletion_denied',
                description=f'Deletion request denied for {self.deletion_request.profile.legal_name}',
                category=AuditCategory.DATA_DELETION,
                user=self.request.user,
                profile=self.deletion_request.profile,
                request=self.request,
                content_object=self.deletion_request,
                extra_data={'reason': denial_reason},
            )

            messages.success(
                self.request,
                _('Deletion request denied.')
            )

        return redirect('gdpr:deletion_request_list')


class AuditLogView(BoardMemberRequiredMixin, ListView):
    """Searchable audit log view for board members."""

    template_name = 'gdpr/audit_log.html'
    context_object_name = 'audit_logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = AuditLog.objects.select_related('user', 'profile').order_by('-timestamp')

        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # Filter by search term
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(description__icontains=search)

        # Filter by date range
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Audit Log')
        context['category_choices'] = AuditCategory.choices
        context['current_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context
