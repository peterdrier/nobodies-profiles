"""URL configuration for members app."""
from django.urls import path

from . import views

app_name = 'members'

urlpatterns = [
    path('profile/', views.ProfileView.as_view(), name='profile'),
]
