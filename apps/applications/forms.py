"""Forms for the applications app."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.members.models import Role

from .models import Application


class ApplicationForm(forms.ModelForm):
    """
    Public application form for membership.

    Requires GDPR consent before submission.
    """

    COUNTRY_CHOICES = [
        ('', _('Select your country')),
        ('ES', _('Spain')),
        ('PT', _('Portugal')),
        ('FR', _('France')),
        ('DE', _('Germany')),
        ('GB', _('United Kingdom')),
        ('IT', _('Italy')),
        ('NL', _('Netherlands')),
        ('BE', _('Belgium')),
        ('AT', _('Austria')),
        ('CH', _('Switzerland')),
        ('PL', _('Poland')),
        ('SE', _('Sweden')),
        ('NO', _('Norway')),
        ('DK', _('Denmark')),
        ('FI', _('Finland')),
        ('IE', _('Ireland')),
        ('US', _('United States')),
        ('CA', _('Canada')),
        ('AU', _('Australia')),
        ('OTHER', _('Other')),
    ]

    LANGUAGE_CHOICES = [
        ('es', _('Spanish')),
        ('en', _('English')),
        ('fr', _('French')),
        ('de', _('German')),
        ('pt', _('Portuguese')),
    ]

    country_of_residence = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        label=_('Country of Residence'),
        help_text=_('Where do you currently live?'),
    )

    preferred_language = forms.ChoiceField(
        choices=LANGUAGE_CHOICES,
        label=_('Preferred Language'),
        help_text=_('Language for communications'),
        initial='en',
    )

    role_requested = forms.ChoiceField(
        choices=[
            (Role.COLABORADOR, _('Colaborador - Volunteer participant with voice but no vote at Assembly')),
            (Role.ASOCIADO, _('Asociado - Full member with voting rights (requires prior participation)')),
        ],
        label=_('Membership Type'),
        widget=forms.RadioSelect,
        initial=Role.COLABORADOR,
    )

    gdpr_consent = forms.BooleanField(
        required=True,
        label=_('I consent to data processing'),
        help_text=_(
            'I consent to Asociación Nobodies Collective processing my personal data '
            'for the purpose of evaluating my membership application, as described in '
            'the Privacy Policy. I understand I can withdraw this consent at any time.'
        ),
    )

    statutes_acknowledgment = forms.BooleanField(
        required=True,
        label=_('I acknowledge the membership terms'),
        help_text=_(
            'I understand that membership is for 2 years and subject to Board approval '
            'per Article 20 of the Statutes. I agree to comply with the Statutes and '
            'decisions of the General Assembly.'
        ),
    )

    class Meta:
        model = Application
        fields = [
            'legal_name',
            'preferred_name',
            'country_of_residence',
            'preferred_language',
            'role_requested',
            'motivation',
            'skills',
            'how_heard',
            'attended_before',
            'attended_years',
        ]
        widgets = {
            'legal_name': forms.TextInput(attrs={
                'placeholder': _('Your full legal name'),
                'class': 'form-control',
            }),
            'preferred_name': forms.TextInput(attrs={
                'placeholder': _('Name you prefer to be called (optional)'),
                'class': 'form-control',
            }),
            'motivation': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': _('Why do you want to join Nobodies Collective?'),
                'class': 'form-control',
            }),
            'skills': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('Skills or experience you can contribute (optional)'),
                'class': 'form-control',
            }),
            'how_heard': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': _('How did you hear about us? (optional)'),
                'class': 'form-control',
            }),
            'attended_years': forms.TextInput(attrs={
                'placeholder': _('e.g., 2019, 2022, 2023'),
                'class': 'form-control',
            }),
        }
        labels = {
            'legal_name': _('Legal Name'),
            'preferred_name': _('Preferred Name'),
            'motivation': _('Motivation'),
            'skills': _('Skills & Experience'),
            'how_heard': _('How did you hear about us?'),
            'attended_before': _('Have you attended a Nobodies event before?'),
            'attended_years': _('Which years?'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Pre-fill from user if available
        if self.user:
            if self.user.display_name:
                self.fields['legal_name'].initial = self.user.display_name
            self.fields['preferred_language'].initial = self.user.preferred_language

    def clean(self):
        cleaned_data = super().clean()

        # If attended before, years should be provided
        attended_before = cleaned_data.get('attended_before')
        attended_years = cleaned_data.get('attended_years')

        if attended_before and not attended_years:
            self.add_error(
                'attended_years',
                _('Please specify which years you attended.')
            )

        # If requesting Asociado, should have attended before
        role_requested = cleaned_data.get('role_requested')
        if role_requested == Role.ASOCIADO and not attended_before:
            self.add_error(
                'role_requested',
                _('Asociado membership typically requires prior event participation. '
                  'Consider applying as Colaborador first.')
            )

        return cleaned_data
