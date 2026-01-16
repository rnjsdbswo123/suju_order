# 파일 위치: SujuOrderSystem/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),

    # API
    path('api/production/', include('production.api_urls')),
    
    # [화면 경로]
    path('orders/', include('orders.urls')),
    path('production/', include('production.urls')),
    path('masters/', include('masters.urls')), 
    path('users/', include('users.urls')),

    # [로그인/로그아웃]
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # [첫 화면]
    path('', RedirectView.as_view(url='/orders/new/', permanent=True)),
    path('accounts/', include('django.contrib.auth.urls')),
]

# 미디어 파일 서빙을 위한 URL 패턴 추가
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]