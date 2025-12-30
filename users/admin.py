from django.contrib import admin
from .models import User, Role, UserRole

# User 모델 등록 (기본 Django UserAdmin 사용)
from django.contrib.auth.admin import UserAdmin
admin.site.register(User, UserAdmin)

# Role과 UserRole 등록
admin.site.register(Role)
admin.site.register(UserRole)