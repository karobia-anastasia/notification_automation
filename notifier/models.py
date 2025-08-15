from django.db import models

class NotifiedDelivery(models.Model):
    order_number = models.CharField(max_length=50)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    dispatch_date = models.DateField(blank=True, null=True)
    plan_send_date = models.DateField(blank=True, null=True)
    ship_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    service_type = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    reg_date = models.DateField(blank=True, null=True)
    reg_time = models.TimeField(blank=True, null=True)
    spec = models.CharField(max_length=255, blank=True, null=True)
    product_code = models.CharField(max_length=50, blank=True, null=True)
    quantity_ordered = models.IntegerField(default=0)
    unit = models.CharField(max_length=20, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    base_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    cost_account = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)


    def __str__(self):
        return f"Order {self.order_number} - {self.customer_name}"
