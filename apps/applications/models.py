"""
Application models for membership applications.

Uses django-fsm for state machine workflow.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from simple_history.models import HistoricalRecords

from apps.members.models import Profile, Role, RoleAssignment


class ApplicationBatchStatus(models.TextChoices):
    """Status choices for application batches."""
    OPEN = 'OPEN', _('Open')
    IN_REVIEW = 'IN_REVIEW', _('In Review')
    CLOSED = 'CLOSED', _('Closed')


class ApplicationBatch(models.Model):
    """
    Groups applications for board review sessions.

    Allows the board to review multiple applications together.
    """
    name = models.CharField(
        _('name'),
        max_length=255,
        blank=True,
        help_text=_('e.g., "January 2026 Review"'),
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=ApplicationBatchStatus.choices,
        default=ApplicationBatchStatus.OPEN,
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_batches',
        verbose_name=_('created by'),
    )
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        verbose_name = _('application batch')
        verbose_name_plural = _('application batches')
        ordering = ['-created_at']

    def __str__(self):
        return self.name or f"Batch {self.pk} ({self.created_at.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        # Auto-generate name if not provided
        if not self.name:
            self.name = f"Review Batch - {timezone.now().strftime('%B %Y')}"
        super().save(*args, **kwargs)


class ApplicationStatus(models.TextChoices):
    """Status choices for applications."""
    SUBMITTED = 'SUBMITTED', _('Submitted')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')


class Application(models.Model):
    """
    Membership application with FSM workflow.

    Tracks the application from submission through board review.
    On approval, creates Profile and RoleAssignment records.
    """
    # Applicant
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name=_('user'),
    )

    # Application data
    legal_name = models.CharField(
        _('legal name'),
        max_length=255,
        help_text=_('Your full legal name'),
    )
    preferred_name = models.CharField(
        _('preferred name'),
        max_length=255,
        blank=True,
        help_text=_('Name you prefer to be called (optional)'),
    )
    country_of_residence = models.CharField(
        _('country of residence'),
        max_length=2,
        help_text=_('ISO 3166-1 alpha-2 country code'),
    )
    preferred_language = models.CharField(
        _('preferred language'),
        max_length=5,
        default='en',
        help_text=_('Language for communications'),
    )
    role_requested = models.CharField(
        _('role requested'),
        max_length=20,
        choices=[
            (Role.COLABORADOR, _('Colaborador (volunteer)')),
            (Role.ASOCIADO, _('Asociado (full member)')),
        ],
        default=Role.COLABORADOR,
    )

    # Additional info
    how_heard = models.TextField(
        _('how did you hear about us'),
        blank=True,
    )
    motivation = models.TextField(
        _('motivation'),
        help_text=_('Why do you want to join Nobodies Collective?'),
    )
    attended_before = models.BooleanField(
        _('attended event before'),
        default=False,
    )
    attended_years = models.CharField(
        _('years attended'),
        max_length=255,
        blank=True,
        help_text=_('e.g., "2019, 2022, 2023"'),
    )
    skills = models.TextField(
        _('skills'),
        blank=True,
        help_text=_('Skills or experience you can contribute'),
    )

    # Workflow
    status = FSMField(
        default=ApplicationStatus.SUBMITTED,
        verbose_name=_('status'),
    )

    batch = models.ForeignKey(
        ApplicationBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
        verbose_name=_('review batch'),
    )
    submitted_at = models.DateTimeField(_('submitted at'), auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications',
        verbose_name=_('reviewed by'),
    )
    reviewed_at = models.DateTimeField(_('reviewed at'), null=True, blank=True)
    review_notes = models.TextField(_('review notes'), blank=True)

    # GDPR consent for application processing
    data_processing_consent = models.BooleanField(
        _('data processing consent'),
        default=False,
        help_text=_('Consent to process personal data for this application'),
    )
    data_processing_consent_at = models.DateTimeField(
        _('consent timestamp'),
        null=True,
        blank=True,
    )
    data_processing_consent_ip = models.GenericIPAddressField(
        _('consent IP address'),
        null=True,
        blank=True,
    )

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('application')
        verbose_name_plural = _('applications')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.legal_name} - {self.get_status_display()} ({self.submitted_at.strftime('%Y-%m-%d')})"

    # FSM Transitions

    @transition(
        field=status,
        source=ApplicationStatus.SUBMITTED,
        target=ApplicationStatus.UNDER_REVIEW,
    )
    def start_review(self, reviewer=None):
        """Move application to under review status."""
        if reviewer:
            self.reviewed_by = reviewer

    @transition(
        field=status,
        source=ApplicationStatus.UNDER_REVIEW,
        target=ApplicationStatus.APPROVED,
    )
    def approve(self, reviewer=None, notes=''):
        """
        Approve the application.

        Creates Profile and RoleAssignment when called.
        """
        from dateutil.relativedelta import relativedelta

        self.reviewed_at = timezone.now()
        if reviewer:
            self.reviewed_by = reviewer
        if notes:
            self.review_notes = notes

        # Update user's preferred language
        self.user.preferred_language = self.preferred_language
        self.user.save(update_fields=['preferred_language'])

        # Create or update Profile
        profile, created = Profile.objects.get_or_create(
            user=self.user,
            defaults={
                'legal_name': self.legal_name,
                'country_of_residence': self.country_of_residence,
            }
        )
        if not created:
            # Update existing profile
            profile.legal_name = self.legal_name
            profile.country_of_residence = self.country_of_residence
            profile.save()

        # Create RoleAssignment
        today = timezone.now().date()
        RoleAssignment.objects.create(
            profile=profile,
            role=self.role_requested,
            start_date=today,
            end_date=today + relativedelta(years=2),
            assigned_by=reviewer,
            notes=f"Approved via application #{self.pk}",
        )

    @transition(
        field=status,
        source=ApplicationStatus.UNDER_REVIEW,
        target=ApplicationStatus.REJECTED,
    )
    def reject(self, reviewer=None, notes=''):
        """Reject the application."""
        self.reviewed_at = timezone.now()
        if reviewer:
            self.reviewed_by = reviewer
        if notes:
            self.review_notes = notes

    @property
    def can_be_approved(self) -> bool:
        """Check if application can be approved."""
        return self.status == ApplicationStatus.UNDER_REVIEW

    @property
    def can_be_rejected(self) -> bool:
        """Check if application can be rejected."""
        return self.status == ApplicationStatus.UNDER_REVIEW

    @property
    def is_pending(self) -> bool:
        """Check if application is still pending decision."""
        return self.status in [ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW]
