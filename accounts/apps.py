from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    has_connected = False 

    def ready(self) -> None:
        if not AccountsConfig.has_connected:  # 👈 prevents duplicate signal registration
            from django.db.models.signals import post_save
            from .models import User
            from .signals import post_save_account_receiver

            post_save.connect(post_save_account_receiver, sender=User)
            AccountsConfig.has_connected = True  # mark as connected

        super().ready()
