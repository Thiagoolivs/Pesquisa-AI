from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('pesquisa', views.pesquisa, name='pesquisa'),
    path('ia', views.ia_page, name='ia'),

    path('api/csv/upload', views.api_csv_upload, name='api_csv_upload'),
    path('upload-csv/', views.api_csv_upload, name='api_csv_upload_compat'),


    path('api/analysis/save', views.api_analysis_save, name='api_analysis_save'),
    path('api/analysis/discard', views.api_analysis_discard, name='api_analysis_discard'),
    path('api/analysis/list', views.api_analyses_list, name='api_analyses_list'),
    path('api/analysis/<int:analysis_id>/open', views.api_analysis_open, name='api_analysis_open'),
    path('api/analysis/<int:analysis_id>/delete', views.api_analysis_delete, name='api_analysis_delete'),

    path('api/form/create', views.api_form_create, name='api_form_create'),
    path('api/form/<int:form_id>/respond', views.api_form_respond, name='api_form_respond'),
    path('api/form/<int:form_id>/open', views.api_form_open_as_analysis, name='api_form_open'),
    path('api/form/<int:form_id>/delete', views.api_form_delete, name='api_form_delete'),

    path('api/data/analyze', views.api_data_analyze, name='api_data_analyze'),
    path('api/ai/chat', views.api_ai_chat, name='api_ai_chat'),
    path('api/ai/column-insight', views.api_column_insight, name='api_column_insight'),
    path('api/ai/global-insight', views.api_global_insight, name='api_global_insight'),
]
