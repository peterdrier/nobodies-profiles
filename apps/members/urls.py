"""URL configuration for members app."""
from django.urls import path

from . import views

app_name = 'members'

urlpatterns = [
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/tags/', views.EditTagsView.as_view(), name='edit_tags'),
]
