import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from .models import Address, Category, Product, Cart, CartItem, Banner,Bannersection2,Bannersection3, Order, OrderItem,UserProfile,Routine,HomePromo
from django.views.decorators.http import require_POST
from decimal import Decimal
from django.contrib.auth.models import User
from datetime import timedelta
from .models import ReturnRequest
from django.utils import timezone
from .services import process_replacement, process_return
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import Coalesce
import uuid
from django.core.paginator import Paginator


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)

    product.display_price = product.get_price_for_user(request.user)

    # ✅ related products (same category)
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:10]

    for p in related_products:
        p.display_price = p.get_price_for_user(request.user)

    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products
    })

def tag_products(request, tag):
    products = Product.objects.filter(tag__iexact=tag)

    for p in products:
        p.display_price = p.get_price_for_user(request.user)

    return render(request, "category.html", {
        "products": products,
        "category": {"name": tag.capitalize()}
    })

def home(request):
    banners = Banner.objects.filter(active=True).order_by('order')
    bannerssection2 = Bannersection2.objects.filter(active=True).order_by('order')
    bannerssection3 = Bannersection3.objects.filter(active=True).order_by('order')

    products = Product.objects.select_related('category').all()

    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    min_price = request.GET.get('min')
    max_price = request.GET.get('max')

    if min_price:
        products = products.filter(retail_price__gte=min_price)

    if max_price:
        products = products.filter(retail_price__lte=max_price)

    for p in products:
        p.display_price = p.get_price_for_user(request.user)

    routine_items = Routine.objects.filter(active=True).order_by('order')
    promos = HomePromo.objects.filter(active=True).order_by('order')[:2]

    # ✅ ACCESSORIES PRODUCTS
    accessories_products = Product.objects.filter(
        category__slug='accessories'
    )[:8]

    for p in accessories_products:
        p.display_price = p.get_price_for_user(request.user)

    return render(request, 'home.html', {
        'banners': banners,
        'bannerssection2': bannerssection2,
        'bannerssection3': bannerssection3,
        'products': products,
        'routine_items': routine_items,
        'promos': promos,
        'accessories_products': accessories_products,
    })

def price_filter(request):
    min_price = request.GET.get('min')
    max_price = request.GET.get('max')

    products = Product.objects.all()

    if min_price and max_price:
        products = products.filter(
            retail_price__gte=min_price,
            retail_price__lte=max_price
        )
    elif min_price:  # for 1000+
        products = products.filter(retail_price__gte=min_price)

    # ✅ apply pricing logic (IMPORTANT)
    for p in products:
        p.display_price = p.get_price_for_user(request.user)

    return render(request, 'price_filter.html', {
        'products': products,
        'min': min_price,
        'max': max_price
    })

def ajax_products(request):
    tab = request.GET.get('tab', 'new')

    products = Product.objects.select_related('category')

    # 🔥 SAME LOGIC AS HOME (consistent UI)
    if tab == 'new':
        products = products.order_by('-id')

    elif tab == 'sold':
        products = products.annotate(
            total_sold=Coalesce(Sum('order_items__quantity'), 0)
        ).order_by('-total_sold', '-id')

    elif tab == 'deal':
        products = products.filter(is_hot_deal=True).order_by('-id')

    else:
        products = products.order_by('-id')

    products = products[:12]

    for p in products:
        p.display_price = p.get_price_for_user(request.user)

    html = render_to_string(
    "partials/product_grid.html",
    {
        "products": products,
        "user": request.user
    },
    request=request   # ✅ MUST BE HERE
    )
    return JsonResponse({"html": html})

