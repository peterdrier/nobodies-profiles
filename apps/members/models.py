"""
Member models for Nobodies Profiles.

Includes Profile (membership data) and RoleAssignment (role tracking).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Role(models.TextChoices):
    """Membership roles as defined in the statutes."""
    COLABORADOR = 'COLABORADOR', _('Colaborador')
    ASOCIADO = 'ASOCIADO', _('Asociado')
    BOARD_MEMBER = 'BOARD_MEMBER', _('Board Member')


class MembershipStatus(models.TextChoices):
    """Computed membership status values."""
    NONE = 'NONE', _('No membership')
    PENDING = 'PENDING', _('Application pending')
    APPROVED_PENDING_DOCUMENTS = 'APPROVED_PENDING_DOCUMENTS', _('Approved - pending documents')
    ACTIVE = 'ACTIVE', _('Active member')
    RESTRICTED = 'RESTRICTED', _('Restricted - missing consent')
    EXPIRED = 'EXPIRED', _('Membership expired')
    REMOVED = 'REMOVED', _('Removed by board')


class Profile(models.Model):
    """
    Member profile containing association-specific data.

    Linked to the User model for authentication.
    membership_status is computed from role assignments and document compliance.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('user'),
    )
    legal_name = models.CharField(
        _('legal name'),
        max_length=255,
        help_text=_('Full legal name as required by Art. 26 of the statutes'),
    )
    country_of_residence = models.CharField(
        _('country of residence'),
        max_length=2,
        help_text=_('ISO 3166-1 alpha-2 country code'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('profile')
        verbose_name_plural = _('profiles')

    def __str__(self):
        return f"{self.legal_name} ({self.user.email})"

    @property
    def membership_status(self) -> str:
        """
        Compute membership status from role assignments and document compliance.

        Status logic:
        1. If no active role assignment → check for pending application → PENDING or NONE
        2. If has active role but missing required documents → APPROVED_PENDING_DOCUMENTS
        3. If has active role and all documents signed → ACTIVE
        4. If past re-consent deadline → RESTRICTED
        5. If role assignment expired → EXPIRED
        6. If removed by board → REMOVED
        """
        # Check for active role assignment
        active_role = self.role_assignments.filter(
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
        ).first()

        if not active_role:
            # Check if there's a pending application
            if hasattr(self, 'user') and hasattr(self.user, 'applications'):
                pending_app = self.user.applications.filter(
                    status__in=['SUBMITTED', 'UNDER_REVIEW']
                ).exists()
                if pending_app:
                    return MembershipStatus.PENDING

            # Check if role expired
            expired_role = self.role_assignments.filter(
                is_active=False,
                end_date__lt=timezone.now().date(),
            ).exists()
            if expired_role:
                return MembershipStatus.EXPIRED

            # Check if removed
            removed = self.role_assignments.filter(
                is_active=False,
                notes__icontains='removed',
            ).exists()
            if removed:
                return MembershipStatus.REMOVED

            return MembershipStatus.NONE

        # Has active role - check document compliance
        # This will be implemented fully in Phase 2 with the documents app
        # For now, assume documents are pending if profile was just created
        if not self._has_all_required_consents():
            return MembershipStatus.APPROVED_PENDING_DOCUMENTS

        # Check for overdue re-consent
        if self._has_overdue_reconsent():
            return MembershipStatus.RESTRICTED

        return MembershipStatus.ACTIVE

    def _has_all_required_consents(self) -> bool:
        """
        Check if profile has all required document consents.
        Placeholder - will be implemented in Phase 2.
        """
        # TODO: Implement when documents app is created
        # For now, return True to allow testing
        return True

    def _has_overdue_reconsent(self) -> bool:
        """
        Check if profile has any overdue re-consent deadlines.
        Placeholder - will be implemented in Phase 2.
        """
        # TODO: Implement when documents app is created
        return False

    @property
    def current_role(self) -> str | None:
        """Get the current active role, if any."""
        active_assignment = self.role_assignments.filter(
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
        ).first()
        return active_assignment.role if active_assignment else None

    @property
    def is_board_member(self) -> bool:
        """Check if this profile belongs to a board member."""
        return self.current_role == Role.BOARD_MEMBER


class RoleAssignment(models.Model):
    """
    Tracks role assignments for members.

    Roles are time-limited (2 years per Art. 20.3 of the statutes).
    Historical records are kept for audit purposes.
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='role_assignments',
        verbose_name=_('profile'),
    )
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices,
    )
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(
        _('end date'),
        help_text=_('Typically start_date + 2 years'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Set to False when expired or revoked'),
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments_made',
        verbose_name=_('assigned by'),
    )
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('role assignment')
        verbose_name_plural = _('role assignments')
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.profile.legal_name} - {self.get_role_display()} ({self.start_date} to {self.end_date})"

    def save(self, *args, **kwargs):
        # Auto-set end_date if not provided (2 years from start)
        if not self.end_date and self.start_date:
            from dateutil.relativedelta import relativedelta
            self.end_date = self.start_date + relativedelta(years=2)
        super().save(*args, **kwargs)

    @property
    def is_current(self) -> bool:
        """Check if this assignment is currently valid."""
        today = timezone.now().date()
        return (
            self.is_active and
            self.start_date <= today <= self.end_date
        )

    @property
    def days_until_expiry(self) -> int | None:
        """Get days until this assignment expires, or None if expired/inactive."""
        if not self.is_active:
            return None
        today = timezone.now().date()
        if today > self.end_date:
            return None
        return (self.end_date - today).days
