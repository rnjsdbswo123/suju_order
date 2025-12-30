# audit/models.py
from django.db import models
from users.models import User # 사용자 참조

class AuditLog(models.Model):
    """ 시스템 내 중요 작업(발주, 수주, 마스터 데이터 변경)에 대한 감사 로그 """
    ACTION_CHOICES = (
        ('CREATE', '등록'), 
        ('UPDATE', '수정'), 
        ('DELETE', '삭제'), 
        ('FULFILL', '수주 완료') # 완료 수량 입력 및 상태 변경
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="작업자")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="작업 유형")
    model_name = models.CharField(max_length=50, verbose_name="대상 모델") # 예: OrderHeader, Customer
    object_id = models.IntegerField(verbose_name="객체 ID")
    
    # 변경된 내용을 JSON 형태로 저장 (필요시)
    details = models.JSONField(null=True, blank=True, verbose_name="변경 상세 내역") 
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="작업 시각")
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "감사 로그"
        
    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user} - {self.action} on {self.model_name} #{self.object_id}"