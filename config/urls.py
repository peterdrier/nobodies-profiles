"""
URL configuration for Nobodies Profiles.
"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView

from apps.members.views import DashboardView

# Import admin customizations
import config.admin  # noqa: F401

urlpatterns = [
    # Health check (no i18n prefix)
    path('health/', TemplateView.as_view(template_name='health.html'), name='health'),

    # Auth URLs without language prefix (for stable OAuth callback)
    path('accounts/', include('allauth.urls')),
]

# i18n URL patterns
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),

    # Dashboard (main landing page after login)
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # App URLs
    path('applications/', include('apps.applications.urls')),
    path('members/', include('apps.members.urls')),
    path('documents/', include('apps.documents.urls')),
    path('gdpr/', include('apps.gdpr.urls')),

    # Home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    prefix_default_language=True,
)

# Debug toolbar (only in DEBUG mode)
if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
