from django.db import transaction
from django.db.models import F
from .models import Product,Order, OrderItem

from django.db import transaction
from django.db.models import F

def process_replacement(return_req):
    old_item = return_req.order_item
    user = old_item.order.user
    new_product = return_req.replacement_product

    if not new_product:
        return False, "No replacement product selected"

    if return_req.is_completed:
        return False, "Replacement already completed"

    if old_item.order.status != "delivered":
        return False, "Replacement only allowed after delivery"

    if not return_req.is_picked:
        return False, "Item not picked yet"

    if new_product.id == old_item.product.id:
        return False, "Cannot replace with same product"

    with transaction.atomic():

        # 🔒 Lock both products
        old_product = Product.objects.select_for_update().get(id=old_item.product.id)
        new_product = Product.objects.select_for_update().get(id=new_product.id)

        if new_product.stock < old_item.quantity:
            return False, "Not enough stock"

        # 💰 Price calculation
        price_old = old_item.price
        price_new = new_product.get_price_for_user(user)

        if price_new is None:
            return False, "You are not allowed to purchase this product"
        
        old_total = price_old * old_item.quantity
        new_total = price_new * old_item.quantity

        if new_total > old_total:
            return False, f"Additional payment required: {new_total - old_total}"

        # ✅ 1. RESTORE OLD PRODUCT STOCK
        Product.objects.filter(id=old_product.id).update(
            stock=F('stock') + old_item.quantity
        )

        # ✅ 2. REDUCE NEW PRODUCT STOCK
        Product.objects.filter(
            id=new_product.id,
            stock__gte=old_item.quantity
        ).update(
            stock=F('stock') - old_item.quantity
        )

        # ✅ 3. CREATE REPLACEMENT ORDER
        replacement_order = Order.objects.create(
            user=user,
            name=old_item.order.name,
            address=old_item.order.address,
            phone=old_item.order.phone,
            total=new_total,
            status='processing',
            parent_order=old_item.order
        )

        # ✅ 4. CREATE NEW ORDER ITEM
        OrderItem.objects.create(
            order=replacement_order,
            product=new_product,
            quantity=old_item.quantity,
            price=price_new
        )

        # ✅ 5. UPDATE RETURN REQUEST
        return_req.replacement_order = replacement_order
        return_req.status = "completed"
        return_req.is_completed = True
        return_req.is_replacement_sent = True
        return_req.save()

        # ✅ 6. UPDATE PARENT ORDER STATUS
        parent = old_item.order
        all_items = parent.items.all()

        all_replaced = all(
            item.returnrequest_set.filter(
                status="completed",
                request_type="replace"
            ).exists()
            for item in all_items
        )

        if all_replaced:
            parent.status = "replaced"
            parent.save()

    return True, "Replacement created successfully"

def process_return(return_req):

    if return_req.request_type != "return":
        return False, "Not a return request"

    if return_req.is_completed:
        return False, "Already completed"

    if not return_req.is_picked:
        return False, "Item must be picked first"

    with transaction.atomic():

        item = return_req.order_item

        # ✅ Restore stock
        Product.objects.filter(
            id=item.product.id
        ).update(
            stock=F('stock') + item.quantity
        )

        # ❌ DO NOT MODIFY QUANTITY
        # item.quantity = 0  ← REMOVE THIS

        return_req.status = "completed"
        return_req.is_completed = True
        return_req.save()

    return True, "Return completed"