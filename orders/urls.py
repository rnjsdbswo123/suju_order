from django.urls import path
from .views import (
    OrderFormView, 
    OrderEditView,
    OrderCreateView, 
    OrderUpdateView,
    my_order_list_api, 
    MyOrderListView,
    SalesOrderCreateView,
    cancel_order
)

urlpatterns = [
    # 1. 발주 작성 및 수정 화면
    path('new/', OrderFormView.as_view(), name='order-form'),
    path('edit/<int:order_id>/', OrderEditView.as_view(), name='order-edit'),
    
    # 2. 발주 저장/수정 기능 (API)
    path('api/create/', OrderCreateView.as_view(), name='order-create-api'),
    path('api/update/<int:order_id>/', OrderUpdateView.as_view(), name='order-update-api'),

    # 3. 내 발주 목록 가져오기
    path('my-list/', MyOrderListView.as_view(), name='my-order-list'),

    # 4. [보조] 내 발주 데이터만 주는 API (팝업용 - 주소 분리함)
    path('api/list/', my_order_list_api, name='my-order-list-api'),

    # 5. 영업부 발주 작성 화면
    path('sales/create/', SalesOrderCreateView.as_view(), name='sales-order-create'),

    # 6. 발주 취소 기능
    path('cancel/<int:order_id>/', cancel_order, name='cancel_order'),
]