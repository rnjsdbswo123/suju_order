# masters/models.py
from django.conf import settings
from django.db import models

# 1. 거래처 (Customer) 모델
class Customer(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="거래처명")
    business_id = models.CharField(max_length=20, null=True, blank=True, verbose_name="사업자번호")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

# 2. 품목 (Product) 모델
class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="품목명")
    sku = models.CharField(max_length=50, unique=True, verbose_name="품목코드")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="단가")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    
    # 향후 확장을 위한 필드: 생산동 (현재는 사용하지 않음)
    production_facility = models.CharField(max_length=50, null=True, blank=True, verbose_name="생산동") 
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "품목"
        verbose_name_plural = "품목들"

    def __str__(self):
        return f"[{self.sku}] {self.name}"

# 3. 거래처-품목 매핑 (CustomerProductMap) 모델
class CustomerProductMap(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('customer', 'product') # 특정 거래처에 같은 품목이 중복 매핑되지 않도록 설정
        verbose_name = "거래처별 취급 품목"
        
    def __str__(self):
        return f"{self.customer.name} -> {self.product.name}"

# 4. 영업사원 선호 품목 (SalesFavoriteProduct) 모델
class SalesFavoriteProduct(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        verbose_name = '영업사원 선호 품목'
        verbose_name_plural = '영업사원 선호 품목들'

    def __str__(self):
        try:
            return f'{self.user.username} - {self.product.name}'
        except Exception:
            return f'Unknown User - {self.product.name}'