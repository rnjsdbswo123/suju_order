from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView, View, ListView, CreateView, UpdateView
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from orders.models import OrderLine, OrderLog, OrderHeader
from SujuOrderSystem.utils import FACILITY_LIST
from django.utils import timezone
from collections import defaultdict
from orders.permissions import IsProductionTeam
from users.permissions import is_in_role
from rest_framework import serializers
from django.db.models import Q, Sum, F
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
import json

from .models import MaterialOrder, MaterialOrderItem
from masters.models import RawMaterial

# ====================================================================
# 부자재 발주 기능
# ====================================================================

class MaterialOrderRequestView(LoginRequiredMixin, CreateView):
    model = MaterialOrder
    fields = []
    template_name = 'production/material_order_form.html'
    success_url = reverse_lazy('production:material-order-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('search', '')
        products = []
        if search_query:
            products = RawMaterial.objects.filter(
                Q(name__icontains=search_query) | Q(barcode=search_query)
            ).filter(is_active=True)
        
        context['products'] = products
        context['search_query'] = search_query
        return context

    def form_valid(self, form):
        with transaction.atomic():
            order = form.save(commit=False)
            order.requester = self.request.user
            order.requested_delivery_date = self.request.POST.get('requested_delivery_date')
            order.save()

            product_ids = self.request.POST.getlist('product_id')

            for product_id in product_ids:
                try:
                    box_qty = int(self.request.POST.get(f'box_{product_id}', 0) or 0)
                    bundle_qty = int(self.request.POST.get(f'bundle_{product_id}', 0) or 0)
                    each_qty = int(self.request.POST.get(f'each_{product_id}', 0) or 0)

                    if (box_qty + bundle_qty + each_qty) > 0:
                        MaterialOrderItem.objects.create(
                            material_order=order,
                            product_id=product_id,
                            box_quantity=box_qty,
                            bundle_quantity=bundle_qty,
                            each_quantity=each_qty
                        )
                except ValueError:
                    # 수량 변환에 실패한 경우 해당 품목은 무시
                    continue
        
        if not order.items.exists():
            order.delete()
        
        return super().form_valid(form)


class MaterialOrderListView(LoginRequiredMixin, ListView):
    model = MaterialOrder
    template_name = 'production/material_order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        if is_in_role(user, '관리자') or is_in_role(user, '자재담당자'):
            queryset = MaterialOrder.objects.all()
        elif is_in_role(user, '생산팀'):
            queryset = MaterialOrder.objects.filter(requester=user)
        else:
            queryset = MaterialOrder.objects.none()

        # date 파라미터가 없으면 오늘 날짜로, 값이 비어있으면 전체(None)로 취급
        date_filter = self.request.GET.get('date', timezone.localdate().strftime('%Y-%m-%d'))
        if date_filter: # date_filter가 빈 문자열이 아닌 경우에만 필터링
            queryset = queryset.filter(created_at__date=date_filter)

        return queryset.prefetch_related('items__product').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # date 파라미터가 없으면 오늘 날짜를 기본값으로 설정
        context['date_filter'] = self.request.GET.get('date', timezone.localdate().strftime('%Y-%m-%d'))
        return context

class MaterialOrderStatusUpdateView(LoginRequiredMixin, UpdateView):
    model = MaterialOrder
    fields = ['status']
    template_name = 'production/material_order_detail.html'
    context_object_name = 'order'
    success_url = reverse_lazy('production:material-order-list')

    def form_valid(self, form):
        order = form.save(commit=False)
        if form.cleaned_data['status'] == 'completed':
            order.completed_at = timezone.now()
        else:
            order.completed_at = None
        order.save()
        return super().form_valid(form)

@require_POST
@login_required
def material_order_delete(request, pk):
    order = get_object_or_404(MaterialOrder, pk=pk)
    
    if not (is_in_role(request.user, '관리자') or order.requester == request.user):
        messages.error(request, '삭제 권한이 없습니다.')
        return redirect('production:material-order-list')

    if order.status != 'pending':
        messages.error(request, '대기 상태인 발주만 삭제할 수 있습니다.')
        return redirect('production:material-order-list')
        
    order.delete()
    messages.success(request, f'발주 #{order.pk}이(가) 성공적으로 삭제되었습니다.')
    return redirect('production:material-order-list')


class MaterialOrderQuantityUpdateView(LoginRequiredMixin, View):
    template_name = 'production/material_order_edit_form.html'

    def get(self, request, pk):
        order = get_object_or_404(MaterialOrder.objects.prefetch_related('items__product'), pk=pk)
        if order.status != 'pending':
            messages.error(request, '대기 상태인 발주만 수정할 수 있습니다.')
            return redirect('production:material-order-list')
        
        context = {'order': order}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        with transaction.atomic():
            order = get_object_or_404(MaterialOrder.objects.prefetch_related('items'), pk=pk)
            if order.status != 'pending':
                messages.error(request, '대기 상태인 발주만 수정할 수 있습니다.')
                return redirect('production:material-order-list')

            for item in order.items.all():
                new_quantity_str = request.POST.get(f'quantity_{item.id}')
                if new_quantity_str:
                    new_quantity = int(new_quantity_str)
                    if new_quantity > 0:
                        if item.quantity != new_quantity:
                            item.quantity = new_quantity
                            item.save()
                    else: # 수량이 0이하이면 해당 아이템 삭제
                        item.delete()
            
            # 모든 아이템이 삭제되었다면 발주 자체를 삭제
            if not order.items.exists():
                order.delete()
                messages.warning(request, f'발주 #{order.pk}의 모든 품목이 삭제되어 발주 자체가 취소되었습니다.')
            else:
                messages.success(request, f'발주 #{order.pk}의 수량이 성공적으로 수정되었습니다.')

        return redirect('production:material-order-list')


# ====================================================================
# 기존 생산 현황판 기능
# ====================================================================

class ProductionStatusView(LoginRequiredMixin, TemplateView):
    template_name = 'production/production_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Get parameters from request
        group_by = self.request.GET.get('group_by', 'product')
        sort_by = self.request.GET.get('sort', 'delivery_date')
        sort_dir = self.request.GET.get('dir', 'asc')
        q = self.request.GET.get('q', '')
        date = self.request.GET.get('date', timezone.localdate().strftime('%Y-%m-%d'))
        facility = self.request.GET.get('facility', '')
        status_filter = self.request.GET.get('status', 'all')

        # 2. Base queryset
        lines = OrderLine.objects.select_related(
            'header', 
            'header__customer', 
            'header__created_by', 
            'product'
        )

        # 3. Filtering
        if q:
            lines = lines.filter(
                Q(header__customer__name__icontains=q) |
                Q(header__created_by__username__icontains=q) |
                Q(header__created_by__last_name__icontains=q) |
                Q(header__created_by__first_name__icontains=q) |
                Q(product__name__icontains=q)
            )

        if date and date != 'ALL':
            lines = lines.filter(header__requested_delivery_date=date)

        if facility and facility != 'ALL':
            facility_prefix = facility.removesuffix('동')
            lines = lines.filter(production_facility__startswith=facility_prefix)
        
        if status_filter == 'completed':
            lines = lines.filter(status='COMPLETED')
        elif status_filter == 'incomplete':
            lines = lines.exclude(status='COMPLETED')

        # 4. Branch logic based on grouping
        if group_by == 'time':
            # Ungrouped view, sorted by time
            context['results'] = lines.order_by('-header__created_at')
        else:
            # Grouped view (product or customer)
            grouped_data = defaultdict(lambda: {'lines': [], 'total_qty': 0})
            
            for line in lines:
                key_obj, key_id = None, None
                if group_by == 'product':
                    key_obj, key_id = line.product, line.product_id
                    if 'product' not in grouped_data[key_id]:
                        grouped_data[key_id]['product'] = key_obj
                else: # group_by == 'customer'
                    key_obj, key_id = line.header.customer, line.header.customer_id
                    if 'customer' not in grouped_data[key_id]:
                        grouped_data[key_id]['customer'] = key_obj

                grouped_data[key_id]['lines'].append(line)

            # Status filtering and Sorting within groups
            sort_field_map = {
                'delivery_date': 'header.requested_delivery_date',
                'customer': 'header.customer.name',
                'requester': 'header.created_by.username',
                'product': 'product.name',
                'order_time': 'header.created_at',
                'memo': 'header.memo'
            }
            sort_key = sort_field_map.get(sort_by, 'header.requested_delivery_date')

            final_list = []
            from operator import attrgetter
            for key, group in grouped_data.items():
                original_lines = group['lines']
                
                # Sort lines within the group
                try:
                    sorted_lines = sorted(original_lines, key=attrgetter(sort_key), reverse=(sort_dir == 'desc'))
                except AttributeError:
                    sorted_lines = sorted(original_lines, key=lambda l: getattr(l, sort_key, None), reverse=(sort_dir == 'desc'))

                group['lines'] = sorted_lines
                group['total_qty'] = sum(l.requested_quantity for l in sorted_lines)
                
                any_completed = any(l.status == 'COMPLETED' for l in original_lines)
                all_completed = all(l.status == 'COMPLETED' for l in original_lines)

                if all_completed:
                    total_req = sum(l.requested_quantity for l in original_lines)
                    total_ful = sum(l.fulfilled_quantity for l in original_lines)
                    group['group_status'] = 'PERFECT' if total_req == total_ful else 'IMPERFECT'
                elif any_completed:
                    group['group_status'] = 'PARTIAL'
                else:
                    group['group_status'] = 'PENDING'
                
                final_list.append(group)
            
            # Sort the final groups themselves
            if group_by == 'product':
                final_list.sort(key=lambda g: g.get('product').name if g.get('product') else '')
            else: # group_by == 'customer'
                final_list.sort(key=lambda g: g.get('customer').name if g.get('customer') else '')
            context['results'] = final_list
        
        # 6. Pass common context to template
        context['search_query'] = q
        context['selected_date'] = date
        context['selected_facility'] = facility
        context['selected_status'] = status_filter
        context['facility_list'] = FACILITY_LIST
        context['group_by'] = group_by
        context['sort_by'] = sort_by
        context['sort_dir'] = sort_dir
        context['next_sort_dir'] = 'desc' if sort_dir == 'asc' else 'asc'

        return context

@login_required
def pending_production_summary(request):
    lines = OrderLine.objects.select_related('header', 'product').exclude(status='COMPLETED')
    date = request.GET.get('date')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    facility = request.GET.get('facility')

    if date and date != 'ALL':
        lines = lines.filter(header__requested_delivery_date=date)
    if date_from:
        lines = lines.filter(header__requested_delivery_date__gte=date_from)
    if date_to:
        lines = lines.filter(header__requested_delivery_date__lte=date_to)
    if facility and facility != 'ALL':
        lines = lines.filter(production_facility=facility)
    grouped = {}

    for line in lines:
        date_str = line.header.requested_delivery_date.strftime('%Y-%m-%d')
        key = (date_str, line.product_id, line.production_facility)
        if key not in grouped:
            grouped[key] = {
                'date': date_str,
                'product_id': line.product_id,
                'product_name': line.product.name,
                'product_sku': line.product.sku,
                'production_facility': line.production_facility,
                'total_qty': 0,
                'line_count': 0,
                'line_ids': [],
            }
        grouped[key]['total_qty'] += line.requested_quantity
        grouped[key]['line_count'] += 1
        grouped[key]['line_ids'].append(line.id)

    items = sorted(grouped.values(), key=lambda item: (item['date'], item['product_name']))
    return JsonResponse({'items': items})

class OrderLineCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProductionTeam]
    
    def post(self, request, pk):
        line = get_object_or_404(OrderLine, pk=pk)
        input_qty = request.data.get('quantity')
        
        final_qty = int(input_qty) if input_qty is not None else line.requested_quantity
        OrderLog.objects.create(
            line=line,
            editor=request.user,
            change_type="최초 완료",
            description=f"완료 수량 입력: {final_qty}개"
        )

        line.fulfilled_quantity = final_qty
        line.status = 'COMPLETED'
        line.save()
        return Response({"message": "완료 처리되었습니다."}, status=status.HTTP_200_OK)

class OrderLineBulkCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProductionTeam]
    
    def post(self, request):
        ids = request.data.get('ids', [])
        lines = OrderLine.objects.filter(id__in=ids)
        
        for line in lines:
            OrderLog.objects.create(
                line=line,
                editor=request.user,
                change_type="일괄 완료",
                description=f"요청 수량({line.requested_quantity})으로 일괄 처리됨"
            )
            line.fulfilled_quantity = line.requested_quantity
            line.status = 'COMPLETED'
            line.save()
            
        return Response({"message": f"{len(lines)}건 처리 완료"}, status=status.HTTP_200_OK)

class OrderLineBulkUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProductionTeam]

    def post(self, request, *args, **kwargs):
        data = request.data
        line_ids = data.get('ids', [])
        new_delivery_date = data.get('delivery_date')
        new_facility = data.get('production_facility')

        if not line_ids:
            return Response({"error": "선택된 항목이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not new_delivery_date and not new_facility:
            return Response({"error": "변경할 내용이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        lines_to_update = OrderLine.objects.filter(id__in=line_ids).select_related('header')
        header_ids = lines_to_update.values_list('header_id', flat=True).distinct()
        headers = OrderHeader.objects.filter(id__in=header_ids).prefetch_related('lines')
        lines_by_header = defaultdict(list)
        for line in lines_to_update:
            lines_by_header[line.header_id].append(line)

        with transaction.atomic():
            log_entries = []
            
            # 1. 생산동 변경 (OrderLine)
            if new_facility:
                for line in lines_to_update:
                    if line.production_facility != new_facility:
                        log_entries.append(OrderLog(
                            line=line, editor=request.user, change_type="일괄 생산동 변경",
                            description=f"{line.production_facility} -> {new_facility}"
                        ))
                lines_to_update.update(production_facility=new_facility)

            # 2. 납기일 변경 (OrderHeader)
            if new_delivery_date:
                for header in headers:
                    selected_lines = lines_by_header.get(header.id, [])
                    if not selected_lines:
                        continue

                    if str(header.requested_delivery_date) != new_delivery_date:
                        for line in selected_lines:
                            log_entries.append(OrderLog(
                                line=line, editor=request.user, change_type="일괄 납기일 변경",
                                description=f"{header.requested_delivery_date} -> {new_delivery_date}"
                            ))

                        header_lines = list(header.lines.all())
                        if len(selected_lines) == len(header_lines):
                            header.requested_delivery_date = new_delivery_date
                            update_fields = ['requested_delivery_date']
                            if new_facility and header.production_facility != new_facility:
                                header.production_facility = new_facility
                                update_fields.append('production_facility')
                            header.save(update_fields=update_fields)
                        else:
                            new_header = OrderHeader.objects.create(
                                customer=header.customer,
                                requested_delivery_date=new_delivery_date,
                                memo=header.memo,
                                created_by=header.created_by,
                                production_facility=new_facility or header.production_facility
                            )
                            OrderLine.objects.filter(
                                id__in=[line.id for line in selected_lines]
                            ).update(header=new_header)

            # 생산동만 변경하는 경우 헤더 동기화
            if new_facility and not new_delivery_date:
                for header in headers:
                    selected_lines = lines_by_header.get(header.id, [])
                    if not selected_lines:
                        continue
                    if len(selected_lines) == len(list(header.lines.all())):
                        if header.production_facility != new_facility:
                            header.production_facility = new_facility
                            header.save(update_fields=['production_facility'])
            
            if log_entries:
                OrderLog.objects.bulk_create(log_entries)

        return Response({"message": f"{len(line_ids)}개 품목이 수정되었습니다."}, status=status.HTTP_200_OK)

    
class OrderLineUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProductionTeam]
    
    def post(self, request, pk):
        line = get_object_or_404(OrderLine.objects.select_related('header'), pk=pk)
        
        new_qty = request.data.get('fulfilled_quantity')
        new_memo = request.data.get('memo')
        new_facility = request.data.get('production_facility')
        new_delivery_date = request.data.get('delivery_date')

        with transaction.atomic():
            if new_delivery_date and str(line.header.requested_delivery_date) != new_delivery_date:
                OrderLog.objects.create(
                    line=line,
                    editor=request.user,
                    change_type="납기일 변경",
                    description=f"{line.header.requested_delivery_date} -> {new_delivery_date}"
                )

                if line.header.lines.count() == 1:
                    line.header.requested_delivery_date = new_delivery_date
                    update_fields = ['requested_delivery_date']
                    if new_facility and line.header.production_facility != new_facility:
                        line.header.production_facility = new_facility
                        update_fields.append('production_facility')
                    line.header.save(update_fields=update_fields)
                else:
                    new_header = OrderHeader.objects.create(
                        customer=line.header.customer,
                        requested_delivery_date=new_delivery_date,
                        memo=line.header.memo,
                        created_by=line.header.created_by,
                        production_facility=new_facility or line.header.production_facility
                    )
                    line.header = new_header

            if new_qty is not None:
                new_qty = int(new_qty)
                if line.fulfilled_quantity != new_qty:
                    OrderLog.objects.create(
                        line=line,
                        editor=request.user,
                        change_type="수량 수정",
                        description=f"{line.fulfilled_quantity}개 → {new_qty}개"
                    )
                    line.fulfilled_quantity = new_qty
                
            if new_memo is not None:
                old_memo = line.header.memo or ""
                if old_memo != new_memo:
                    OrderLog.objects.create(
                        line=line,
                        editor=request.user,
                        change_type="메모 수정",
                        description="발주 메모 내용 변경됨"
                    )
                    line.header.memo = new_memo
                    line.header.save(update_fields=['memo'])

            if new_facility and line.production_facility != new_facility:
                OrderLog.objects.create(
                    line=line,
                    editor=request.user,
                    change_type="생산동 변경",
                    description=f"{line.production_facility} → {new_facility}"
                )
                line.production_facility = new_facility
                if line.header.lines.count() == 1 and line.header.production_facility != new_facility:
                    line.header.production_facility = new_facility
                    line.header.save(update_fields=['production_facility'])
                
            line.save()
        return Response({"message": "수정되었습니다."}, status=status.HTTP_200_OK)

class LogSerializer(serializers.ModelSerializer):
    editor_name = serializers.ReadOnlyField(source='editor.username')
    created_at_fmt = serializers.SerializerMethodField()

    class Meta:
        model = OrderLog
        fields = ['editor_name', 'change_type', 'description', 'created_at_fmt']
    
    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    
class OrderLineLogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogSerializer

    def get_queryset(self):
        line_id = self.kwargs['pk']
        return OrderLog.objects.filter(line_id=line_id).order_by('-created_at')
    
class ProductionOrderListView(LoginRequiredMixin, TemplateView):
    template_name = 'production/production_status.html'

    def get_context_data(self, **kwargs):
        # This view seems to be a duplicate of ProductionStatusView.
        # I'm keeping it for now as it was in the original file.
        context = super().get_context_data(**kwargs)
        lines = OrderLine.objects.select_related('header', 'header__customer', 'header__created_by', 'product').order_by('header__requested_delivery_date')
        q = self.request.GET.get('q', '')
        if q:
            lines = lines.filter(
                Q(header__customer__name__icontains=q) |
                Q(header__created_by__username__icontains=q) |
                Q(header__created_by__last_name__icontains=q) |
                Q(header__created_by__first_name__icontains=q)
            )
        date = self.request.GET.get('date', '')
        if date and date != 'ALL':
            lines = lines.filter(header__requested_delivery_date=date)
        facility = self.request.GET.get('facility', '')
        if facility and facility != 'ALL':
            lines = lines.filter(production_facility=facility)
        grouped_data = {}
        for line in lines:
            pid = line.product.id
            if pid not in grouped_data:
                grouped_data[pid] = {'product': line.product, 'lines': [], 'total_qty': 0, 'group_status': 'PENDING'}
            grouped_data[pid]['lines'].append(line)
            grouped_data[pid]['total_qty'] += line.requested_quantity
        final_list = []
        for pid, group in grouped_data.items():
            all_completed = all(l.status == 'COMPLETED' for l in group['lines'])
            if all_completed:
                total_req = sum(l.requested_quantity for l in group['lines'])
                total_ful = sum(l.fulfilled_quantity for l in group['lines'])
                if total_req == total_ful:
                    group['group_status'] = 'PERFECT'
                else:
                    group['group_status'] = 'IMPERFECT'
            final_list.append(group)
        context['grouped_lines'] = final_list
        context['search_query'] = q
        context['selected_date'] = date
        context['selected_facility'] = facility
        try:
            context['facility_list'] = FACILITY_LIST
        except NameError:
            context['facility_list'] = ['제1공장', '제2공장'] 
        return context
        
# ====================================================================
# API v2 for production status
# ====================================================================

@login_required
def production_summary_api(request):
    """
    생산 현황판의 요약 데이터를 반환하는 API
    - 날짜, 생산동, 상태별 필터링 기능 추가
    """
    # Get query params
    date = request.GET.get('date')
    facility = request.GET.get('facility')
    status_filter = request.GET.get('status')

    # Base queryset
    lines = OrderLine.objects.select_related('product', 'header')

    # Filter by date
    if date:
        lines = lines.filter(header__requested_delivery_date=date)

    # Filter by facility
    if facility:
        lines = lines.filter(production_facility=facility)

    # Group by product and aggregate
    summary = lines.values('product__id', 'product__name').annotate(
        total_requested=Sum('requested_quantity'),
        total_fulfilled=Sum('fulfilled_quantity')
    ).order_by('product__name')
    
    # Filter by status (after aggregation)
    if status_filter == 'completed':
        # Show only products where requested equals fulfilled
        summary = summary.filter(total_requested=F('total_fulfilled'))
    elif status_filter == 'incomplete':
        # Show products where requested does not equal fulfilled
        summary = summary.exclude(total_requested=F('total_fulfilled'))

    return JsonResponse(list(summary), safe=False)


@login_required
def production_detail_api(request):
    """
    특정 날짜, 특정 품목에 대한 상세 주문 내역을 반환하는 API
    """
    date = request.GET.get('date')
    product_id = request.GET.get('product_id')

    lines = OrderLine.objects.filter(
        header__requested_delivery_date=date,
        product_id=product_id
    ).select_related('header__customer', 'header__created_by')

    details = []
    for line in lines:
        details.append({
            'customer_name': line.header.customer.name,
            'created_by': line.header.created_by.username,
            'facility': line.production_facility,
            'status': '완료' if line.status == 'COMPLETED' else '미완료',
            'fulfilled_qty': line.fulfilled_quantity,
            'requested_qty': line.requested_quantity,
            'line_id': line.id
        })
    
    return JsonResponse(details, safe=False)

@login_required
def check_production_updates(request):
    latest_id = request.GET.get('latest_id', 0)
    
    q = request.GET.get('q', '')
    date = request.GET.get('date')
    facility = request.GET.get('facility', '')

    try:
        latest_id = int(latest_id)
    except (ValueError, TypeError):
        latest_id = 0

    lines = OrderLine.objects.filter(id__gt=latest_id)

    if q:
        lines = lines.filter(
            Q(header__customer__name__icontains=q) |
            Q(header__created_by__username__icontains=q) |
            Q(product__name__icontains=q)
        )
    
    if date and date != 'ALL':
        lines = lines.filter(header__requested_delivery_date=date)

    if facility and facility != 'ALL':
        facility_prefix = facility.removesuffix('동')
        lines = lines.filter(production_facility__startswith=facility_prefix)
    
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'completed':
        lines = lines.none() 

    count = lines.count()
    
    return JsonResponse({'new_items_count': count})
