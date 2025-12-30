# audit/urls.py
from django.urls import path, include
from .views import AuditLogListAPIView

urlpatterns = [
    # GET: 전체 로그 조회 (관리자만)
    path('', AuditLogListAPIView.as_view(), name='auditlog-list'),
]

# SujuOrderSystem/urls.py 수정
urlpatterns = [
    # ...
    path('api/masters/', include('masters.urls')),
    path('api/audit/', include('audit.urls')), # 추가
]