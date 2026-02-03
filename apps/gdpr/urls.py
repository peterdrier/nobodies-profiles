"""URL configuration for GDPR app."""
from django.urls import path

from . import views

app_name = 'gdpr'

urlpatterns = [
    # Member self-service
    path('my-data/', views.MyDataView.as_view(), name='my_data'),
    path('my-data/download/', views.RequestExportView.as_view(), name='request_export'),
    path('my-data/download/<uuid:token>/', views.DownloadExportView.as_view(), name='download_export'),
    path('my-data/delete/', views.RequestDeletionView.as_view(), name='request_deletion'),
    path('my-data/delete/confirm/<uuid:token>/', views.ConfirmDeletionView.as_view(), name='confirm_deletion'),

    # Board dashboard
    path('board/', views.GDPRDashboardView.as_view(), name='board_dashboard'),
    path('board/deletion-requests/', views.DeletionRequestListView.as_view(), name='deletion_request_list'),
    path('board/deletion-requests/<int:pk>/', views.DeletionRequestDetailView.as_view(), name='deletion_request_detail'),
    path('board/deletion-requests/<int:pk>/review/', views.ReviewDeletionView.as_view(), name='review_deletion'),
    path('board/audit-log/', views.AuditLogView.as_view(), name='audit_log'),
]
