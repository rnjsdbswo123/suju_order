from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from orders.models import OrderLine, FACILITY_LIST, OrderLog, OrderHeader
from django.utils import timezone
from collections import defaultdict
from orders.permissions import IsProductionTeam

from rest_framework import serializers
from django.db.models import Q
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin


# 생산동 관리 리스트

# 1. 화면: 생산 현황판
class ProductionStatusView(LoginRequiredMixin, TemplateView):
    template_name = 'production/production_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. 기본 데이터 가져오기
        lines = OrderLine.objects.select_related(
            'header', 
            'header__customer', 
            'header__created_by', 
            'product'
        ).order_by('header__requested_delivery_date')

        # -------------------------------------------------------
        # ★ 2. 검색 기능 (거래처 + 아이디 + 이름)
        # -------------------------------------------------------
        q = self.request.GET.get('q', '')
        if q:
            lines = lines.filter(
                Q(header__customer__name__icontains=q) |
                Q(header__created_by__username__icontains=q) | # 아이디 검색
                Q(header__created_by__last_name__icontains=q) | # 성 검색
                Q(header__created_by__first_name__icontains=q)  # 이름 검색
            )

        # 3. 날짜 필터
        date = self.request.GET.get('date', '')
        if date and date != 'ALL':
            lines = lines.filter(header__requested_delivery_date=date)

        # 4. 공장 필터
        facility = self.request.GET.get('facility', '')
        if facility and facility != 'ALL':
            lines = lines.filter(production_facility=facility)

        # 5. 데이터 그룹핑 (화면 표시용)
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

        # 6. 상태(색상) 결정
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

        # 7. 데이터 전달
        context['grouped_lines'] = final_list
        context['search_query'] = q
        context['selected_date'] = date
        context['selected_facility'] = facility
        
        # 공장 목록 처리
        try:
            context['facility_list'] = FACILITY_LIST
        except NameError:
            context['facility_list'] = ['제1공장', '제2공장'] 

        return context
# (나머지 UpdateView, CompleteView 등은 기존 코드 그대로 유지)
class OrderLineCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProductionTeam]
    
    def post(self, request, pk):
        line = get_object_or_404(OrderLine, pk=pk)
        input_qty = request.data.get('quantity')
        
        # 로그 기록
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
            # 로그 기록
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

        # 1) 수량이 바뀌었나?
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
            
        # 2) 메모가 바뀌었나?
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

        # 3) ★ [NEW] 생산동이 바뀌었나?
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
    editor_name = serializers.ReadOnlyField(source='editor.username') # 아이디 표시
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
        # 최신순으로 정렬해서 가져오기
        return OrderLog.objects.filter(line_id=line_id).order_by('-created_at')
    

class ProductionOrderListView(LoginRequiredMixin, TemplateView):
    template_name = 'production/production_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. 데이터 가져오기 (전체 품목)
        lines = OrderLine.objects.select_related(
            'header', 
            'header__customer', 
            'header__created_by', 
            'product'
        ).order_by('header__requested_delivery_date')

        # -------------------------------------------------------
        # ★ 2. 검색 기능 (여기가 핵심입니다!)
        # -------------------------------------------------------
        q = self.request.GET.get('q', '')
        if q:
            # 거래처 이름 OR 담당자 아이디 OR 담당자 성 OR 담당자 이름
            lines = lines.filter(
                Q(header__customer__name__icontains=q) |
                Q(header__created_by__username__icontains=q) |
                Q(header__created_by__last_name__icontains=q) |
                Q(header__created_by__first_name__icontains=q)
            )

        # 3. 날짜 필터 (선택된 날짜가 있을 때만 작동)
        date = self.request.GET.get('date', '')
        if date and date != 'ALL':
            lines = lines.filter(header__requested_delivery_date=date)

        # 4. 공장 필터
        facility = self.request.GET.get('facility', '')
        if facility and facility != 'ALL':
            lines = lines.filter(production_facility=facility)

        # 5. 데이터 가공 (화면 그리기용 그룹핑)
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

        # 6. 그룹 상태(색상) 결정
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

        # 7. 데이터 전달
        context['grouped_lines'] = final_list
        context['search_query'] = q
        context['selected_date'] = date
        context['selected_facility'] = facility
        
        # 공장 목록 안전하게 넣기
        try:
            context['facility_list'] = FACILITY_LIST
        except NameError:
            context['facility_list'] = ['제1공장', '제2공장'] 

        return context