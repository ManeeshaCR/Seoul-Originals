from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),

    path('signup/', views.signup_choice, name='signup_choice'),
    path('signup/individual/', views.signup_individual, name='signup_individual'),
    path('signup/wholesale/', views.signup_wholesale, name='signup_wholesale'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html',redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    path('cart/', views.cart_view, name='cart'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('category/<int:id>/', views.category_view, name='category'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/<int:order_id>/', views.success, name='success'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('orders/', views.orders, name='orders'),
    path('account/', views.account, name='account'),
    path('address/add/', views.add_address, name='add_address'),
    path('address/set-default/<int:id>/', views.set_default_address, name='set_default_address'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('address/edit/<int:id>/', views.edit_address, name='edit_address'),
    path('address/delete/<int:id>/', views.delete_address, name='delete_address'),
    path('delete-address/<int:id>/', views.delete_address, name='delete_address'),
    path('restore-address/<int:id>/', views.restore_address, name='restore_address'),   
    path('order/<int:id>/', views.order_detail, name='order_detail'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('return/<int:item_id>/', views.create_return_request, name='create_return_request'),
    path('confirm-replacement/<int:return_id>/', views.confirm_replacement, name='confirm_replacement'),
    path('return/complete/<int:return_id>/', views.complete_return, name='complete_return'),
    path('ajax/products/', views.ajax_products, name='ajax_products'),
]