from django.shortcuts import render
from django.views.generic import TemplateView, View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone  # 시간 확인용
from datetime import timedelta     # 날짜 계산용
import json
from django.db.models import Q
from .models import OrderHeader, OrderLine, FACILITY_LIST
from masters.models import Customer, SalesFavoriteProduct
from users.permissions import SalesRequiredMixin


# 1. 발주 작성 화면
class OrderFormView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/order_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.filter(is_active=True)
        context['facility_list'] = FACILITY_LIST
        return context

# 2. 발주 저장 API
class OrderCreateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            customer_id = data.get('customer_id')
            delivery_date = data.get('delivery_date')
            facility = data.get('production_facility')
            memo = data.get('memo')
            items = data.get('items', [])

            # 15시 마감 체크 로직
            now = timezone.localtime() 
            if now.hour >= 15:
                tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')
                if delivery_date <= tomorrow:
                    return JsonResponse({'error': '❌ 15시가 지나 내일 납기는 불가능합니다. 모레부터 선택해주세요.'}, status=400)

            with transaction.atomic():
                order = OrderHeader.objects.create(
                    customer_id=customer_id,
                    requested_delivery_date=delivery_date, 
                    production_facility=facility,
                    memo=memo,
                    created_by=request.user
                )

                for item in items:
                    OrderLine.objects.create(
                        header=order,
                        product_id=item['product_id'],
                        requested_quantity=int(item['quantity']),
                        production_facility=facility
                    )

            return JsonResponse({'message': '발주 성공!'}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

# 3. [API] 내 발주 목록 데이터 (팝업용 - 혹시 몰라 남겨둠)
def my_order_list_api(request):
    orders = OrderHeader.objects.filter(
        created_by=request.user
    ).order_by('-created_at')[:20]
    
    data = []
    for order in orders:
        lines = order.lines.all()
        summary = f"{lines[0].product.name} 외 {lines.count()-1}건" if lines.exists() else "품목 없음"
        
        data.append({
            'date': order.created_at.strftime('%Y-%m-%d'),
            'customer': order.customer.name,
            'summary': summary,
            'status': order.total_status,
            'facility': order.production_facility
        })
    
    return JsonResponse({'orders': data})

# 4. [페이지] 내 발주 이력 페이지 (★ 신규 추가됨)
class MyOrderListView(LoginRequiredMixin, ListView):
    template_name = 'orders/my_order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = OrderHeader.objects.filter(
            created_by=self.request.user
        ).select_related('customer').prefetch_related('lines', 'lines__product').order_by('-created_at')

        q = self.request.GET.get('q', '')

        if q:
            queryset = queryset.filter(customer__name__icontains=q)
            
        return queryset

# 5. [페이지] 영업부 발주 화면
class SalesOrderCreateView(LoginRequiredMixin, SalesRequiredMixin, View):
    template_name = 'orders/sales_order_form.html'
    
    def get(self, request, *args, **kwargs):
        # 영업사원의 선호 품목 목록을 가져옵니다.
        favorite_products = SalesFavoriteProduct.objects.filter(
            user=request.user
        ).select_related('product').order_by('product__name')
        
        context = {
            'page_title': '영업부 발주',
            'favorite_products': favorite_products,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            delivery_date = data.get('delivery_date')
            memo = data.get('memo', '')
            items = data.get('items', [])

            if not items:
                return JsonResponse({'error': '발주할 품목이 없습니다.'}, status=400)

            # 15시 마감 체크
            now = timezone.localtime()
            if now.hour >= 15:
                tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')
                if delivery_date <= tomorrow:
                    return JsonResponse({'error': '오후 3시가 지나 내일 납기는 불가능합니다. 모레부터 선택해주세요.'}, status=400)
            
            # '내부 영업팀' 거래처 가져오기
            internal_customer = Customer.objects.get(name='내부 영업팀')

            with transaction.atomic():
                # OrderHeader 생성
                order = OrderHeader.objects.create(
                    customer=internal_customer,
                    requested_delivery_date=delivery_date,
                    memo=memo,
                    created_by=request.user,
                    # 영업부 발주는 특정 생산시설을 가정하지 않거나, 기본값을 사용
                    production_facility='A동' 
                )

                # OrderLine 생성
                for item in items:
                    if int(item.get('quantity', 0)) > 0:
                        OrderLine.objects.create(
                            header=order,
                            product_id=item['product_id'],
                            requested_quantity=int(item['quantity']),
                            production_facility=order.production_facility 
                        )
            
            return JsonResponse({'message': '영업 발주가 성공적으로 등록되었습니다.'}, status=201)

        except Customer.DoesNotExist:
            return JsonResponse({'error': '기본 설정된 "내부 영업팀" 거래처를 찾을 수 없습니다. 관리자에게 문의하세요.'}, status=500)
        except Exception as e:
            return JsonResponse({'error': f'발주 처리 중 오류 발생: {str(e)}'}, status=400)