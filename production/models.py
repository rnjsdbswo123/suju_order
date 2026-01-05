from django.conf import settings
from django.db import models
from masters.models import RawMaterial

class MaterialOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', '대기'),
        ('completed', '완료'),
        ('cancelled', '취소'),
    ]

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="요청자")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="상태")
    requested_delivery_date = models.DateField(null=True, blank=True, verbose_name="요청납기일")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="완료일시")

    def __str__(self):
        return f"Material Order #{self.pk} by {self.requester.username}"

    class Meta:
        verbose_name = "부자재 발주"
        verbose_name_plural = "부자재 발주 목록"
        ordering = ['-created_at']

class MaterialOrderItem(models.Model):
    material_order = models.ForeignKey(MaterialOrder, related_name='items', on_delete=models.CASCADE, verbose_name="부자재 발주")
    product = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, verbose_name="품목")
    
    # 신규 단위별 수량 필드
    box_quantity = models.PositiveIntegerField(verbose_name="박스 수량", default=0)
    bundle_quantity = models.PositiveIntegerField(verbose_name="번들 수량", default=0)
    each_quantity = models.PositiveIntegerField(verbose_name="낱개 수량", default=0)

    def __str__(self):
        parts = []
        if self.box_quantity > 0:
            parts.append(f"{self.box_quantity} 박스")
        if self.bundle_quantity > 0:
            parts.append(f"{self.bundle_quantity} 묶음")
        if self.each_quantity > 0:
            parts.append(f"{self.each_quantity} 개")
        
        quantity_str = ", ".join(parts)
        if not quantity_str:
            return f"{self.product.name} - 0개"
            
        return f"{self.product.name} - {quantity_str}"

    class Meta:
        verbose_name = "부자재 발주 품목"
        verbose_name_plural = "부자재 발주 품목들"
