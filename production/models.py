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
    quantity = models.PositiveIntegerField(verbose_name="수량")

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

    class Meta:
        verbose_name = "부자재 발주 품목"
        verbose_name_plural = "부자재 발주 품목들"
