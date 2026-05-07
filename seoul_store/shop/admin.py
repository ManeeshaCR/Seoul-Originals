import uuid
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Product, Category, Cart, CartItem, Banner,Bannersection2,Bannersection3,
    Order, OrderItem, ReturnRequest, UserProfile,
    Address, ProductImage,Routine,HomePromo

)

# ---------------- CATEGORY ----------------
admin.site.register(Category)

# ---------------- PRODUCT IMAGES INLINE ----------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3

@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ('name', 'tag', 'order', 'active')
    list_editable = ('order', 'active')
    search_fields = ('name', 'tag')

@admin.register(HomePromo)
class HomePromoAdmin(admin.ModelAdmin):
    list_display = ['title', 'tag', 'order', 'active']
    list_editable = ['order', 'active']

# ---------------- PRODUCT ----------------
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'retail_price', 'wholesale_price', 'stock', 'category','tag')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]

    fieldsets = (
        ("Basic Info", {
            "fields": ("name", "slug", "category", "image", 'tag',"description")
        }),
        ("Pricing & Stock", {
            "fields": ("retail_price", "wholesale_price", "stock", "is_hot_deal")
        }),
        ("Product Details Sections", {
            "fields": (
                "how_to_use",
                "ingredients",
                "authenticity",
                "shipping_info",
                "return_policy",
            )
        }),
    )

admin.site.register(Product, ProductAdmin)

# ---------------- CART ----------------
admin.site.register(Cart)
admin.site.register(CartItem)

# ---------------- BANNER ----------------
admin.site.register(Banner)
admin.site.register(Bannersection2)
admin.site.register(Bannersection3)

# ---------------- ORDER ----------------
admin.site.register(Order)
admin.site.register(OrderItem)

# ---------------- ADDRESS ----------------
admin.site.register(Address)

# ---------------- USER PROFILE ----------------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_type', 'approved', 'approve_toggle')
    list_filter = ('account_type', 'approved')
    search_fields = ('user__username', 'company_name')

    def approve_toggle(self, obj):
        if obj.account_type == 'wholesale':
            if obj.approved:
                return format_html(
                    '<a href="/admin/toggle-approval/{}/" style="color:red;">Revoke</a>',
                    obj.id
                )
            else:
                return format_html(
                    '<a href="/admin/toggle-approval/{}/" style="color:green;">Approve</a>',
                    obj.id
                )
        return "-"

    approve_toggle.short_description = "Action"

# ---------------- RETURN REQUEST ----------------
@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('order_item', 'request_type', 'status', 'created_at')
    list_filter = ('status', 'request_type')

    actions = ['approve_request', 'reject_request']

    def approve_request(self, request, queryset):
        for obj in queryset:
            obj.status = 'picked'
            obj.pickup_tracking_id = str(uuid.uuid4())[:10]
            obj.save()

    def reject_request(self, request, queryset):
        queryset.update(status='rejected')