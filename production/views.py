from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView, View, ListView, CreateView, UpdateView
from django.shortcuts import get_object_or_404, redirect, render
from orders.models import OrderLine, FACILITY_LIST, OrderLog, OrderHeader
from django.utils import timezone
from collections import defaultdict
from orders.permissions import IsProductionTeam
from users.permissions import is_in_role
from rest_framework import serializers
from django.db.models import Q
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
            order.save()

            product_ids = self.request.POST.getlist('product_id')
            quantities = self.request.POST.getlist('quantity')

            for i, product_id in enumerate(product_ids):
                if product_id and quantities[i]:
                    product = RawMaterial.objects.get(id=product_id)
                    quantity = int(quantities[i])
                    if quantity > 0:
                        MaterialOrderItem.objects.create(
                            material_order=order,
                            product=product,
                            quantity=quantity
                        )
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

        date_filter = self.request.GET.get('date')
        if date_filter:
            queryset = queryset.filter(created_at__date=date_filter)

        return queryset.prefetch_related('items__product').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date_filter'] = self.request.GET.get('date', '')
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
        
        lines = OrderLine.objects.select_related(
            'header', 
            'header__customer', 
            'header__created_by', 
            'product'
        ).order_by('header__requested_delivery_date')

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
                grouped_data[pid] = {
                    'product': line.product,
                    'lines': [],
                    'total_qty': 0,
                    'group_status': 'PENDING'
                }
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
    
class OrderLineUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProductionTeam]
    
    def post(self, request, pk):
        line = get_object_or_404(OrderLine, pk=pk)
        
        new_qty = request.data.get('fulfilled_quantity')
        new_memo = request.data.get('memo')
        new_facility = request.data.get('production_facility')

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
                line.header.save()

        if new_facility and line.production_facility != new_facility:
            OrderLog.objects.create(
                line=line,
                editor=request.user,
                change_type="생산동 변경",
                description=f"{line.production_facility} → {new_facility}"
            )
            line.production_facility = new_facility
            
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
