# production/serializers.py
from rest_framework import serializers
from orders.models import OrderLine

class OrderLineFulfillmentSerializer(serializers.ModelSerializer):
    """ 수주 창에서 개별 품목 라인의 완료 처리를 위한 Serializer """
    customer_name = serializers.CharField(source='header.customer.name', read_only=True)
    requested_delivery_date = serializers.DateField(source='header.requested_delivery_date', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    created_by_name = serializers.CharField(source='header.created_by.username', read_only=True)

    class Meta:
        model = OrderLine
        fields = (
            'id', 'customer_name', 'product_name', 'requested_delivery_date',
            'requested_quantity', 'fulfilled_quantity', 'status', 'created_by_name'
        )
        # 완료 처리 시에는 완료 수량만 직접 입력받으므로 나머지는 read_only
        read_only_fields = (
            'customer_name', 'product_name', 'requested_delivery_date', 
            'requested_quantity', 'status', 'created_by_name'
        )