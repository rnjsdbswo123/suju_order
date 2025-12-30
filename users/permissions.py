from rest_framework.permissions import BasePermission
from users.models import Role # Role 모델을 참조합니다.
from django.core.exceptions import PermissionDenied

# 헬퍼 함수: 사용자가 특정 역할을 가지고 있는지 확인
def is_in_role(user, role_name):
    if not user.is_authenticated:
        return False
    # User 모델에 정의된 related_name 'user_roles'를 사용하여 효율적으로 확인
    return user.user_roles.filter(role__name=role_name).exists()


class IsAdminUser(BasePermission):
    """ 관리자 역할만 접근 허용 """
    def has_permission(self, request, view):
        return is_in_role(request.user, '관리자')

class IsOrderer(BasePermission):
    """ 발주자 역할만 접근 허용 """
    def has_permission(self, request, view):
        # 관리자는 모든 권한을 가진다고 가정하고, 관리자이거나 발주자 역할을 가진 경우 허용
        return is_in_role(request.user, '관리자') or is_in_role(request.user, '발주자')

class IsProductionUser(BasePermission):
    """ 생산부 역할만 접근 허용 """
    def has_permission(self, request, view):
        # 관리자는 모든 권한을 가진다고 가정하고, 관리자이거나 생산부 역할을 가진 경우 허용
        return is_in_role(request.user, '관리자') or is_in_role(request.user, '생산부')

class SalesRequiredMixin:
    """
    '영업' 또는 '관리자' 역할을 가진 사용자만 접근을 허용하는 믹스인
    """
    def dispatch(self, request, *args, **kwargs):
        if not (is_in_role(request.user, '영업팀') or is_in_role(request.user, '관리자')):
            raise PermissionDenied("영업 담당자 또는 관리자만 접근할 수 있습니다.")
        return super().dispatch(request, *args, **kwargs)