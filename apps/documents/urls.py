"""URL configuration for documents app."""
from django.urls import path

from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.PendingDocumentsView.as_view(), name='pending'),
    path('history/', views.ConsentHistoryView.as_view(), name='history'),
    path('<slug:slug>/', views.DocumentDetailView.as_view(), name='detail'),
    path('<slug:slug>/sign/', views.ConsentView.as_view(), name='consent'),
]
