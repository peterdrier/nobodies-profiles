"""Custom admin site configuration."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# Customize the default admin site
admin.site.site_header = _('Nobodies Profiles Administration')
admin.site.site_title = _('Nobodies Admin')
admin.site.index_title = _('Membership Management')
