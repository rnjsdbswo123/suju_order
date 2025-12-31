from django.contrib import admin
from .models import Customer, Product, CustomerProductMap

# CustomerProductMap을 Customer 상세 페이지에서 바로 편집할 수 있도록 Inline 등록
class CustomerProductMapInline(admin.TabularInline):
    model = CustomerProductMap
    extra = 1 # 한 번에 추가할 빈 줄 개수

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_id', 'is_active')
    search_fields = ('name',)
    inlines = [CustomerProductMapInline] # 인라인 편집기 추가

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'order', 'unit_price', 'production_facility', 'is_active')
    list_editable = ('order',)
    search_fields = ('sku', 'name')
    list_filter = ('production_facility', 'is_active')