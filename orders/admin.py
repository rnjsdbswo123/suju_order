from django.contrib import admin
from .models import OrderHeader, OrderLine, OrderLog
from datetime import timedelta

# 1. 발주서 상세 품목을 '표' 형태로 같이 보기 위한 설정 (Inline)
class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0  
    readonly_fields = ('product_sku', 'product_name') 
    
    def product_sku(self, obj):
        return obj.product.sku
    
    def product_name(self, obj):
        return obj.product.name

# 2. 발주서 헤더(메인) 설정
@admin.register(OrderLog)
class OrderLogAdmin(admin.ModelAdmin):
    # 리스트에 보여줄 항목들 (시간, 수정자, 유형, 품목정보, 내용)
    list_display = ('localized_created_at', 'editor', 'change_type', 'get_product_name', 'description')
    
    # 우측 필터창 (유형별, 날짜별, 수정자별 필터링 가능)
    list_filter = ('change_type', 'created_at', 'editor')
    
    # 검색창 (내용, 수정자 이름, 품목명으로 검색 가능)
    search_fields = ('description', 'editor__username', 'line__product__name')
    
    # 최신순 정렬
    ordering = ('-created_at',)

    # 시간을 한국 시간으로 변환하여 보여주는 함수 (수동 변환)
    def localized_created_at(self, obj):
        if not obj.created_at:
            return None
        # UTC 시간에 9시간을 수동으로 더해서 KST로 변환
        kst_time = obj.created_at + timedelta(hours=9)
        return kst_time.strftime('%Y-%m-%d %H:%M:%S')
        
    localized_created_at.short_description = "변경 일시 (KST)"

    # 품목 이름을 보기 좋게 가져오는 함수
    def get_product_name(self, obj):
        return f"{obj.line.product.name} ({obj.line.header.customer.name})"
    get_product_name.short_description = "관련 품목"