from django.urls import path
from . import views

app_name = 'cart'

# project imports
from cart.views import (
    TransactionCreateView,
    TransactionDetailView,
    PaymentParamsView,
)
# app_name = "ecomflutterwave"

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove,
         name='cart_remove'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path("transaction/", TransactionCreateView.as_view(), name="transaction_create"),
    path("payment-params/", PaymentParamsView.as_view(), name="payment_params"),
    path('checkout/square/', views.checkout_square, name='checkout_square'),
    # path("<str:tx_ref>/", TransactionDetailView.as_view(), name="transaction_detail"),
    

]
