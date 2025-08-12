import xmltodict
import requests
from django.core.management.base import BaseCommand
from notifier.models import NotifiedDelivery
from .emails import send_email
from .sms import send_sms
from datetime import datetime
import pprint
from decouple import config

# Load configuration from .env
HANSA_API_URL = config("HANSA_API_URL")
HANSA_GET_CUSTOMER_API_URL = config("HANSA_GET_CUSTOMER_API_URL")
HANSA_USERNAME = config("HANSA_USERNAME")
HANSA_PASSWORD = config("HANSA_PASSWORD")
CONTACT_PHONE = config("CONTACT_PHONE")  # Default phone number from config (can be overwritten)
API_AUTH = config("API_AUTH")  # API authentication credentials

def fetch_all_customers_and_find(order_number):
    """
    Fetches all customers' details from the external customer API and checks for the customer with the matching order number.
    """
    try:
        # Construct the API URL to get all customers
        api_url = f"{HANSA_GET_CUSTOMER_API_URL}"  # Assuming this endpoint fetches all customers
        
        # Send the request to the API using the same authentication pattern as deliveries
        response = requests.get(api_url, auth=(HANSA_USERNAME, HANSA_PASSWORD))
        response.raise_for_status()  # Check for HTTP errors
        
        # Check the status code of the response
        print(f"[INFO] Response status code: {response.status_code}")
        
        # Assuming the API returns a list of customers in JSON format
        customers_data = response.json()

        # Print the entire customers data for debugging
        print(f"[INFO] Customers API Response: {customers_data}")

        # Find the customer that matches the order_number
        for customer in customers_data:
            # Check if the customer order number matches
            if customer.get('OrderNumber') == order_number:
                # Extract customer details (phone, name, email, etc.)
                phone = customer.get('Phone')
                customer_name = customer.get('Name')
                email = customer.get('Email')
                
                # Debugging: Display the found customer details
                print(f"[INFO] Found customer for order {order_number}:")
                print(f"Name: {customer_name}, Email: {email}, Phone: {phone}")
                
                return {
                    'phone': phone,
                    'name': customer_name,
                    'email': email
                }
        
        # If customer with the given order number was not found
        print(f"[INFO] No customer found for order number {order_number}.")
        return None
        
    except requests.HTTPError as e:
        print(f"[ERROR] HTTP error while fetching customers: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error while fetching customers: {e}")
    
    # If anything goes wrong, return None
    return None

# Helper function to get deliveries from Hansa
def get_deliveries():
    print("[INFO] Fetching deliveries from Hansa...")
    try:
        response = requests.get(HANSA_API_URL, auth=(HANSA_USERNAME, HANSA_PASSWORD))
        response.raise_for_status()
        deliveries_xml = xmltodict.parse(response.text)
    except Exception as e:
        print(f"[ERROR] Failed to fetch or parse XML: {e}")
        return []

    data = deliveries_xml.get('data')
    if not data:
        print("[ERROR] No <data> found in response.")
        return []

    shvc_entries = data.get('SHVc')
    if not shvc_entries:
        print("[INFO] No <SHVc> entries found.")
        return []

    if isinstance(shvc_entries, dict):
        shvc_entries = [shvc_entries]

    print(f"[INFO] Found {len(shvc_entries)} delivery entries.")
    pprint.pprint(shvc_entries)

    return shvc_entries

class Command(BaseCommand):
    help = 'Send dispatch email and SMS notifications'

    def handle(self, *args, **options):
        deliveries = get_deliveries()

        if not deliveries:
            print("[INFO] No deliveries to process.")
            return

        for delivery in deliveries:
            order_number = delivery.get('SerNr', 'N/A')
            if NotifiedDelivery.objects.filter(order_number=order_number).exists():
                print(f"[INFO] Order {order_number} already notified. Skipping.")
                continue

            customer_name = delivery.get('Addr0', 'Unknown')
            dispatch_date_str = delivery.get('PlanSendDate')
            dispatch_date = None

            if dispatch_date_str:
                try:
                    dispatch_date = datetime.strptime(dispatch_date_str, '%Y-%m-%d').date()
                except Exception as e:
                    print(f"[WARN] Failed to parse dispatch date '{dispatch_date_str}': {e}")

            email = delivery.get('Addr1')
            
            # Fetch phone number from the second API (Customer API)
            phone = fetch_all_customers_and_find(order_number)

            # Create the message body for both email and SMS
            message = (
                f"Dear {customer_name},\n"
                f"Your order #{order_number} has been dispatched today, {dispatch_date_str}, and is on its way to your location.\n\n"
                f"Should you have any questions, feel free to contact us via {CONTACT_PHONE}.\n"
                f"Thank you for choosing REXE Roofing."
            )
            subject = f"Your Order #{order_number} Has Been Dispatched"

            # Email
            print(f"[EMAIL] Sending to {email}...")
            email_sent = send_email(email, subject, message) if email else False
            if email_sent:
                print(f"[EMAIL SUCCESS] Sent to {email}")
            else:
                print(f"[EMAIL ERROR] Failed to send to {email}")

            # SMS
            sms_sent = False  # Initialize sms_sent to avoid UnboundLocalError
            if phone:
                print(f"[SMS] Sending to {phone}...")
                sms_sent = send_sms(phone, message)
                if sms_sent:
                    print(f"[SMS SUCCESS] Sent to {phone}")
                else:
                    print(f"[SMS ERROR] Failed to send to {phone}")
            else:
                print(f"[SMS WARNING] No phone number found for {order_number}, SMS skipped.")

            # Get row data safely
            rows = delivery.get('rows', {}).get('row')
            if isinstance(rows, list):
                row_data = rows[0]
            elif isinstance(rows, dict):
                row_data = rows
            else:
                row_data = {}

            # Save notification record with full mapped data
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
                quantity_ordered=int(row_data.get('Ordered', '0')),
                unit=row_data.get('UnitCode'),
                price=row_data.get('Price'),
                base_price=row_data.get('BasePrice'),
                cost_account=row_data.get('CostAcc'),
                email=email,
                phone_number=phone,  # Now using phone fetched from the customer API
                email_sent=email_sent,
                sms_sent=sms_sent,  # Now sms_sent will always have a value
                notes=""  # You can add any notes if you have them
            )

            print(f"[INFO] Order {order_number} marked as notified.\n")