def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)

    products_list = Product.objects.filter(category=category)

    # ✅ GET TAG FROM URL
    selected_tag = request.GET.get('tag')

    if selected_tag:
        products_list = products_list.filter(tag__iexact=selected_tag)

    # ✅ GET UNIQUE TAGS FOR FILTER UI
    tags = Product.objects.filter(
        category=category
    ).exclude(
        tag=""
    ).values_list(
        'tag', flat=True
    ).distinct()

    # ✅ pagination
    paginator = Paginator(products_list, 12)

    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    # ✅ pricing
    for p in products:
        p.display_price = p.get_price_for_user(request.user)

    return render(request, 'category.html', {
        'category': category,
        'products': products,
        'tags': tags,
        'selected_tag': selected_tag,
    })

def all_categories_products(request):

    products_list = Product.objects.select_related('category').all()

    # ✅ pagination
    paginator = Paginator(products_list, 12)

    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    for p in products:
        p.display_price = p.get_price_for_user(request.user)

    return render(request, 'category.html', {
        'category': {'name': 'All Products'},
        'products': products,
    })

def signup(request):
    form = UserCreationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('/')
    return render(request, 'signup.html', {'form': form})

def signup_choice(request):
    return render(request, 'signup_choice.html')



def signup_individual(request):
    if request.user.is_authenticated:
        return redirect('/')  # ✅ prevent logged-in users

    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            # ✅ ensure profile exists
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.account_type = 'individual'
            profile.save()

            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('/')

        # else:
        #     messages.error(request, "Please fix the errors below.")

    else:
        form = UserCreationForm()

    return render(request, 'signup_individual.html', {'form': form})

def signup_wholesale(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")

        company = request.POST.get("company_name")
        website = request.POST.get("business_website")
        address = request.POST.get("address")
        phone = request.POST.get("phone")

        if not all([username, password, email, company]):
            messages.error(request, "Please fill all required fields")
            return redirect('signup_wholesale')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('signup_wholesale')

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.account_type = 'wholesale'
        profile.company_name = company
        profile.business_website = website
        profile.address = address
        profile.phone = phone
        profile.approved = False  # 🔒 requires admin approval
        profile.save()

        messages.success(request, "Wholesale account created. Await approval.")
        return redirect('login')

    return render(request, 'signup_wholesale.html')
# ---------------- CART ----------------
@login_required
@require_POST
def add_to_cart(request, product_id):

    qty = int(request.POST.get("quantity", 1))  # ✅ NEW

    replacement_id = request.session.get('replacement_id')

    if replacement_id:
        return_req = ReturnRequest.objects.filter(
            id=replacement_id,
            order_item__order__user=request.user
        ).first()

        if not return_req or return_req.status == "completed":
            request.session.pop('replacement_id', None)
            replacement_id = None

    # ================= REPLACEMENT FLOW =================
    if replacement_id:
        product = get_object_or_404(Product, id=product_id)

        if product.id == return_req.order_item.product.id:
            messages.error(request, "Please choose a different product for replacement.")
            return redirect('home')

        return_req.replacement_product = product
        return_req.save()

        return redirect('confirm_replacement', return_id=return_req.id)

    # ================= NORMAL CART =================
    with transaction.atomic():
        product = Product.objects.select_for_update().get(id=product_id)
        cart = get_cart(request.user)

        if product.stock <= 0:
            messages.error(request, "Out of stock")
            return redirect('home')

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if created:
            item.quantity = min(qty, product.stock)
        else:
            new_qty = item.quantity + qty
            if new_qty > product.stock:
                messages.error(request, "No more stock available")
                return redirect('cart')
            item.quantity = new_qty

        item.save()

    messages.success(request, f"{product.name} added to cart")
    return redirect('cart')

@login_required
def confirm_replacement(request, return_id):
    return_req = get_object_or_404(
        ReturnRequest,
        id=return_id,
        order_item__order__user=request.user
    )

    # 🚨 1. ONLY after delivery
    if return_req.order_item.order.status != "delivered":
        messages.error(request, "Replacement not allowed at this stage.")
        return redirect('orders')

    # 🚨 2. PRODUCT must be selected
    if not return_req.replacement_product:
        messages.error(request, "No replacement product selected.")
        return redirect('orders')

    # ✅ ALWAYS CALCULATE PRICE
    price_old = return_req.order_item.price
    price_new = return_req.replacement_product.get_price_for_user(request.user)

    extra_amount = None
    if price_new > price_old:
        extra_amount = price_new - price_old

    # 🚨 3. BLOCK BEFORE PICKUP
    if not return_req.is_picked:
        messages.warning(request, "Replacement will be processed after pickup.")
        return redirect('orders')

    # 🚨 4. prevent double processing
    if return_req.status in ["completed"]:
        messages.info(request, "Replacement already processed.")
        return redirect('orders')

    if request.method == "POST":
        action = request.POST.get("action")

        # ❌ BLOCK CONFIRM IF EXTRA PAYMENT NEEDED
        if action == "confirm" and extra_amount:
            messages.error(request, f"Extra payment required: AED {extra_amount}")
            return redirect('orders')

        if action == "confirm":
            success, message = process_replacement(return_req)

            if not success:
                messages.error(request, message)
                return redirect('orders')

            request.session.pop('replacement_id', None)

            messages.success(request, "Replacement created successfully")
            return redirect('orders')

        elif action == "cancel":
            request.session.pop('replacement_id', None)
            messages.info(request, "Replacement cancelled")
            return redirect('orders')

    return render(request, "confirm_replacement.html", {
        "return_req": return_req,
        "extra_amount": extra_amount   # ✅ ALWAYS PASS
    })

@login_required
def cart_view(request):
    cart = get_cart(request.user)
    items = CartItem.objects.select_related('product').filter(cart=cart)

    # ✅ FIX: sync cart with stock
    for item in items:
        if item.quantity > item.product.stock:
            item.quantity = item.product.stock
            item.save()

   
    total = sum((item.subtotal for item in items), Decimal('0.00'))

    return render(request, 'cart.html', {
        'items': items,
        'total': total,
    })



@login_required
@require_POST
def update_cart(request, item_id, action):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product = item.product

    if action == "inc":
        if item.quantity < product.stock:
            item.quantity += 1
            item.save()
        else:
            messages.error(request, "Stock limit reached")

    elif action == "dec":
        if item.quantity > 1:
            item.quantity -= 1
            item.save()

    return redirect('cart')

@login_required
@require_POST
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, f"{item.product.name} removed from cart.")
    return redirect('cart')

