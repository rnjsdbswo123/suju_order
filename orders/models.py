from django.db import models
from django.conf import settings  # ★ [수정] User 대신 settings를 가져옵니다.
from masters.models import Customer, Product
from SujuOrderSystem.utils import FACILITY_LIST

class OrderHeader(models.Model):
    """ 발주 요청의 헤더 정보 (거래처, 납기일, 메모 등) """
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT, 
        verbose_name="거래처"
    )
    requested_delivery_date = models.DateField(verbose_name="요청 납기일")
    memo = models.TextField(null=True, blank=True, verbose_name="메모")
    
    # ★ [수정] User -> settings.AUTH_USER_MODEL
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='placed_orders', 
        verbose_name="작성자"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="발주 등록일")
    
    production_facility = models.CharField(max_length=50, verbose_name="생산동", default=FACILITY_LIST[0])

    def __str__(self):
        return f"발주 #{self.pk} - {self.customer.name}"

    @property
    def total_status(self):
        """ 발주 헤더의 전체 상태를 계산하는 프로퍼티 """
        lines = self.lines.all()
        if not lines.exists():
            return '대기'

        statuses = lines.values_list('status', flat=True)
        
        if all(status == 'COMPLETED' for status in statuses):
            return '완료'
        elif any(status == 'COMPLETED' for status in statuses):
            return '부분완료'
        else:
            return '대기'

class OrderLine(models.Model):
    """ 발주 헤더에 속한 품목별 상세 발주 내역 """
    
    STATUS_CHOICES = (
        ('PENDING', '대기'),
        ('IN_PROGRESS', '진행중'),
        ('COMPLETED', '완료'),
    )
    
    header = models.ForeignKey(
        OrderHeader, 
        on_delete=models.CASCADE, 
        related_name='lines', 
        verbose_name="발주 헤더"
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT, 
        verbose_name="품목"
    )
    
    production_facility = models.CharField(max_length=50, default=FACILITY_LIST[0], verbose_name="생산동")
    
    requested_quantity = models.PositiveIntegerField(verbose_name="요청 수량")
    fulfilled_quantity = models.PositiveIntegerField(default=0, verbose_name="완료 수량")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="생산 상태")
    
    def save(self, *args, **kwargs):
        # 생산동 정보가 비어있으면 -> 품목 마스터의 정보를 가져옴
        if not self.production_facility and self.product:
            if hasattr(self.product, 'production_facility'):
                self.production_facility = self.product.production_facility
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.header.pk} - {self.product.name} ({self.requested_quantity}개)"
    
class OrderLog(models.Model):
    """ 품목별 수정 이력 기록장 """
    line = models.ForeignKey(OrderLine, on_delete=models.CASCADE, related_name='logs')
    
    # ★ [수정] User -> settings.AUTH_USER_MODEL
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="수정자"
    )
    change_type = models.CharField(max_length=50, verbose_name="변경 유형")
    description = models.TextField(verbose_name="변경 내용")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="변경 일시")

    def __str__(self):
        return f"[{self.change_type}] {self.editor} ({self.created_at})"