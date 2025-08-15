import traceback
import xmltodict
import requests
from datetime import datetime
from decouple import config
from notifier.models import NotifiedDelivery
from .emails import send_email
from .sms import send_sms

# Load configuration
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

        # DEBUG: print top-level keys to verify structure
        print(f"Deliveries XML root keys: {list(deliveries_xml.keys())}", flush=True)

    except Exception as e:
        print(f"Error fetching deliveries: {e}", flush=True)
        return []

    data = deliveries_xml.get('data')
    if not data:
        print(f"No 'data' key found in deliveries response. Available keys: {list(deliveries_xml.keys())}", flush=True)
        return []

    print(f"'data' keys: {list(data.keys())}", flush=True)

    shvc_entries = data.get('SHVc')
    if not shvc_entries:
        print(f"No 'SHVc' entries found in deliveries data. Available keys: {list(data.keys())}", flush=True)
        return []

    if isinstance(shvc_entries, dict):
        shvc_entries = [shvc_entries]

    print(f"Found {len(shvc_entries)} deliveries", flush=True)
    return shvc_entries


def fetch_all_customers():
    try:
        response = requests.get(HANSA_GET_CUSTOMER_API_URL, auth=(HANSA_USERNAME, HANSA_PASSWORD))
        response.raise_for_status()
        customers_data = xmltodict.parse(response.text)
        return customers_data.get('data', {}).get('CUVc', [])
    except Exception:
        print("Error fetching customers:\n", traceback.format_exc(), flush=True)
        return []

def get_customer_phone(customer_email, customers_data):
    for customer in customers_data:
        if str(customer.get('eMail', '')).strip().lower() == str(customer_email).strip().lower():
            phone = customer.get('Phone') or customer.get('Mobile') or customer.get('AltPhone')
            print(f"Phone found for {customer_email}: {phone}", flush=True)
            return phone
    print(f"No customer phone found for email: {customer_email}", flush=True)
    return None

def run_dispatch_notification_job():
    customers_data = fetch_all_customers()
    if not customers_data:
        print("No customer data found.", flush=True)
        return

    deliveries = get_deliveries()
    if not deliveries:
        print("No deliveries found.", flush=True)
        return

    print(f"Processing {len(deliveries)} deliveries", flush=True)

    for delivery in deliveries:
        try:
            order_number = delivery.get('SerNr', 'N/A')
            if NotifiedDelivery.objects.filter(order_number=order_number).exists():
                print(f"Order {order_number} already notified, skipping.", flush=True)
                continue

            customer_name = delivery.get('Addr0', 'Unknown')
            dispatch_date_str = delivery.get('PlanSendDate')
            dispatch_date = None
            if dispatch_date_str:
                try:
                    dispatch_date = datetime.strptime(dispatch_date_str, '%Y-%m-%d').date()
                except Exception:
                    print(f"Failed to parse dispatch date {dispatch_date_str} for order {order_number}", flush=True)

            email = delivery.get('Addr1')
            phone = get_customer_phone(email, customers_data) if email else None

            message = (
                f"Your order #{order_number} has been dispatched and will arrive today. "
                f"We will notify you right away if there are any delays."
            )
            subject = f"Your Order #{order_number} Has Been Dispatched"

            email_sent = send_email(email, subject, message) if email else False
            sms_sent = send_sms(phone, message) if phone else False

            rows = delivery.get('rows', {}).get('row')
            if isinstance(rows, list):
                row_data = rows[0] if rows else {}
            elif isinstance(rows, dict):
                row_data = rows
            else:
                row_data = {}

            NotifiedDelivery.objects.create(
                order_number=order_number,
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
                cost_account=delivery.get('CostAcc'),
                email=email,
                phone_number=phone,
                email_sent=email_sent,
                sms_sent=sms_sent,
                notes=""
            )
            print(f"NotifiedDelivery created for order {order_number}", flush=True)
        except Exception as e:
            print(f"Error processing delivery {delivery.get('SerNr', 'N/A')}: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
