from django.urls import path
from .views import (
    OrderFormView, 
    OrderCreateView, 
    my_order_list_api, 
    MyOrderListView,
    SalesOrderCreateView
)

urlpatterns = [
    # 1. 발주 작성 화면
    path('new/', OrderFormView.as_view(), name='order-form'),
    
    # 2. 발주 저장 기능 (API)
    path('create/', OrderCreateView.as_view(), name='order-create'),
    
    # 3. 내 발주 목록 가져오기 (API)
    path('my-list/', MyOrderListView.as_view(), name='my-order-list'),

    # 4. [보조] 내 발주 데이터만 주는 API (팝업용 - 주소 분리함)
    path('api/list/', my_order_list_api, name='my-order-list-api'),

    # 5. 영업부 발주 작성 화면
    path('sales/create/', SalesOrderCreateView.as_view(), name='sales-order-create'),
]