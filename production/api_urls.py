# production/api_urls.py
from django.urls import path
from .views import production_summary_api, production_detail_api

app_name = 'production_api'

urlpatterns = [
    path('summary/', production_summary_api, name='summary'),
    path('detail/', production_detail_api, name='detail'),
]