"""Views for the members app."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView

from apps.applications.models import Application, ApplicationStatus
from apps.documents.models import get_pending_documents_for_profile
from apps.members.forms import EditTagsForm
from apps.members.models import CommunityTag, MembershipStatus, ProfileTag


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Member dashboard - the main landing page after login.

    Shows different content based on membership status.
    """

    template_name = 'members/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['page_title'] = _('Dashboard')

        # Check if user has a profile
        profile = getattr(user, 'profile', None)
        context['profile'] = profile

        if profile:
            context['membership_status'] = profile.membership_status
            context['current_role'] = profile.current_role

            # Get active role assignment for expiry info
            from apps.members.models import RoleAssignment
            from django.utils import timezone
            active_assignment = profile.role_assignments.filter(
                is_active=True,
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date(),
            ).first()
            context['role_assignment'] = active_assignment

            # Get team memberships (for Phase 3)
            # context['teams'] = profile.team_memberships.filter(is_active=True)

            # Get pending documents
            context['pending_documents'] = get_pending_documents_for_profile(profile)
            context['pending_documents_count'] = len(context['pending_documents'])
        else:
            context['membership_status'] = MembershipStatus.NONE
            context['pending_documents'] = []
            context['pending_documents_count'] = 0

        # Get pending application if any
        pending_application = Application.objects.filter(
            user=user,
            status__in=[ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW]
        ).first()
        context['pending_application'] = pending_application

        # Get most recent application for status display
        latest_application = Application.objects.filter(user=user).order_by('-submitted_at').first()
        context['latest_application'] = latest_application

        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    """View and edit profile information."""

    template_name = 'members/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('My Profile')
        profile = getattr(self.request.user, 'profile', None)
        context['profile'] = profile

        if profile:
            # Get all tags for this profile (both self-assigned and admin-assigned)
            context['profile_tags'] = ProfileTag.objects.filter(
                profile=profile,
                tag__is_active=True,
            ).select_related('tag').order_by('tag__display_order', 'tag__name')

            # Check if there are self-assignable tags available
            context['has_self_assignable_tags'] = CommunityTag.objects.filter(
                is_self_assignable=True,
                is_active=True,
            ).exists()

        return context


class EditTagsView(LoginRequiredMixin, FormView):
    """View for members to edit their self-assignable tags."""

    template_name = 'members/edit_tags.html'
    form_class = EditTagsForm
    success_url = reverse_lazy('members:profile')

    def dispatch(self, request, *args, **kwargs):
        # Require a profile to edit tags
        if not hasattr(request.user, 'profile'):
            messages.error(request, _('You need a profile to manage tags.'))
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.request.user.profile
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Your tags have been updated.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Edit My Tags')
        context['profile'] = self.request.user.profile

        # Get admin-assigned tags (non-self-assignable)
        context['admin_tags'] = ProfileTag.objects.filter(
            profile=self.request.user.profile,
            tag__is_self_assignable=False,
            tag__is_active=True,
        ).select_related('tag').order_by('tag__display_order', 'tag__name')

        return context
