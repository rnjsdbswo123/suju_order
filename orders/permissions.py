from rest_framework import permissions
from users.permissions import is_in_role

class IsSalesTeam(permissions.BasePermission):
    """ 영업팀 권한 (관리자는 프리패스) """
    message = "영업팀 권한이 필요합니다."

    def has_permission(self, request, view):
        user = request.user
        
        # ★ [디버깅] 터미널에 현재 접속한 사람의 정보를 찍어봅니다.
        print(f"\n====== [권한 검사] 사용자: {user.username} ======")
        print(f" - 관리자 여부: {user.is_superuser}")
        
        # 사용자가 속한 모든 그룹의 이름을 리스트로 가져옴
        user_groups = [g.name for g in user.groups.all()]
        print(f" - 소속 그룹: {user_groups}")
        print(f" - 코드에서 찾는 그룹명: '영업팀'")

        # 1. 관리자면 통과
        if user.is_superuser:
            print(" -> 결과: 관리자 프리패스 통과 (OK)")
            return True
            
        # 2. '영업팀' 그룹이 있는지 확인
        if '영업팀' in user_groups:
            print(" -> 결과: 영업팀 소속 확인됨 (OK)")
            return True
            
        print(" -> 결과: 권한 없음 (거부됨) ❌")
        return False

class IsProductionTeam(permissions.BasePermission):
    """ 생산팀 또는 관리자 권한 """
    message = "생산팀 또는 관리자 권한이 필요합니다."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        
        # is_staff, '관리자' 역할, '생산팀' 역할 중 하나라도 해당되면 통과
        if user.is_staff or is_in_role(user, '관리자') or is_in_role(user, '생산팀'):
            return True
            
        return False
