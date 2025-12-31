from django.urls import path
from .views import (
    DataUploadView, 
    CustomerProductManageView, 
    delete_customer_product, 
    get_products_by_customer,
    search_customers,
    search_products,
    SalesFavoriteProductManageView,
    ProductFacilityManageView,
)

urlpatterns = [
    # 1. 엑셀 업로드 화면
    path('upload/', DataUploadView.as_view(), name='data-upload'),
    
    # 2. 매핑 관리 화면
    path('mapping/', CustomerProductManageView.as_view(), name='customer-product-manage'),
    path('mapping/<int:pk>/delete/', delete_customer_product, name='customer-product-delete'),
    
    # 3. [API] 발주창 연동용
    path('customers/<int:customer_id>/products/', get_products_by_customer, name='customer-products-api'),
    
    # 4. [API] 검색 기능 (이 두 줄이 핵심입니다!)
    path('search/customers/', search_customers, name='customer-search-api'),
    path('search/products/', search_products, name='product-search-api'),

    # 5. [화면] 영업사원 선호품목 관리
    path('favorites/', SalesFavoriteProductManageView.as_view(), name='sales-favorite-manage'),

    # 6. [화면] 품목별 생산동 관리
    path('products/facilities/', ProductFacilityManageView.as_view(), name='product-facility-manage'),
]