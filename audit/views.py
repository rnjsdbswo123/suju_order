# audit/views.py
from rest_framework import generics
from users.permissions import IsAdminUser
from .models import AuditLog
from .serializers import AuditLogSerializer
from django.utils import timezone

class AuditLogListAPIView(generics.ListAPIView):
    """ 관리자를 위한 감사 로그 조회 뷰 """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser] # 관리자만 접근 가능

    # 요구사항: 6개월 보관 -> 쿼리셋에서 6개월 이전 로그는 제외
    def get_queryset(self):
        from datetime import timedelta
        # 현재 시각 기준 6개월 전
        six_months_ago = timezone.now() - timedelta(days=30 * 6) 
        # 최신 순으로 정렬하여 6개월 이내 로그만 반환
        return AuditLog.objects.filter(timestamp__gte=six_months_ago).order_by('-timestamp')