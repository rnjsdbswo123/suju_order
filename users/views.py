from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .permissions import is_in_role

@login_required
def role_based_login_redirect_view(request):
    """
    로그인 후 사용자의 역할에 따라 적절한 페이지로 리디렉션합니다.
    """
    if is_in_role(request.user, '관리자'):
        # 관리자는 일반 발주창으로
        return redirect('order-form')
    elif is_in_role(request.user, '영업팀'):
        # 영업팀은 영업 발주창으로
        return redirect('sales-order-create')
    elif is_in_role(request.user, '생산팀'):
        # 생산팀은 수주 현황판으로
        return redirect('production:production-status-ui')
    else:
        # 그 외 역할은 내 발주 목록으로 리디렉션
        return redirect('my-order-list')