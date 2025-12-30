from django.urls import path
from .views import ProductionStatusView, OrderLineCompleteView, OrderLineBulkCompleteView

urlpatterns = [
    # 1. 화면: 생산 현황판 (UI)
    # 주소: /api/production/status/
    path('status/', ProductionStatusView.as_view(), name='production-status-ui'),
    
    # 2. API: 개별 생산 완료 처리 (OK 버튼용)
    # 주소: /api/production/line/1/complete/
    path('line/<int:pk>/complete/', OrderLineCompleteView.as_view(), name='line-complete'),
    
    # 3. API: 일괄 생산 완료 처리 (선택항목 일괄처리용)
    # 주소: /api/production/lines/bulk_complete/
    path('lines/bulk_complete/', OrderLineBulkCompleteView.as_view(), name='lines-bulk-complete'),
]