from django.urls import path
from .views import (
    ProductionStatusView, 
    pending_production_summary,
    OrderLineCompleteView, 
    OrderLineBulkCompleteView, 
    OrderLineBulkUpdateView,
    OrderLineUpdateView, 
    OrderLineLogListView,
    MaterialOrderRequestView,
    MaterialOrderListView,
    MaterialOrderStatusUpdateView,
    MaterialOrderQuantityUpdateView,
    material_order_delete,
)

app_name = 'production'

urlpatterns = [
    path('status/', ProductionStatusView.as_view(), name='production-status-ui'),
    path('pending-summary/', pending_production_summary, name='pending-summary'),
    path('line/<int:pk>/complete/', OrderLineCompleteView.as_view(), name='line-complete'),
    path('lines/bulk_complete/', OrderLineBulkCompleteView.as_view(), name='lines-bulk-complete'),
    path('lines/bulk-update/', OrderLineBulkUpdateView.as_view(), name='lines-bulk-update'),
    path('line/<int:pk>/update/', OrderLineUpdateView.as_view(), name='line-update'),
    path('line/<int:pk>/logs/', OrderLineLogListView.as_view(), name='line-logs'),

    # 부자재 발주
    path('material/request/', MaterialOrderRequestView.as_view(), name='material-order-request'),
    path('material/list/', MaterialOrderListView.as_view(), name='material-order-list'),
    path('material/<int:pk>/', MaterialOrderStatusUpdateView.as_view(), name='material-order-detail'),
    path('material/<int:pk>/edit/', MaterialOrderQuantityUpdateView.as_view(), name='material-order-edit'),
    path('material/<int:pk>/delete/', material_order_delete, name='material-order-delete'),
]
