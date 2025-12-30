# 파일 위치: SujuOrderSystem/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # [API 경로] include를 사용해 각 앱의 urls.py로 보냅니다.
    path('api/orders/', include('orders.urls')), 
    path('api/production/', include('production.urls')),
    path('api/masters/', include('masters.urls')),
    path('users/', include('users.urls')),
    # path('api/audit/', include('audit.urls')),

    # [화면 경로]
    path('orders/', include('orders.urls')),

    # [로그인/로그아웃]
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # [첫 화면]
    path('', RedirectView.as_view(url='/orders/new/', permanent=True)),
    # ★ [추가] 장고가 제공하는 로그인/로그아웃 기능 활성화
    path('accounts/', include('django.contrib.auth.urls')),

    # ★ [추가] 텅 빈 주소('')로 들어오면 -> 로그인 페이지로 강제 이동
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    path('masters/', include('masters.urls')), 

]