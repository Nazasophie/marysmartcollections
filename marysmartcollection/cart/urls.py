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

    path("transaction/", TransactionCreateView.as_view(), name="transaction_create"),
    path("payment-params/", PaymentParamsView.as_view(), name="payment_params"),
    path("<str:tx_ref>/", TransactionDetailView.as_view(), name="transaction_detail"),
    

]
