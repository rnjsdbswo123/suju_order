# users/middleware.py
from SujuOrderSystem.utils import set_current_user

class CurrentUserMiddleware:
    """ 
    모든 요청에 대해 현재 로그인된 사용자를 스레드 로컬에 저장하는 미들웨어.
    Signal 핸들러에서 request.user에 접근하기 위해 사용됩니다.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 요청 처리 전: 사용자를 저장
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)

        response = self.get_response(request)
        
        # 응답 처리 후: 사용자를 삭제하여 메모리 누수 방지
        set_current_user(None) 
        
        return response