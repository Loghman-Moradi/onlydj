tomato = 'red'
banana = 'yellow'
milk = 'white'
orange = ""

from datetime import timedelta
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404, Http404
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from account.form import AddressForm
from .forms import *
from cart.cart import Cart
from .models import *
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse
import requests
import json
from shop.utils import verify_phone_base, verify_code_base


def verify_phone(request):
    return verify_phone_base(request, PhoneVerificationPhone, 'orders/verify_phone.html', 'orders:verify_code')


def verify_code(request):
    return verify_code_base(request, 'orders:order_create')


@login_required
def order_create(request):
    addresses = Address.objects.filter(user=request.user)
    has_address = addresses.exists()
    cart = Cart(request)
    if request.method == 'POST':
        if 'selected_address' in request.POST:
            selected_address_id = request.POST.get('selected_address')
            selected_address = Address.objects.get(id=selected_address_id)
            order = Order.objects.create(
                buyer=request.user,
            )

            OrderAddress.objects.create(
                order=order,
                address=selected_address,
            )

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity'],
                    weight=item['weight'],
                )
            cart.clear()
            request.session['order_id'] = order.id
            return redirect('orders:request')
        else:
            form = AddressForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                address = Address.objects.create(
                  user=request.user,
                  first_name=cd['first_name'],
                  last_name=cd['last_name'],
                  phone_number=cd['phone_number'],
                  province=cd['province'],
                  city=cd['city'],
                  postal_code=cd['postal_code'],
                  unit=cd['unit'],
                  plate=cd['plate'],
                  address_line=cd['address_line'],
              )
                order = Order.objects.create(
                    buyer=request.user,
                )

                OrderAddress.objects.create(
                    order=order,
                    address=address
                )

                for item in cart:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['quantity'],
                        weight=item['weight'],
                    )

                cart.clear()
                request.session['order_id'] = order.id
                return redirect('orders:request')
    else:
        form = AddressForm()
    context = {
        'form': form,
        'addresses': addresses,
        'has_address': has_address,
        'cart': cart,
    }
    return render(request, 'orders/order_create.html', context)


if settings.SANDBOX:
    sandbox = 'sandbox'
    api = 'sandbox'
else:
    sandbox = 'www'
    api = 'api'

MERCHANT = settings.MERCHANT
ZP_API_REQUEST = f"https://{api}.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = f"https://{api}.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = f"https://{sandbox}.zarinpal.com/pg/StartPay/"

description = 'test',
email = 'email@example.com'
mobile = '09123456789'
CallbackURL = 'http://localhost:8080/payment/verify/'


def send_request(request):
    cart = Cart(request)
    req_data = {
        "merchant_id": MERCHANT,
        "amount": cart.get_post_price(),
        "callback_url": CallbackURL,
        "description": description,
        "metadata": {"mobile": mobile, "email": email}
    }
    req_header = {"accept": "application/json",
                  "content-type": "application/json'"}
    req = requests.post(url=ZP_API_REQUEST, data=json.dumps(
        req_data), headers=req_header)
    authority = req.json()['data']['authority']
    if len(req.json()['errors']) == 0:
        return redirect(ZP_API_STARTPAY + authority)
    else:
        e_code = req.json()['errors']['code']
        e_message = req.json()['errors']['message']
        return HttpResponse(f"Error code: {e_code}, Error Message: {e_message}")


def verify(request):
    cart = Cart(request)
    t_status = request.GET.get('Status')
    t_authority = request.GET['Authority']
    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json",
                      "content-type": "application/json'"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": cart.get_final_price(),
            "authority": t_authority
        }
        req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
        if len(req.json()['errors']) == 0:
            t_status = req.json()['data']['code']
            if t_status == 100:
                return HttpResponse('Transaction success.\nRefID: ' + str(
                    req.json()['data']['ref_id']
                ))
            elif t_status == 101:
                return HttpResponse('Transaction submitted : ' + str(
                    req.json()['data']['message']
                ))
            else:
                return HttpResponse('Transaction failed.\nStatus: ' + str(
                    req.json()['data']['message']
                ))
        else:
            e_code = req.json()['errors']['code']
            e_message = req.json()['errors']['message']
            return HttpResponse(f"Error code: {e_code}, Error Message: {e_message}")
    else:
        return HttpResponse('Transaction failed or canceled by user')


def order_list(request, status=None):
    user = request.user
    if status:
        orders = Order.objects.filter(buyer=user, status=status)
    else:
        orders = Order.objects.filter(buyer=user)

    context = {
        'orders': orders,
        'status': status,
    }
    return render(request, 'orders/order_list.html', context)


def order_detail(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, buyer=request.user)
    except Http404:
        raise Http404()
    order_items = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'order_items': order_items,
    }

    return render(request, 'orders/order_detail.html', context)


def order_invoice(request, order_id):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return HttpResponse("order not found")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice_{}.pdf"'.format(order_id)
    p = canvas.Canvas(response, pagesize=letter)
    p.drawString(100, 750, "order invoice")
    p.drawString(100, 730, f"order number: {order.id}")
    p.drawString(100, 710, f"order date: {order.created_at}")
    p.drawString(100, 690, f"Name of the buyer: {order.buyer}")

    y_pos = 650
    for item in OrderItem.objects.filter(order=order):
        p.drawString(100, y_pos, f"product: {item.product.name}")
        p.drawString(300, y_pos, f"price: {item.price}")
        p.drawString(400, y_pos, f"number: {item.quantity}")
        y_pos -= 20

    p.drawString(100, y_pos - 20, f"total amount: {order.get_total_cost()}")
    p.drawString(100, y_pos - 40, f"----------------------------------")
    p.drawString(100, y_pos - 60, "market: liashopstar")
    p.drawString(100, y_pos - 80, "phone shop: ************")

    p.save()
    return response


@login_required
def return_product(request, item_id):
    order_item = get_object_or_404(OrderItem, id=item_id)
    can_return = False

    if order_item.order.status == "DELIVERED":
        if order_item.order.delivery_date:
            time_difference = timezone.now() - order_item.order.delivery_date
            if time_difference <= timedelta(days=7):
                can_return = True

    if request.method == 'POST':
        form = ReturnedForm(request.POST, request.FILES)
        if form.is_valid():
            returned_product = form.save(commit=False)
            returned_product.order_item = order_item
            returned_product.user = request.user
            returned_product.save()
            messages.success(request, 'Your request has been successfully registered.')
        else:
            messages.error(request, 'Something went wrong. Please try again.')

    else:
        form = ReturnedForm()
    context = {
        'order_item': order_item,
        'form': form,
        'can_return': can_return,
    }

    return render(request, 'orders/return_product.html', context)








