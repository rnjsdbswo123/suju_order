# masters/serializers.py
from rest_framework import serializers
from .models import Customer, Product, CustomerProductMap

# 1. 거래처 Serializer
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        
# 2. 품목 Serializer
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        # fields = '__all__' 로 되어있다면 name과 sku가 포함되지만, 
        # 명시적으로 써주는 것이 가장 확실합니다.
        fields = ['id', 'name', 'sku', 'unit_price']
        
# 3. 거래처-품목 매핑 Serializer (조회용)
class CustomerProductMapSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = CustomerProductMap
        fields = ('id', 'customer', 'product', 'product_name', 'product_sku')