from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
import openpyxl
from SujuOrderSystem.utils import FACILITY_LIST
from django.core.paginator import Paginator

# 모델 가져오기
from .models import Customer, Product, CustomerProductMap, SalesFavoriteProduct

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
                pass

# ==========================================
# 2. [화면] 거래처-품목 매핑 직접 관리
# ==========================================
class CustomerProductManageView(LoginRequiredMixin, TemplateView):
    template_name = 'masters/customer_product_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
@api_view(['GET'])
def get_products_by_customer(request, customer_id):
    mappings = CustomerProductMap.objects.filter(customer_id=customer_id).select_related('product').order_by('product__order', 'product__name')
    data = [{"id": m.product.id, "name": m.product.name, "sku": m.product.sku, "price": m.product.unit_price} for m in mappings]
    return Response(data)

@api_view(['GET'])
def search_customers(request):
    query = request.GET.get('q', '')
    if query:
        customers = Customer.objects.filter(
            Q(name__icontains=query) | Q(business_id__icontains=query)
        ).filter(is_active=True)
    else:
        customers = Customer.objects.filter(is_active=True)
    customers = customers[:20]
    data = [{"id": c.id, "text": c.name} for c in customers]
    return Response({"results": data})

@api_view(['GET'])
def search_products(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        )
    else:
        products = Product.objects.all().order_by('-id')
    products = products[:20]
    data = [
        {"id": p.id, "text": f"{p.name} ({p.sku})"} 
        for p in products
    ]
    return Response({"results": data})

# ==========================================
# 4. [화면] 영업사원 선호품목 관리
# ==========================================
class SalesFavoriteProductManageView(LoginRequiredMixin, View):
    template_name = 'masters/sales_favorite_product_manage.html'

    def get(self, request, *args, **kwargs):
        all_products = Product.objects.filter(is_active=True).order_by('name')
        favorite_product_ids = SalesFavoriteProduct.objects.filter(user=request.user).values_list('product_id', flat=True)
        context = {
            'products': all_products,
            'favorite_product_ids': set(favorite_product_ids),
            'page_title': '내 선호품목 관리'
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        if not product_id or not action:
            messages.error(request, '잘못된 요청입니다.')
            return redirect('sales-favorite-manage')
        product = get_object_or_404(Product, id=product_id)
        if action == 'add':
            if not SalesFavoriteProduct.objects.filter(user=request.user, product=product).exists():
                SalesFavoriteProduct.objects.create(user=request.user, product=product)
                messages.success(request, f'"{product.name}"을(를) 선호 품목에 추가했습니다.')
        elif action == 'remove':
            favorite = SalesFavoriteProduct.objects.filter(user=request.user, product=product)
            if favorite.exists():
                favorite.delete()
                messages.success(request, f'"{product.name}"을(를) 선호 품목에서 제거했습니다.')
        return redirect('sales-favorite-manage')

# ==========================================
# 5. [화면] 품목별 생산동 관리
# ==========================================
class ProductFacilityManageView(LoginRequiredMixin, View):
    template_name = 'product_facility_manage.html'

    def get(self, request, *args, **kwargs):
        product_list = Product.objects.all().order_by('name')
        
        # 검색
        q = request.GET.get('q', '')
        if q:
            product_list = product_list.filter(Q(name__icontains=q) | Q(sku__icontains=q))

        # 생산동 필터
        facility = request.GET.get('facility', 'ALL')
        if facility == '미지정':
            product_list = product_list.filter(Q(production_facility__isnull=True) | Q(production_facility=''))
        elif facility != 'ALL':
            product_list = product_list.filter(production_facility=facility)

        # 페이지네이션
        paginator = Paginator(product_list, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_title': '품목별 생산동 관리',
            'page_obj': page_obj,
            'facility_list': FACILITY_LIST,
            'search_query': q,
            'selected_facility': facility,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # 엑셀 파일 업로드 처리
        if 'facility_file' in request.FILES:
            try:
                file = request.FILES['facility_file']
                wb = openpyxl.load_workbook(file)
                ws = wb.active
                updated_count = 0
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row or len(row) < 2 or not row[0]: continue
                    sku, facility = row[0], row[1]
                    try:
                        product = Product.objects.get(sku=sku)
                        if product.production_facility != facility:
                            product.production_facility = facility
                            product.save(update_fields=['production_facility'])
                            updated_count += 1
                    except Product.DoesNotExist:
                        continue
                messages.success(request, f"{updated_count}개 품목의 생산동 정보가 엑셀로 업데이트되었습니다.")
            except Exception as e:
                messages.error(request, f"엑셀 처리 중 오류 발생: {e}")

        # 개별 업데이트 처리
        elif 'update_individual' in request.POST:
            product_ids = request.POST.getlist('product_id')
            updated_count = 0
            for pid in product_ids:
                try:
                    product = Product.objects.get(id=pid)
                    new_facility = request.POST.get(f'production_facility_{pid}')
                    if product.production_facility != new_facility:
                        product.production_facility = new_facility
                        product.save(update_fields=['production_facility'])
                        updated_count += 1
                except Product.DoesNotExist:
                    continue
            messages.success(request, f"{updated_count}개 품목의 생산동 정보가 업데이트되었습니다.")
            
        return redirect('product-facility-manage')