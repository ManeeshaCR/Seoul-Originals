from django.apps import AppConfig

class ShopConfig(AppConfig):
    name = 'shop'

    def ready(self):
        import shop.models  # ✅ this loads your signals