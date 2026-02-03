"""Forms for the GDPR app."""
from django import forms
from django.utils.translation import gettext_lazy as _


class RequestExportForm(forms.Form):
    """Form for requesting a data export."""

    confirm = forms.BooleanField(
        required=True,
        label=_('I understand and confirm'),
        help_text=_(
            'I understand that this will generate a complete export of my personal data. '
            'The export will be available for download for 30 days.'
        ),
    )


class RequestDeletionForm(forms.Form):
    """Form for requesting account deletion."""

    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        label=_('Reason (optional)'),
        help_text=_('Please let us know why you want to delete your account.'),
    )
    confirm = forms.BooleanField(
        required=True,
        label=_('I understand this action is irreversible'),
        help_text=_(
            'I understand that deleting my account will permanently remove all my personal data. '
            'This action cannot be undone.'
        ),
    )
    final_confirm = forms.BooleanField(
        required=True,
        label=_('I want to proceed with account deletion'),
        help_text=_(
            'I confirm that I want to delete my account and all associated data.'
        ),
    )


class ConfirmDeletionForm(forms.Form):
    """Form for confirming deletion via email token."""

    confirm = forms.BooleanField(
        required=True,
        label=_('Yes, delete my account'),
        help_text=_(
            'This is your final confirmation. '
            'Your request will be reviewed by the board before execution.'
        ),
    )


class ReviewDeletionForm(forms.Form):
    """Form for board members to review deletion requests."""

    DECISION_CHOICES = [
        ('approve', _('Approve')),
        ('deny', _('Deny')),
    ]

    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect,
        label=_('Decision'),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        label=_('Review notes'),
        help_text=_('Internal notes about this review decision.'),
    )
    denial_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        label=_('Denial reason'),
        help_text=_('If denying, please provide a reason that will be shared with the user.'),
    )

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        denial_reason = cleaned_data.get('denial_reason')

        if decision == 'deny' and not denial_reason:
            raise forms.ValidationError(
                _('A denial reason is required when denying a request.')
            )

        return cleaned_data
