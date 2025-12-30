from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. 커스텀 User 모델: Django 기본 User 모델을 확장합니다.
class User(AbstractUser):
    # AbstractUser가 username, password, email 등을 제공합니다.
    # 지금은 추가 필드 없이 사용합니다.
    pass

# 2. Role 모델: 사용자 역할을 정의합니다. (예: 발주자, 생산부, 관리자)
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="역할명")
    
    def __str__(self):
        return self.name

# 3. UserRole 모델: 사용자와 역할(Role)을 연결합니다.
class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('user', 'role') # 한 사용자에게 같은 역할이 중복되지 않도록 설정
        verbose_name = "사용자-역할 매핑"
        
    def __str__(self):
        return f"{self.user.username} - {self.role.name}"