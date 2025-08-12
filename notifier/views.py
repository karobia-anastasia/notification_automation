from django.shortcuts import render
from django.core.paginator import Paginator
from notifier.models import NotifiedDelivery

def dashboard(request):
    deliveries = NotifiedDelivery.objects.all()

    deliveries_context = []
    for d in deliveries:
        deliveries_context.append({
            'order_number': d.order_number,                    # e.g. '5' from OrderNr or SerNr
            'customer_name': d.customer_name or 'Unknown',     # Addr0 stored as customer_name
            'dispatch_date': d.dispatch_date,                  # PlanSendDate or ShipDate stored as date
            'status': getattr(d, 'status', '-'),               # status if saved, else '-'
            'product_spec': getattr(d, 'spec', 'N/A'),         # from rows.row.Spec stored as spec
            'quantity_ordered': getattr(d, 'quantity_ordered', 0),  # from rows.row.Ordered
            'email_sent': d.email_sent,
            'sms_sent': d.sms_sent,
            'notes': d.notes,
        })

    # Paginate deliveries_context list (e.g., 10 per page)
    paginator = Paginator(deliveries_context, 10)
    page_number = request.GET.get('page')
    deliveries_page = paginator.get_page(page_number)

    return render(request, 'dashboard.html', {'deliveries': deliveries_page})
