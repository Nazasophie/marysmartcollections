from django.shortcuts import render

def home(request):
    return render(request, 'index.html', )

def about(request):
    return render(request, 'about.html', )
def blog(request):
    return render(request, 'blog.html', )
def contact(request):
    return render(request, 'contact.html', )
def login(request):
    return render(request, 'login.html', )
def shoping_cart(request):
    return render(request, 'shoping-cart.html', )
def coming_soon(request):
    return render(request, 'coming-soon.html', )
def collection_full(request):
    return render(request, 'collection-full.html', )
def single_product(request):
    return render(request, 'single-product.html', )