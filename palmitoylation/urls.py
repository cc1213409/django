from django.urls import path

from . import views

urlpatterns = [
    path("", views.browse, name="browse"),
    path("site/<int:pk>/", views.detail, name="detail"),
    path("analysis/", views.analysis, name="analysis"),
    path("export/", views.export_csv, name="export_csv"),
]