# ---------------- CHECKOUT ----------------
@login_required
def checkout(request):

    # 🔒 BLOCK UNAPPROVED WHOLESALE USERS
    profile = getattr(request.user, 'userprofile', None)
    if profile and profile.account_type == 'wholesale' and not profile.approved:
        messages.error(request, "Your wholesale account is pending approval.")
        return redirect('/')

    cart = get_cart(request.user)
    items = CartItem.objects.select_related('product').filter(cart=cart)

    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    addresses = Address.objects.filter(user=request.user)

    # ✅ INITIAL TOTAL (for GET request)
    total = Decimal('0.00')
    for item in items:
        price = item.product.get_price_for_user(request.user)
        if price:
            total += price * item.quantity

    if request.method == "POST":
        address_id = request.POST.get("address")

        if not address_id:
            messages.error(request, "Please select an address.")
            return redirect('checkout')

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, "Invalid address selected.")
            return redirect('checkout')

        with transaction.atomic():

            # 🔒 LOCK CART ITEMS
            items = CartItem.objects.select_for_update().select_related('product').filter(cart=cart)

            if not items.exists():
                messages.error(request, "Cart is empty.")
                return redirect('cart')

            total = Decimal('0.00')

            # 🔒 VALIDATE STOCK + CALCULATE TOTAL
            for item in items:
                product = Product.objects.select_for_update().get(id=item.product.id)

                if product.stock <= 0:
                    messages.error(request, f"{product.name} is out of stock.")
                    return redirect('cart')

                if item.quantity > product.stock:
                    messages.error(request, f"Only {product.stock} left for {product.name}.")
                    return redirect('cart')

                # ✅ FIXED PRICE LOGIC
                price = product.get_price_for_user(request.user)

                if price is None:
                    messages.error(request, "You are not allowed to purchase this product.")
                    return redirect('cart')

                total += price * item.quantity

            # ✅ CREATE ORDER
            order = Order.objects.create(
                user=request.user,
                name=address.full_name,
                address=f"{address.address_line}, {address.city}, {address.country}",
                phone=address.phone,
                total=total,
                status='pending',
                created_at=timezone.now()
            )

            # ✅ CREATE ORDER ITEMS + REDUCE STOCK
            for item in items:
                product = item.product
                price = product.get_price_for_user(request.user)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=price
                )

                updated = Product.objects.filter(
                    id=product.id,
                    stock__gte=item.quantity
                ).update(stock=F('stock') - item.quantity)

                if not updated:
                    messages.error(request, f"Stock update failed for {product.name}")
                    raise Exception("Stock race condition")

            # ✅ CLEAR CART
            items.delete()

        messages.success(request, "Order placed successfully!")
        return redirect('success', order_id=order.id)

    return render(request, 'checkout.html', {
        'items': items,
        'total': total,
        'addresses': addresses
    })

