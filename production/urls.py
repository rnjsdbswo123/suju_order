from django.urls import path
from .views import ProductionStatusView, OrderLineCompleteView, OrderLineBulkCompleteView, OrderLineUpdateView,OrderLineLogListView

urlpatterns = [
    path('status/', ProductionStatusView.as_view(), name='production-status-ui'),
    path('line/<int:pk>/complete/', OrderLineCompleteView.as_view(), name='line-complete'),
    path('lines/bulk_complete/', OrderLineBulkCompleteView.as_view(), name='lines-bulk-complete'),
    path('line/<int:pk>/update/', OrderLineUpdateView.as_view(), name='line-update'),
    
    # ★ 로그 조회용 URL (대괄호 안에 있어야 함)
    path('line/<int:pk>/logs/', OrderLineLogListView.as_view(), name='line-logs'),
]