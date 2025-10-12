from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from .utils import (
    generate_student_credentials,
    generate_lecturer_credentials,
    send_new_account_email,
)

@receiver(post_save, sender=User)
def post_save_account_receiver(sender, instance, created, **kwargs):
    """
    Send account email once when a user is created.
    Prevents duplicate sends from nested save() calls.
    """
    if not created:
        return  # only run for new users

    # prevent recursive trigger during save()
    if hasattr(instance, "_skip_signal"):
        return

    if instance.is_student:
        username, password = generate_student_credentials()
        instance.username = username
        instance.set_password(password)
        instance._skip_signal = True  # 👈 block recursion
        instance.save(update_fields=["username", "password"])
        del instance._skip_signal
        send_new_account_email(instance, password)

    elif instance.is_lecturer:
        username, password = generate_lecturer_credentials()
        instance.username = username
        instance.set_password(password)
        instance._skip_signal = True
        instance.save(update_fields=["username", "password"])
        del instance._skip_signal
        send_new_account_email(instance, password)
