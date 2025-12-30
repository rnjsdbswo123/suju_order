from django.urls import path
from .views import role_based_login_redirect_view

app_name = 'users'

urlpatterns = [
    path('redirect-on-login/', role_based_login_redirect_view, name='login-redirect'),
]
