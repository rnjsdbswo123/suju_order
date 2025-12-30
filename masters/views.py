from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q  # ★ [중요] 검색 기능의 핵심!
import openpyxl

# 모델 가져오기
from .models import Customer, Product, CustomerProductMap

# ==========================================
# 1. [화면] 엑셀 데이터 일괄 업로드
# ==========================================
class DataUploadView(LoginRequiredMixin, TemplateView):
    template_name = 'masters/data_upload.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request):
        try:
            if 'customer_file' in request.FILES:
                self.upload_customers(request.FILES['customer_file'])
                messages.success(request, "거래처 업로드 완료! 🎉")
            
            elif 'product_file' in request.FILES:
                self.upload_products(request.FILES['product_file'])
                messages.success(request, "품목 업로드 완료! 🎉")
                
            elif 'mapping_file' in request.FILES:
                self.upload_mappings(request.FILES['mapping_file'])
                messages.success(request, "매핑 업로드 완료! 🎉")
        except Exception as e:
            messages.error(request, f"업로드 중 오류 발생: {str(e)}")
        return redirect('data-upload')

    def upload_customers(self, file):
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]: continue
            name = row[0]
            biz_id = row[1] if len(row) > 1 else None
            Customer.objects.get_or_create(name=name, defaults={'business_id': biz_id})

    def upload_products(self, file):
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or len(row) < 2 or not row[1]: continue
            name, sku = row[0], row[1]
            price = row[2] if len(row) > 2 else 0
            facility = row[3] if len(row) > 3 else 'A동'
            
            # 가격이 비어있으면 0원으로 처리
            if price is None: price = 0
            
            Product.objects.update_or_create(
                sku=sku,
                defaults={'name': name, 'unit_price': price, 'production_facility': facility}
            )

    def upload_mappings(self, file):
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or len(row) < 2: continue
            c_name, p_sku = row[0], row[1]
            try:
                customer = Customer.objects.get(name=c_name)
                product = Product.objects.get(sku=p_sku)
                CustomerProductMap.objects.get_or_create(customer=customer, product=product)
            except:
                pass # 매핑 실패 시 무시

# ==========================================
# 2. [화면] 거래처-품목 매핑 직접 관리
# ==========================================
class CustomerProductManageView(LoginRequiredMixin, TemplateView):
    template_name = 'masters/customer_product_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 화면 로딩 시에는 전체 목록 대신 매핑된 리스트만 보여줌
        context['mappings'] = CustomerProductMap.objects.select_related('customer', 'product').order_by('-id')
        return context

    def post(self, request):
        customer_id = request.POST.get('customer')
        product_id = request.POST.get('product')
        if customer_id and product_id:
            if not CustomerProductMap.objects.filter(customer_id=customer_id, product_id=product_id).exists():
                CustomerProductMap.objects.create(customer_id=customer_id, product_id=product_id)
        return redirect('customer-product-manage')

def delete_customer_product(request, pk):
    mapping = get_object_or_404(CustomerProductMap, pk=pk)
    mapping.delete()
    return redirect('customer-product-manage')

# ==========================================
# 3. [API] 데이터 검색 및 조회 (AJAX용)
# ==========================================

# (1) 거래처 선택 시 -> 매핑된 품목 가져오기
@api_view(['GET'])
def get_products_by_customer(request, customer_id):
    mappings = CustomerProductMap.objects.filter(customer_id=customer_id).select_related('product')
    data = [{"id": m.product.id, "name": m.product.name, "sku": m.product.sku, "price": m.product.unit_price} for m in mappings]
    return Response(data)

# (2) 거래처 검색 API
@api_view(['GET'])
def search_customers(request):
    query = request.GET.get('q', '')
    
    # 1. 검색어가 있으면 -> 이름이나 사업자번호로 찾기
    if query:
        customers = Customer.objects.filter(
            Q(name__icontains=query) | Q(business_id__icontains=query)
        ).filter(is_active=True)
    # 2. 검색어가 없으면 -> (수정됨) 그냥 활성 거래처 20개 보여주기
    else:
        customers = Customer.objects.filter(is_active=True)

    # 최대 20개까지만 잘라서 보냄
    customers = customers[:20]
    
    data = [{"id": c.id, "text": c.name} for c in customers]
    return Response({"results": data})
# (3) 품목 검색 API ★ [여기가 문제였을 수 있음]
@api_view(['GET'])
def search_products(request):
    query = request.GET.get('q', '')
    print(f"품목 검색 요청 들어옴: 검색어='{query}'") # 터미널에서 확인용
    
    # 1. 검색어가 있으면 -> 이름이나 SKU로 찾기
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        )
    # 2. 검색어가 없으면 -> 그냥 최근 등록된 20개 무조건 보여주기
    else:
        products = Product.objects.all().order_by('-id')

    # (혹시 몰라 is_active 필터도 뺐습니다. 무조건 나오게!)
    products = products[:20] # 최대 20개까지만
    
    data = [
        {"id": p.id, "text": f"{p.name} ({p.sku})"} 
        for p in products
    ]
    return Response({"results": data})