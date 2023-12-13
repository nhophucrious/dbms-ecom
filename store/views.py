from orders.models import OrderProduct
from django.contrib import messages
from store.forms import ReviewForm
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.db.models import Q

from store.models import Product, ReviewRating
from carts.models import Cart, CartItem
from category.models import Category
from carts.views import _cart_id


def store(request, category_slug=None):
    if category_slug is not None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.all().filter(category=categories, is_available=True)
    else:
        products = Product.objects.all().filter(is_available=True).order_by('id')

    sizes = {variation.variation_value for product in products for variation in product.variation_set.filter(variation_category='size')}
    colors = {variation.variation_value for product in products for variation in product.variation_set.filter(variation_category='color')}

    if 'sizes' in request.GET:
        selected_sizes = request.GET.getlist('sizes')
        products = products.filter(variation__variation_category='size', variation__variation_value__in=selected_sizes)

    if 'colors' in request.GET:
        selected_colors = request.GET.getlist('colors')
        products = products.filter(variation__variation_category='color', variation__variation_value__in=selected_colors)

    page = request.GET.get('page')
    page = page or 1
    paginator = Paginator(products, 3)
    paged_products = paginator.get_page(page)
    product_count = products.count()

    context = {
        'products': paged_products,
        'product_count': product_count,
        'sizes': sizes,
        'colors': colors,
    }
    return render(request, 'store/store.html', context=context)


def product_detail(request, category_slug, product_slug=None):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        cart = Cart.objects.get(cart_id=_cart_id(request=request))
        in_cart = CartItem.objects.filter(
            cart=cart,
            product=single_product
        ).exists()
    except Exception as e:
        cart = Cart.objects.create(
            cart_id=_cart_id(request)
        )

    try:
        orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
    except Exception:
        orderproduct = None

    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)

    context = {
        'single_product': single_product,
        'in_cart': in_cart if 'in_cart' in locals() else False,
        'orderproduct': orderproduct,
        'reviews': reviews,
    }
    return render(request, 'store/product_detail.html', context=context)


def search(request):
    q = '' # init q
    products = Product.objects.all()

    if 'q' in request.GET:
        q = request.GET.get('q')
        products = products.filter(Q(product_name__icontains=q) | Q(description__icontains=q))

    if 'sizes' in request.GET:
        sizes = request.GET.getlist('sizes')
        products = products.filter(variation__variation_category='size', variation__variation_value__in=sizes)

    if 'colors' in request.GET:
        colors = request.GET.getlist('colors')
        products = products.filter(variation__variation_category='color', variation__variation_value__in=colors)

    if 'min_price' in request.GET and request.GET.get('min_price').isdigit():
        min_price = request.GET.get('min_price')
        products = products.filter(price__gte=min_price)

    if 'max_price' in request.GET and request.GET.get('max_price').isdigit():
        max_price = request.GET.get('max_price')
        products = products.filter(price__lte=max_price)

    products = products.order_by('-created_date')
    product_count = products.count()

    context = {
        'products': products,
        'q': q,
        'product_count': product_count
    }

    return render(request, 'store/store.html', context)


def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == "POST":
        try:
            review = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=review)
            form.save()
            messages.success(request, "Thank you! Your review has been updated.")
            return redirect(url)
        except Exception:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data['subject']
                data.rating = form.cleaned_data['rating']
                data.review = form.cleaned_data['review']
                data.ip = request.META.get('REMOTE_ADDR')
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, "Thank you! Your review has been submitted.")
                return redirect(url)
