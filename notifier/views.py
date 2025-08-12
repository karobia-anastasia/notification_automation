from django.shortcuts import render
from django.core.paginator import Paginator
from notifier.models import NotifiedDelivery

def dashboard(request):
    deliveries = NotifiedDelivery.objects.all()

    deliveries_context = []
    for d in deliveries:
        deliveries_context.append({
            'order_number': d.order_number,                   
            'customer_name': d.customer_name or 'Unknown',    
            'dispatch_date': d.dispatch_date,                 
            'status': getattr(d, 'status', '-'),               
            'product_spec': getattr(d, 'spec', 'N/A'),        
            'quantity_ordered': getattr(d, 'quantity_ordered', 0), 
            'email_sent': d.email_sent,
            'sms_sent': d.sms_sent,
            'notes': d.notes,
        })

    paginator = Paginator(deliveries_context, 10)
    page_number = request.GET.get('page')
    deliveries_page = paginator.get_page(page_number)

    return render(request, 'dashboard.html', {'deliveries': deliveries_page})
