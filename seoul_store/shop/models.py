import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models import F
from django.db.models.signals import pre_save


# ---------------- CATEGORY ----------------
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            # while Product.objects.filter(slug=slug).exists():
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

# ---------------- PRODUCT ----------------
class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, null=True)
    description = models.TextField(blank=True)

    # ✅ NEW FIELDS
    how_to_use = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    authenticity = models.TextField(blank=True)
    shipping_info = models.TextField(blank=True)
    return_policy = models.TextField(blank=True)

    retail_price = models.DecimalField(max_digits=10, decimal_places=2)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2)

    image = models.ImageField(upload_to='products/')
    stock = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    is_hot_deal = models.BooleanField(default=False)
    
    def get_price_for_user(self, user):
        if not user.is_authenticated:
            return self.retail_price  # safer default

        profile = getattr(user, 'userprofile', None)

        if not profile:
            return self.retail_price

        if profile.account_type == 'wholesale':
            if profile.approved:
                return self.wholesale_price
            return None  # still allowed, but must be handled everywhere

        return self.retail_price

# ---------------- PRODUCT IMAGE GALLERY ----------------
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/gallery/")

    def __str__(self):
        return self.product.name
    
# ---------------- CART ----------------
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    @property
    def subtotal(self):
        price = self.product.get_price_for_user(self.cart.user)
        if price is None:
            return 0
        return price * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


# ---------------- ORDER ----------------
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('replaced', 'Replaced'),  # ✅ ADDED
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    parent_order = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacements'
    )

    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)

    total = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # ✅ HELPERS
    @property
    def is_replacement(self):
        return self.parent_order is not None

    @property
    def is_original(self):
        return self.parent_order is None

    def can_cancel(self):
        return self.status not in ['shipped', 'delivered', 'replaced']

    def __str__(self):
        return f"Order #{self.id}"


# ---------------- ORDER ITEM ----------------
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items"  # ✅ IMPORTANT
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class ReturnRequest(models.Model):

    REQUEST_TYPE = [
        ('return', 'Return'),
        ('replace', 'Replace'),
    ]

    STATUS_CHOICES = [
        ('pending_pickup', 'Pending Pickup'),
        ('picked', 'Picked'),
        ('processing', 'Processing Replacement'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE)

    reason = models.TextField()
    damage_image = models.ImageField(upload_to='returns/', null=True, blank=True)

    replacement_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    price_difference = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ✅ FIXED (OneToOne)
    replacement_order = models.OneToOneField(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    pickup_tracking_id = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_pickup')

    is_picked = models.BooleanField(default=False)
    is_replacement_sent = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request_type} - Item {self.order_item.id} ({self.status})"


# ---------------- BANNER ----------------
class Banner(models.Model):
    title = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='banners/')
    link = models.CharField(max_length=255, blank=True, default="/")
    active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.title or "Banner"


# ---------------- ADDRESS ----------------
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="UAE")
    is_default = models.BooleanField(default=False)

    # ✅ NEW
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.city}"


# ---------------- USER PROFILE ----------------
class UserProfile(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('wholesale', 'Wholesale'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='individual')

    phone = models.CharField(max_length=20, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True)

    company_name = models.CharField(max_length=255, blank=True)
    business_website = models.URLField(blank=True)
    address = models.TextField(blank=True)

    approved = models.BooleanField(default=False)


# ---------------- SIGNAL: RETURN STOCK ----------------
from django.dispatch import receiver

@receiver(pre_save, sender=ReturnRequest)
def handle_return_stock(sender, instance, **kwargs):

    if instance.request_type != "return":
        return

    if not instance.pk:
        return

    old = ReturnRequest.objects.filter(pk=instance.pk).first()
    if not old:
        return

    if old.status != "completed" and instance.status == "completed":

        Product.objects.filter(
            id=instance.order_item.product.id
        ).update(
            stock=F('stock') + instance.order_item.quantity
        )

        print("✅ STOCK UPDATED")

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)