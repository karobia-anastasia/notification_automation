import xmltodict
import requests
from django.core.management.base import BaseCommand
from notifier.models import NotifiedDelivery
from .emails import send_email
from .sms import send_sms
from datetime import datetime
import pprint
from decouple import config, Csv

HANSA_API_URL = config("HANSA_API_URL")
HANSA_USERNAME = config("HANSA_USERNAME")
HANSA_PASSWORD = config("HANSA_PASSWORD")
CONTACT_PHONE = config("CONTACT_PHONE")

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

            email = delivery.get('AddrEmail') or 'karobiaanastasia@gmail.com'
            phone = delivery.get('Phone') or delivery.get('Mobile') or None

            message = (
                f"Dear {customer_name},\n"
                f"Your order #{order_number} has been dispatched today, {dispatch_date_str}, and is on its way to your location.\n\n"
                f"Should you have any questions, feel free to contact us via {CONTACT_PHONE}.\n"
                f"Thank you for choosing REXE Roofing."
            )
            subject = f"Your Order #{order_number} Has Been Dispatched"

            # Email
            print(f"[EMAIL] Sending to {email}...")
            email_sent = send_email(email, subject, message)
            if email_sent:
                print(f"[EMAIL SUCCESS] Sent to {email}")
            else:
                print(f"[EMAIL ERROR] Failed to send to {email}")

            # SMS
            sms_phone = phone if phone else CONTACT_PHONE
            sms_sent = False
            if sms_phone:
                print(f"[SMS] Sending to {sms_phone}...")
                sms_sent = send_sms(sms_phone, message)
                if sms_sent:
                    print(f"[SMS SUCCESS] Sent to {sms_phone}")
                else:
                    print(f"[SMS ERROR] Failed to send to {sms_phone}")
            else:
                print(f"[SMS WARNING] No phone number, SMS skipped.")

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
                phone_number=sms_phone,
                email_sent=email_sent,
                sms_sent=sms_sent,
                notes=""  # You can add any notes if you have them
            )

            print(f"[INFO] Order {order_number} marked as notified.\n")