@login_required
def orders(request):
    orders = Order.objects.filter(
        user=request.user,
        parent_order__isnull=True
    ).prefetch_related(
        'items__product',
        'items__returnrequest_set',  # ✅ IMPORTANT
        'replacements__items__product'
    ).order_by('-created_at')

    # ✅ attach latest return request manually
    for order in orders:
        for item in order.items.all():
            item.latest_request = item.returnrequest_set.order_by('-created_at').first()

    replacement_orders = Order.objects.filter(
        user=request.user,
        parent_order__isnull=False
    )

    return render(request, 'orders.html', {
        'orders': orders,
        'replacement_orders': replacement_orders
    })

@login_required
def success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "success.html", {"order": order})

@login_required
def account(request):
    # profile = request.user.userprofile
    profile = getattr(request.user, 'userprofile', None)
    # addresses = Address.objects.filter(user=request.user)
    addresses = Address.objects.filter( user=request.user, is_deleted=False)
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'account.html', {
        'profile': profile,
        'addresses': addresses,
        'orders': orders
    })


@login_required
def add_address(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        address_line = request.POST.get("address_line")
        city = request.POST.get("city")

        if not all([full_name, phone, address_line, city]):
            messages.error(request, "All fields required")
            return redirect('account')

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            address_line=address_line,
            city=city
        )

        messages.success(request, "Address added")
        return redirect('account')
    return redirect('account')


@login_required
def set_default_address(request, id):
    Address.objects.filter(user=request.user).update(is_default=False)
    address = get_object_or_404(Address, id=id, user=request.user)
    address.is_default = True
    address.save()

    messages.success(request, "Default address updated")
    return redirect('account')

@login_required
def edit_profile(request):
    # profile = request.user.userprofile
    profile = getattr(request.user, 'userprofile', None)

    if request.method == "POST":
        phone = request.POST.get("phone")
        age = request.POST.get("age")
        gender = request.POST.get("gender")

        if age:
            try:
                age = int(age)
                if age < 0 or age > 120:
                    messages.error(request, "Invalid age")
                    return redirect('edit_profile')
            except:
                messages.error(request, "Age must be a number")
                return redirect('edit_profile')

        profile.phone = phone
        profile.age = age
        profile.gender = gender
        profile.save()

        messages.success(request, "Profile updated")
        return redirect('account')

    return render(request, 'edit_profile.html', {'profile': profile})

