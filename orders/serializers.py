from rest_framework import serializers
from .models import OrderHeader, OrderLine
from masters.models import Customer
from django.utils import timezone

# 1. OrderLine Serializer (단순 조회용으로만 남겨둠)
class OrderLineSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderLine
        # 검사용 필드가 아니라 조회용 필드만 남김
        fields = (
            'id', 'product_id', 'product_sku', 'product_name', 
            'requested_quantity', 'fulfilled_quantity', 'status', 'production_facility'
        )

# 2. OrderHeader Serializer (저장용)
class OrderHeaderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.filter(is_active=True), 
        source='customer', 
        write_only=True
    )

    # ★ 중요: 여기에 'lines = ...' 코드가 없어야 합니다!
    # ★ 중요: Meta fields에도 'lines'가 없어야 합니다!

    class Meta:
        model = OrderHeader
        fields = ['id', 'customer_id', 'customer_name', 'requested_delivery_date', 'memo'] 
        read_only_fields = ('created_by', 'created_at',)

    def validate_requested_delivery_date(self, value):
        now_kr = timezone.localtime(timezone.now())
        if value < now_kr.date():
            raise serializers.ValidationError("과거 납기일은 선택할 수 없습니다.")
        return value