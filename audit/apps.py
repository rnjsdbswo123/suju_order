from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    verbose_name = '감사 로그'
    
    def ready(self):
        # 앱 로드 시 signals.py 파일의 리시버들을 등록합니다.
        import audit.signals