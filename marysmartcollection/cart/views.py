from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from Ecommerce.models import Category, Product
from .cart import Cart
from .forms import CartAddProductForm
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import DRTransactionSerializer
from .models import FlwTransactionModel, FlwPlanModel
from .utils import create_transaction_ref
from marysmartcollection import settings

UserModel = get_user_model()

@require_POST
@login_required
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    print(f"POST data: {request.POST}")  # Debug: Log form data
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        print(f"Cleaned data: {cd}")  # Debug: Log cleaned data
        size = cd.get('size')  # Safely get size to avoid KeyError
        if not size:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': {'size': ['Please select a size.']}}, status=400)
            return render(request, 'single-product.html', {
                'product': product,
                'cart_product_form': form,
                'error': 'Please select a size.',
                'category': product.category,
                'categories': Category.objects.all()
            })
        cart.add(
            product=product,
            quantity=cd['quantity'],
            size=size,
            override_quantity=cd['update']  # Match Cart class parameter
        )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Product added to cart',
                'total_quantity': cart.__len__()
            })
        return redirect('cart:cart_detail')
    print(f"Form errors: {form.errors}")  # Debug: Log form errors
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return render(request, 'single-product.html', {
        'product': product,
        'cart_product_form': form,
        'error': form.errors.as_text(),
        'category': product.category,
        'categories': Category.objects.all()
    })

@require_POST
@login_required
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Product removed from cart'})
    return redirect('cart:cart_detail')

@require_POST
@login_required
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    print(f"POST data: {request.POST}")  # Debug
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        print(f"Cleaned data: {cd}")  # Debug
        size = cd.get('size')  # Include size for consistency
        cart.add(
            product=product,
            quantity=cd['quantity'],
            size=size,
            override_quantity=True
        )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Cart updated',
                'total_quantity': cart.__len__()
            })
        return redirect('cart:cart_detail')
    print(f"Form errors: {form.errors}")  # Debug
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return render(request, 'single-product.html', {
        'product': product,
        'cart_product_form': form,
        'error': form.errors.as_text(),
        'category': product.category,
        'categories': Category.objects.all()
    })

@require_POST
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

class TransactionDetailView(LoginRequiredMixin ):
    """Returns a transaction template"""
    template_name = "djangoflutterwave/transaction.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        try:
            kwargs["transaction"] = FlwTransactionModel.objects.get(
                user=self.request.user, tx_ref=self.kwargs["tx_ref"]
            )
        except FlwTransactionModel.DoesNotExist:
            kwargs["transaction"] = None
        return kwargs

class TransactionCreateView(CreateAPIView):
    """Api end point to create transactions. This is used as a webhook called by Flutterwave."""
    queryset = FlwTransactionModel.objects.all()
    serializer_class = DRTransactionSerializer
    authentication_classes: list = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data.get("data", None))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer: DRTransactionSerializer) -> None:
        reference = serializer.validated_data["tx_ref"]
        plan_id = reference.split("__")[0]
        user_id = reference.split("__")[2]
        serializer.save(
            user=UserModel.objects.get(id=user_id),
            plan=FlwPlanModel.objects.get(id=plan_id),
        )

class PaymentParamsView(APIView):
    """Api view for retrieving params required when submitting a payment request to Flutterwave."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
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