# 파일 위치: SujuOrderSystem/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # [API 경로]
    path('api/orders/', include('orders.urls')), 
    path('api/masters/', include('masters.urls')),
    path('api/production/', include('production.urls')),
    
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

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)