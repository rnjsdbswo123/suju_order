from django.urls import path
from .views import (
    DataUploadView, 
    CustomerProductMappingView, 
    delete_customer_product, 
    get_products_by_customer,
    search_customers,
    search_products,
    update_customer_products, 
    SalesFavoriteProductManageView,
    ProductFacilityManageView,
    CustomerCreateView,
    ProductCreateView,
    RawMaterialCreateView,
    RawMaterialListView,
    RawMaterialUpdateView,
)


urlpatterns = [
    # 1. 엑셀 업로드 화면
    path('upload/', DataUploadView.as_view(), name='data-upload'),
    
    # 2. 매핑 관리 화면
    path('mapping/', CustomerProductMappingView.as_view(), name='customer-product-manage'),
    path('mapping/<int:pk>/delete/', delete_customer_product, name='customer-product-delete'),
    
    # 3. [API]
    path('api/customers/<int:customer_id>/products/', get_products_by_customer, name='customer-products-api'),
    path('api/search/customers/', search_customers, name='customer-search-api'),
    path('api/search/products/', search_products, name='product-search-api'),
    path('api/update-customer-products/', update_customer_products, name='update-customer-products-api'),

    # 4. [화면] 개별 데이터 등록
    path('customer/add/', CustomerCreateView.as_view(), name='customer-create'),
    path('product/add/', ProductCreateView.as_view(), name='product-create'),
    path('rawmaterial/add/', RawMaterialCreateView.as_view(), name='rawmaterial-create'),
    path('rawmaterials/', RawMaterialListView.as_view(), name='rawmaterial-list'),
    path('rawmaterial/<int:pk>/edit/', RawMaterialUpdateView.as_view(), name='rawmaterial-edit'),

    # 5. [화면] 영업사원 선호품목 관리
    path('favorites/', SalesFavoriteProductManageView.as_view(), name='sales-favorite-manage'),

    # 6. [화면] 품목별 생산동 관리
    path('products/facilities/', ProductFacilityManageView.as_view(), name='product-facility-manage'),
]