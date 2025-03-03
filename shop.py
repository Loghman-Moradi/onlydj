def login():
    return False


def logout():
    return True


def register():
    username = ""
    password_1 = ""
    password_2 = ""
    code = ""


def Change_password():
    return True


def test():
    des = 'te1224'
    return des


def like_post():
    return test()


class Profile():
    def __init__(self, name):
        return self.name


def edit(user):
    return user


# this is a test in github
phone = "123456789"
name = "via"
age = 18
city = "L.A"


def login():
    return False


def logout():
    return True


def register():
    username = ""
    password_1 = ""
    password_2 = ""
    code = ""


def Change_password():
    return True


def test():
    des = 'te1224'
    return des


def like_post():
    return test()


class Profile():
    def __init__(self, name):
        return self.name


def edit(user):
    return user


# this is a test in github
phone = "123456789"
name = "via"
age = 18
city = "L.A"




from itertools import product

from django.shortcuts import render, redirect
from account.models import ShopUser
from account.admin import ShopUserAdmin
from cart.cart import Cart
from .models import OrderItem
from .forms import PhoneVerificationForm, OrderCreateForm
from django.contrib import messages
import random


# Create your views here.

def verify_phone(request):
    if request.user.is_authenticated:
        return redirect('orders:order_create')
    if request.method == "POST":
        form = PhoneVerificationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data.get('phone_number')
            tokens = {'token': ''.join(random.choices("123456789", k=6))}
            request.session['verification_code'] = tokens['token']
            request.session['phone'] = phone
            print(tokens)
            messages.success(request, 'Your verification code has been sent')
            return redirect('orders:verify_code')
    else:
        form = PhoneVerificationForm()
    return render(request, 'verify/verify_phone.html', {'form': form})


def verify_code(request):
    if request.method == "POST":
        code = request.POST['code']
        verification_code = request.session['verification_code']
        phone = request.session['phone']
        if code == verification_code:
            user = ShopUser.objects.create_user(phone=phone)
            user.set_password("123456")
            user.save()
            print(user)
            return redirect('orders:create_order')

        else:
            messages.error(request,'Your verification code does not match.')
    return render(request, 'verify/verify_code.html')


def create_order(request):
    cart = Cart(request)
    if request.method == "POST":
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity'],
                    weight=item['weight'],
                )
            cart.clear()
            return redirect('store:products_list')
    else:
        form = OrderCreateForm()
    return render(request, 'forms/create_order.html', {'form': form})



from django.db import models
from account.models import ShopUser
from store.models import Product


# Create your models here.

class Order(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    phone = models.CharField(max_length=11)
    address = models.TextField()
    postal_code = models.CharField(max_length=10)
    province = models.CharField(max_length=20)
    city = models.CharField(max_length=20)
    paid = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['-created'])
        ]

    def get_post_cost(self):
        return sum(item.post_cost() for item in self.items.all)

    def get_total_cost(self):
        total_weight =  sum(item.total_cost() for item in self.items.all)

        if total_weight == 0:
            return 0
        elif total_weight < 1000:
            return 20000
        elif 1000 < total_weight < 2000:
            return 30000
        else:
            return 50000

    def get_final_cost(self):
        final_price = self.get_total_cost() * self.get_post_cost()
        return final_price

    def __str__(self):
        return f"Order: {self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="order_items")
    weight = models.PositiveIntegerField(default=0)
    price = models.PositiveIntegerField(default=0)
    quantity = models.PositiveIntegerField(default=1)

    def post_cost(self):
        return self.weight * self.quantity

    def total_cost(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.id}"

from django.shortcuts import render, get_object_or_404
from .models import *
# Create your views here.


def products_list(request, category_slug=None, sort_slug=None):
    category = None
    products = Product.objects.all()
    categories = Category.objects.all()

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    if sort_slug:
        if sort_slug == "price_asc":
            products = Product.objects.all().order_by('-new_price')
        elif sort_slug == "price_desc":
            products = Product.objects.all().order_by('new_price')
        elif sort_slug == 'new':
            products = Product.objects.all().order_by('-created')
        elif sort_slug == "biggest_discount":
            products = Product.objects.all().order_by('-offers')


    context = {
        'products': products,
        'category': category,
        'categories': categories,

    }

    return render(request, 'shop/product_list.html', context)


def products_detail(request, product_id, slug):
    product = get_object_or_404(Product, id=product_id, slug=slug)
    related_products = Product.objects.exclude(id=product.id).filter(name__icontains=product.name.split(' ')[0])[:3]

    context = {
        'product': product,
        'related_products': related_products,
    }

    return render(request, 'shop/detail.html', context)








