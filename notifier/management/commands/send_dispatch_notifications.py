import xmltodict
import requests
from django.core.management.base import BaseCommand
from notifier.models import NotifiedDelivery
from .emails import send_email
from .sms import send_sms
from datetime import datetime
from decouple import config
import traceback

# Load configuration from .env
HANSA_API_URL = config("HANSA_API_URL")
HANSA_GET_CUSTOMER_API_URL = config("HANSA_GET_CUSTOMER_API_URL")
HANSA_USERNAME = config("HANSA_USERNAME")
HANSA_PASSWORD = config("HANSA_PASSWORD")
CONTACT_PHONE = config("CONTACT_PHONE") 


def get_deliveries():
    try:
        response = requests.get(HANSA_API_URL, auth=(HANSA_USERNAME, HANSA_PASSWORD))
        response.raise_for_status()
        deliveries_xml = xmltodict.parse(response.text)
    except Exception as e:
        print(f"Error fetching deliveries: {str(e)}", flush=True)
        return []

    data = deliveries_xml.get('data')
    if not data:
        print("No data found in response.", flush=True)
        return []

    shvc_entries = data.get('SHVc')
    if not shvc_entries:
        print("No SHVc entries found.", flush=True)
        return []

    if isinstance(shvc_entries, dict):
        shvc_entries = [shvc_entries]

    return shvc_entries


def fetch_all_customers():
    try:
        print("Fetching all customers from API...", flush=True)
        api_url = f"{HANSA_GET_CUSTOMER_API_URL}"
        response = requests.get(api_url, auth=(HANSA_USERNAME, HANSA_PASSWORD))

        response.raise_for_status()  

        customers_data = xmltodict.parse(response.text)

        return customers_data.get('data', {}).get('CUVc', [])  

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", flush=True)
    except xmltodict.expat.ExpatError as e:
        print(f"Error parsing XML response: {e}", flush=True)
        print(f"Response content: {response.text}", flush=True) 
    except Exception as e:
        print(f"Error fetching customers: {e}", flush=True)
        print(traceback.format_exc(), flush=True)

    return [] 


def get_customer_phone(customer_email, customers_data):
    for customer in customers_data:
        if str(customer.get('eMail')).strip().lower() == str(customer_email).strip().lower():
            print(f"Found customer with email: {customer_email}", flush=True)
            phone = customer.get('Phone') or customer.get('Mobile') or customer.get('AltPhone')
            return phone
    print(f"No customer found for email: {customer_email}", flush=True)
    return None



class Command(BaseCommand):
    help = 'Send dispatch email and SMS notifications'

    def handle(self, *args, **options):
        customers_data = fetch_all_customers()
        if not customers_data:
            print("No customer data found.", flush=True)
            return

        deliveries = get_deliveries()  
        if not deliveries:
            print("No deliveries found.", flush=True)
            return

        for delivery in deliveries:
            order_number = delivery.get('SerNr', 'N/A')

            if NotifiedDelivery.objects.filter(order_number=order_number).exists():
                email = delivery.get('Addr1')
                phone = None 

                if email:
                    phone = get_customer_phone(email, customers_data)
                
                print(f"Order {order_number} already notified. Email: {email}, Phone: {phone}", flush=True)
                continue  

            customer_name = delivery.get('Addr0', 'Unknown')
            dispatch_date_str = delivery.get('PlanSendDate')
            dispatch_date = None

            if dispatch_date_str:
                try:
                    dispatch_date = datetime.strptime(dispatch_date_str, '%Y-%m-%d').date()
                except Exception:
                    pass

            email = delivery.get('Addr1')

            phone = get_customer_phone(email, customers_data)

            if phone:
                print(f"Phone for {email}: {phone}", flush=True)
            else:
                print(f"No phone found for {email}", flush=True)

            message = (
                f"Dear {customer_name},\n"
                f"Your order #{order_number} has been dispatched today, {dispatch_date_str}, and is on its way to your location.\n\n"
                f"Should you have any questions, feel free to contact us via {CONTACT_PHONE}.\n"
                f"Thank you for choosing REXE Roofing."
            )
            subject = f"Your Order #{order_number} Has Been Dispatched"

            email_sent = False
            sms_sent = False

            if email:
                email_sent = send_email(email, subject, message)
            if phone:
                sms_sent = send_sms(phone, message)

            rows = delivery.get('rows', {}).get('row')
            if isinstance(rows, list):
                row_data = rows[0]
            elif isinstance(rows, dict):
                row_data = rows
            else:
                row_data = {}

            NotifiedDelivery.objects.create(
                order_number=delivery.get('SerNr'),
                customer_name=customer_name,
                dispatch_date=dispatch_date,
                status=delivery.get('Status', '-'),
                location=delivery.get('Location'),
                reg_date=delivery.get('RegDate'),
                reg_time=delivery.get('RegTime'),
                plan_send_date=delivery.get('PlanSendDate'),
                ship_date=delivery.get('ShipDate'),
                service_type=delivery.get('ServiceType'),
                spec=row_data.get('Spec'),
                product_code=row_data.get('ArtCode'),
                quantity_ordered=int(row_data.get('Ordered', '0')) if row_data.get('Ordered') else 0,
                unit=row_data.get('UnitCode'),
                price=row_data.get('Price'),
                base_price=row_data.get('BasePrice'),
                cost_account=row_data.get('CostAcc'),
                email=email,
                phone_number=phone,
                email_sent=email_sent,
                sms_sent=sms_sent,
                notes=""
            )
            print(f"NotifiedDelivery created for order {order_number}", flush=True)
