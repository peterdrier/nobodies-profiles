"""Views for the members app."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from apps.applications.models import Application, ApplicationStatus
from apps.documents.models import get_pending_documents_for_profile
from apps.members.models import MembershipStatus


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
        context['profile'] = getattr(self.request.user, 'profile', None)
        return context
