# SujuOrderSystem/utils.py
import threading

# 현재 요청을 보낸 사용자 정보를 저장할 스레드 로컬 객체
_thread_local = threading.local()

def get_current_user():
    """ 현재 요청을 처리하는 사용자 객체를 반환합니다. """
    return getattr(_thread_local, 'user', None)

def set_current_user(user):
    """ 현재 요청 사용자 객체를 저장합니다. """
    _thread_local.user = user

# 생산동 리스트 정의
FACILITY_LIST = ['A동', 'B동', 'C동', '관리동', '구운란동', '외부가공']
