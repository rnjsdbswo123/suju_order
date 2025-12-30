# audit/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from orders.models import OrderHeader, OrderLine
from masters.models import Customer, Product, CustomerProductMap
from .models import AuditLog
from SujuOrderSystem.utils import get_current_user # 현재 사용자 가져오기

def log_change(instance, action):
    """ 감사 로그를 기록하는 헬퍼 함수 """
    user = get_current_user() 
    
    # 시스템 작업일 경우 User가 None일 수 있음
    if not user:
        # 로그인되지 않은 사용자(예: 초기 데이터 업로드)는 system으로 기록
        user_id = None
    else:
        user_id = user.id

    AuditLog.objects.create(
        user_id=user_id,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=instance.pk,
        # details는 필요시 변경 전/후 값 등을 기록할 수 있지만, 여기서는 단순화
    )

@receiver(post_save, sender=OrderHeader)
@receiver(post_save, sender=OrderLine)
@receiver(post_save, sender=Customer)
@receiver(post_save, sender=Product)
@receiver(post_save, sender=CustomerProductMap)
def log_post_save(sender, instance, created, **kwargs):
    """ 생성(CREATE) 및 수정(UPDATE) 로그 기록 """
    action = 'CREATE' if created else 'UPDATE'
    # OrderLine의 완료 수량 변경은 Production View에서 직접 FULFILL로 기록
    if action == 'UPDATE' and sender == OrderLine:
        # 일반 업데이트는 UPDATE로 기록
        log_change(instance, 'UPDATE')
    else:
        log_change(instance, action)


@receiver(post_delete, sender=OrderHeader)
@receiver(post_delete, sender=OrderLine)
@receiver(post_delete, sender=Customer)
@receiver(post_delete, sender=Product)
@receiver(post_delete, sender=CustomerProductMap)
def log_post_delete(sender, instance, **kwargs):
    """ 삭제(DELETE) 로그 기록 """
    log_change(instance, 'DELETE')