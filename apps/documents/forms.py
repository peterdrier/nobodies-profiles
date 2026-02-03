"""Forms for the documents app."""
from django import forms
from django.utils.translation import gettext_lazy as _


class ConsentForm(forms.Form):
    """
    Form for consenting to a legal document.

    The consent checkbox must be explicitly checked (not pre-checked).
    """

    consent = forms.BooleanField(
        required=True,
        label=_('I agree'),
        widget=forms.CheckboxInput(attrs={'class': 'consent-checkbox'}),
    )

    def __init__(self, *args, document=None, version=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document
        self.version = version

        # Update the consent text dynamically
        if document and version:
            self.fields['consent'].label = _(
                'I have read and agree to "{title}" version {version} dated {date}. '
                'I acknowledge that the Spanish version is the legally binding document. '
                'Translations are provided for reference only.'
            ).format(
                title=document.title,
                version=version.version_number,
                date=version.effective_date.strftime('%B %d, %Y'),
            )

    def get_consent_text(self) -> str:
        """Get the full consent text that will be recorded."""
        if self.document and self.version:
            return (
                f'I have read and agree to "{self.document.title}" '
                f'version {self.version.version_number} dated '
                f'{self.version.effective_date.strftime("%Y-%m-%d")}. '
                f'I acknowledge that the Spanish version is the legally binding document. '
                f'Translations are provided for reference only.'
            )
        return "I have read and agree to this document."
