"""Forms for the members app."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import CommunityTag, ProfileTag


class EditTagsForm(forms.Form):
    """Form for members to manage their self-assignable tags."""

    tags = forms.ModelMultipleChoiceField(
        queryset=CommunityTag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('My Tags'),
    )

    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile

        # Only show self-assignable, active tags
        self.fields['tags'].queryset = CommunityTag.objects.filter(
            is_self_assignable=True,
            is_active=True,
        ).order_by('display_order', 'name')

        # Pre-select tags the profile already has
        if profile:
            current_tag_ids = ProfileTag.objects.filter(
                profile=profile,
                tag__is_self_assignable=True,
            ).values_list('tag_id', flat=True)
            self.initial['tags'] = current_tag_ids

    def save(self):
        """Save tag selections for the profile."""
        if not self.profile:
            return

        selected_tags = set(self.cleaned_data['tags'])
        current_tags = set(
            ProfileTag.objects.filter(
                profile=self.profile,
                tag__is_self_assignable=True,
            ).select_related('tag')
        )

        current_tag_objects = {pt.tag for pt in current_tags}

        # Remove tags that were deselected
        tags_to_remove = current_tag_objects - selected_tags
        if tags_to_remove:
            ProfileTag.objects.filter(
                profile=self.profile,
                tag__in=tags_to_remove,
            ).delete()

        # Add newly selected tags
        tags_to_add = selected_tags - current_tag_objects
        for tag in tags_to_add:
            ProfileTag.objects.create(
                profile=self.profile,
                tag=tag,
                assigned_by=None,  # Self-assigned
            )
