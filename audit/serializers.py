# audit/serializers.py
from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    # 사용자 ID 대신 이름(username)을 보여주기 위한 설정
    user_name = serializers.CharField(source='user.username', read_only=True)
    # action 필드의 Choice 값(CREATE -> 등록)을 읽기 쉬운 한글로 변환
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            'id', 
            'user_name', 
            'action', 
            'action_display', 
            'model_name', 
            'object_id', 
            'details', 
            'timestamp'
        )