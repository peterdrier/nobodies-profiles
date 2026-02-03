"""Views for the applications app."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, TemplateView

from .forms import ApplicationForm
from .models import Application, ApplicationStatus


class ApplicationCreateView(LoginRequiredMixin, CreateView):
    """View for submitting a new membership application."""

    model = Application
    form_class = ApplicationForm
    template_name = 'applications/application_form.html'
    success_url = reverse_lazy('applications:success')

    def dispatch(self, request, *args, **kwargs):
        # Check if user already has a pending or approved application
        if request.user.is_authenticated:
            existing = Application.objects.filter(
                user=request.user,
                status__in=[
                    ApplicationStatus.SUBMITTED,
                    ApplicationStatus.UNDER_REVIEW,
                    ApplicationStatus.APPROVED,
                ]
            ).first()

            if existing:
                if existing.status == ApplicationStatus.APPROVED:
                    messages.info(request, _('You already have an approved application.'))
                    return redirect('dashboard')
                else:
                    messages.info(request, _('You already have a pending application.'))
                    return redirect('applications:status', pk=existing.pk)

            # Check if user already has a profile (is already a member)
            if hasattr(request.user, 'profile'):
                messages.info(request, _('You are already a member.'))
                return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Set the user and GDPR consent details
        form.instance.user = self.request.user
        form.instance.data_processing_consent = True
        form.instance.data_processing_consent_at = timezone.now()
        form.instance.data_processing_consent_ip = self.get_client_ip()

        response = super().form_valid(form)

        messages.success(
            self.request,
            _('Your application has been submitted successfully. '
              'You will receive an email confirmation shortly.')
        )

        return response

    def get_client_ip(self):
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Apply for Membership')
        return context


class ApplicationSuccessView(LoginRequiredMixin, TemplateView):
    """Success page after submitting an application."""

    template_name = 'applications/application_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Application Submitted')

        # Get the most recent application
        context['application'] = Application.objects.filter(
            user=self.request.user
        ).order_by('-submitted_at').first()

        return context


class ApplicationStatusView(LoginRequiredMixin, DetailView):
    """View for checking application status."""

    model = Application
    template_name = 'applications/application_status.html'
    context_object_name = 'application'

    def get_queryset(self):
        # Users can only view their own applications
        return Application.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Application Status')
        return context
