from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import json
from collections import defaultdict
from django.db.models import Q
from .models import OrderHeader, OrderLine, FACILITY_LIST, OrderLog
from masters.models import Customer, Product, SalesFavoriteProduct
from users.permissions import SalesRequiredMixin

# 1. 발주 작성 화면
class OrderFormView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/order_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.filter(is_active=True)
        context['facility_list'] = FACILITY_LIST
        context['is_staff'] = self.request.user.is_staff
        return context

# 1.1. 발주 수정 화면
class OrderEditView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/order_edit_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = self.kwargs.get('order_id')
        order = get_object_or_404(
            OrderHeader.objects.prefetch_related('lines', 'lines__product'), 
            id=order_id, 
            created_by=self.request.user
        )
        context['order'] = order
        return context

# 2. 발주 저장 API
class OrderCreateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            customer_id = data.get('customer_id')
            delivery_date = data.get('delivery_date')
            memo = data.get('memo')
            items = data.get('items', [])

            # 15시 마감 체크 로직 (관리자는 제외)
            if not request.user.is_staff:
                now = timezone.localtime() 
                if now.hour >= 15:
                    tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')
                    if delivery_date <= tomorrow:
                        return JsonResponse({'error': '❌ 15시가 지나 내일 납기는 불가능합니다. 모레부터 선택해주세요.'}, status=400)

            # 품목 정보를 가져와 생산동별로 그룹화
            items_by_facility = defaultdict(list)
            product_ids = [item['product_id'] for item in items]
            products = Product.objects.in_bulk(product_ids)

            for item in items:
                product = products.get(int(item['product_id']))
                if product and product.production_facility:
                    items_by_facility[product.production_facility].append(item)
                else:
                    # 생산동이 지정되지 않은 품목에 대한 처리 (기본값 또는 오류)
                    items_by_facility['미지정'].append(item)

            with transaction.atomic():
                for facility, facility_items in items_by_facility.items():
                    order = OrderHeader.objects.create(
                        customer_id=customer_id,
                        requested_delivery_date=delivery_date, 
                        production_facility=facility,
                        memo=memo,
                        created_by=request.user
                    )

                    for item in facility_items:
                        OrderLine.objects.create(
                            header=order,
                            product_id=item['product_id'],
                            requested_quantity=int(item['quantity']),
                            production_facility=facility
                        )

            return JsonResponse({'message': f'발주 성공! {len(items_by_facility)}개의 주문으로 분리되었습니다.'}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

# 2.1. 발주 수정 API
class OrderUpdateView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, order_id):
        try:
            order = get_object_or_404(OrderHeader.objects.prefetch_related('lines', 'lines__product'), id=order_id, created_by=request.user)
            if order.total_status != '대기':
                return JsonResponse({'error': '대기 상태인 주문만 수정할 수 있습니다.'}, status=400)

            data = json.loads(request.body)
            new_items_map = {int(item['line_id']): int(item['quantity']) for item in data.get('items', [])}
            
            # 헤더 정보 업데이트
            order.requested_delivery_date = data.get('delivery_date', order.requested_delivery_date)
            order.memo = data.get('memo', order.memo)
            order.save()
            
            existing_lines = order.lines.all()
            logs_to_create = []

            for line in existing_lines:
                new_quantity = new_items_map.get(line.id)
                if new_quantity is not None and new_quantity != line.requested_quantity and new_quantity >= 0:
                    old_quantity = line.requested_quantity
                    logs_to_create.append(OrderLog(
                        line=line,
                        editor=request.user,
                        change_type='수량 변경',
                        description=f'{line.product.name} 수량 변경: {old_quantity} -> {new_quantity}'
                    ))
                    line.requested_quantity = new_quantity
                    line.save()
            
            if logs_to_create:
                OrderLog.objects.bulk_create(logs_to_create)
                return JsonResponse({'message': '주문이 성공적으로 수정되었습니다.'})
            else:
                return JsonResponse({'message': '변경 사항이 없어 수정되지 않았습니다.'})

        except Exception as e:
            return JsonResponse({'error': f'수정 중 오류 발생: {str(e)}'}, status=400)


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

            # 15시 마감 체크 (관리자는 제외)
            if not request.user.is_staff:
                now = timezone.localtime()
                if now.hour >= 15:
                    tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')
                    if delivery_date <= tomorrow:
                        return JsonResponse({'error': '오후 3시가 지나 내일 납기는 불가능합니다. 모레부터 선택해주세요.'}, status=400)
            
            internal_customer = Customer.objects.get(name='내부 영업팀')

            # 품목 정보를 가져와 생산동별로 그룹화
            items_by_facility = defaultdict(list)
            product_ids = [item['product_id'] for item in items if int(item.get('quantity', 0)) > 0]
            products = Product.objects.in_bulk(product_ids)

            for item in items:
                if int(item.get('quantity', 0)) <= 0: continue
                product = products.get(int(item['product_id']))
                if product and product.production_facility:
                    items_by_facility[product.production_facility].append(item)
                else:
                    items_by_facility['미지정'].append(item)

            with transaction.atomic():
                for facility, facility_items in items_by_facility.items():
                    order = OrderHeader.objects.create(
                        customer=internal_customer,
                        requested_delivery_date=delivery_date,
                        memo=memo,
                        created_by=request.user,
                        production_facility=facility
                    )

                    for item in facility_items:
                        OrderLine.objects.create(
                            header=order,
                            product_id=item['product_id'],
                            requested_quantity=int(item['quantity']),
                            production_facility=facility
                        )
            
            return JsonResponse({'message': f'영업 발주가 성공적으로 등록되었습니다. {len(items_by_facility)}건의 주문으로 분리되었습니다.'}, status=201)

        except Customer.DoesNotExist:
            return JsonResponse({'error': '기본 설정된 "내부 영업팀" 거래처를 찾을 수 없습니다. 관리자에게 문의하세요.'}, status=500)
        except Exception as e:
            return JsonResponse({'error': f'발주 처리 중 오류 발생: {str(e)}'}, status=400)

@require_POST
@login_required
def cancel_order(request, order_id):
    try:
        order = get_object_or_404(OrderHeader, id=order_id, created_by=request.user)

        if order.total_status != '대기':
            return JsonResponse({'error': '생산이 시작된 주문은 취소할 수 없습니다.'}, status=400)

        order.delete()
        return JsonResponse({'message': '주문이 성공적으로 취소되었습니다.'}, status=200)

    except OrderHeader.DoesNotExist:
        return JsonResponse({'error': '주문을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)