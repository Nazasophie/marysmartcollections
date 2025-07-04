from django.shortcuts import render, redirect, get_object_or_404
from Ecommerce.models import Category, Product
from .cart import Cart
from .forms import CartAddProductForm
from django.contrib.auth.models import User
from django.http import JsonResponse




# stdlib imports

# django imports
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.views.generic import TemplateView

# 3rd party imports
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import CartAddProductForm

# project imports
from marysmartcollection import settings
from cart.models import FlwTransactionModel, FlwPlanModel
from cart.serializers import DRTransactionSerializer
from cart.utils import create_transaction_ref


# yourapp/views.py

from django.contrib.auth.decorators import login_required


@login_required
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = CartAddProductForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            cart.add(product=product, quantity=cd['quantity'], override_quantity=cd['override'])
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Product added to cart'})
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return redirect('cart:cart_detail')

@login_required
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Product removed from cart'})
    return redirect('cart:cart_detail')

@login_required
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = CartAddProductForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            cart.add(product=product, quantity=cd['quantity'], override_quantity=True)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Cart updated'})
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return redirect('cart:cart_detail')

@login_required
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Cart cleared'})
    return redirect('cart:cart_detail')

def cart_detail(request, category_slug=None):
    cart = Cart(request)
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    context = {
        'cart': cart,
        'category': category,
        'categories': categories,
        'products': products,
        'cart_form': CartAddProductForm()
    }
    return render(request, 'cart/cart.html', context)

UserModel = get_user_model()


class TransactionDetailView(LoginRequiredMixin, TemplateView):
    """Returns a transaction template"""

    template_name = "djangoflutterwave/transaction.html"

    def get_context_data(self, **kwargs):
        """Add transaction to context data"""
        kwargs = super().get_context_data(**kwargs)
        try:
            kwargs["transaction"] = FlwTransactionModel.objects.get(
                user=self.request.user, tx_ref=self.kwargs["tx_ref"]
            )
        except FlwTransactionModel.DoesNotExist:
            kwargs["transaction"] = None
        return kwargs


class TransactionCreateView(CreateAPIView):
    """Api end point to create transactions. This is used as a webhook called by
    Flutterwave."""

    queryset = FlwTransactionModel.objects.all()
    serializer_class = DRTransactionSerializer
    authentication_classes: list = []

    def create(self, request, *args, **kwargs):
        """Override create to specify request.data['data'] for serializer data"""
        serializer = self.get_serializer(data=request.data.get("data", None))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer: DRTransactionSerializer) -> None:
        """Add plan and user to Transaction instance, determined from the received
        reference"""
        reference = serializer.validated_data["tx_ref"]
        plan_id = reference.split("__")[0]
        user_id = reference.split("__")[2]
        serializer.save(
            user=UserModel.objects.get(id=user_id),
            plan=FlwPlanModel.objects.get(id=plan_id),
        )


class PaymentParamsView(APIView):
    """Api view for retrieving params required when submiting a payment request to
    Flutterwave. End point can be used by SPA's instead of using template payment
    button."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Return params based on provided plan name"""
        try:
            plan = FlwPlanModel.objects.get(name=request.GET.get("plan", None))
        except FlwPlanModel.DoesNotExist:
            return Response("Plan does not exist", status=status.HTTP_404_NOT_FOUND)

        data = {
            "public_key": settings.FLW_PUBLIC_KEY,
            "tx_ref": create_transaction_ref(plan_pk=plan.pk, user_pk=request.user.pk),
            "amount": plan.amount,
            "currency": plan.currency,
            "payment_plan": plan.flw_plan_id,
            "customer": {
                "email": request.user.email,
                "name": f"{request.user.first_name} {request.user.last_name}",
            },
            "customizations": {"title": plan.modal_title, "logo": plan.modal_logo_url},
        }
        return Response(data)