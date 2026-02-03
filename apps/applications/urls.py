"""URL configuration for applications app."""
from django.urls import path

from . import views

app_name = 'applications'

urlpatterns = [
    path('apply/', views.ApplicationCreateView.as_view(), name='apply'),
    path('success/', views.ApplicationSuccessView.as_view(), name='success'),
    path('status/<int:pk>/', views.ApplicationStatusView.as_view(), name='status'),
]