@login_required
def edit_address(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)

    if request.method == "POST":
        address.full_name = request.POST.get("full_name")
        address.phone = request.POST.get("phone")
        address.address_line = request.POST.get("address_line")
        address.city = request.POST.get("city")

        if not all([address.full_name, address.phone, address.address_line, address.city]):
            messages.error(request, "All fields required")
            return redirect('edit_address', id=id)

        address.save()
        messages.success(request, "Address updated")
        return redirect('account')

    return render(request, 'edit_address.html', {'address': address})


@login_required
@require_POST
def delete_address(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)

    # ❌ prevent deleting last active address
    active_addresses = Address.objects.filter(
        user=request.user,
        is_deleted=False
    ).count()

    if active_addresses <= 1:
        return JsonResponse({
            "success": False,
            "message": "You must keep at least one address."
        })

    # ✅ soft delete
    address.is_deleted = True
    address.is_default = False
    address.save()

    # ✅ assign another default
    other = Address.objects.filter(
        user=request.user,
        is_deleted=False
    ).first()

    if other:
        other.is_default = True
        other.save()

    return JsonResponse({
        "success": True,
        "message": "Address deleted",
        "address_id": address.id
    })

@login_required
@require_POST
def restore_address(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)

    address.is_deleted = False
    address.save()

    return JsonResponse({
        "success": True,
        "message": "Address restored"
    })
@login_required
def order_detail(request, id):
    order = get_object_or_404(Order, id=id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})


@login_required
def create_return_request(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = item.order

    # ✅ Only delivered orders
    # ✅ ONLY allow after delivery
    if order.status != "delivered":
        messages.error(request, "You can only return/replace after delivery.")
        return redirect("orders")

    # ✅ 10-day window
    if timezone.now() > order.created_at + timedelta(days=10):
        messages.error(request, "Return window expired (10 days).")
        return redirect("orders")

    # ✅ BLOCK duplicate requests
    existing_request = ReturnRequest.objects.filter(order_item=item).order_by('-created_at').first()

    if existing_request:
        if existing_request.status == "completed":
            messages.error(request, "Already returned/replaced.")
            return redirect("orders")

        elif existing_request.status in ["pending_pickup", "picked", "processing"]:
            messages.error(request, "Request already in progress.")
            return redirect("orders")

        elif existing_request.status == "rejected":
            pass  # ✅ allow retry
            # ✅ allow retry if rejected

    if request.method == "POST":
        reason = request.POST.get("reason")
        request_type = request.POST.get("type")
        image = request.FILES.get("image")

        return_req = ReturnRequest.objects.create(
            order_item=item,
            request_type=request_type,
            reason=reason,
            damage_image=image,
            pickup_tracking_id=str(uuid.uuid4())[:10],
            status="pending_pickup"
        )

        if request_type == "replace":
            request.session['replacement_id'] = return_req.id
            return redirect('home')

        return redirect("orders")

    products = Product.objects.all()

    return render(request, "return.html", {
        "item": item,
        "products": products
    })

@login_required
def mark_as_picked(request, return_id):
    return_req = get_object_or_404(
        ReturnRequest,
        id=return_id,
        order_item__order__user=request.user
    )

    if return_req.is_picked:
        messages.warning(request, "Already picked.")
        return redirect('orders')

    return_req.is_picked = True
    return_req.status = "picked"
    return_req.save()

    if return_req.request_type == "return":
        process_return(return_req)

    messages.success(request, "Item marked as picked.")
    return redirect('orders')

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if not order.can_cancel():
        messages.error(request, "Cannot cancel this order")
        return redirect('orders')

    with transaction.atomic():
        for item in order.items.select_related('product'):
            Product.objects.filter(id=item.product.id).update(
                stock=F('stock') + item.quantity
            )

        order.status = 'cancelled'
        order.save()

    messages.success(request, "Order cancelled successfully")
    return redirect('orders')


@login_required
def complete_return(request, return_id):
    return_req = get_object_or_404(
        ReturnRequest,
        id=return_id,
        order_item__order__user=request.user
    )

    success, message = process_return(return_req)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('orders')