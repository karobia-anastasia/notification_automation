import requests
import time
from decouple import config, Csv

# SMS
SMS_OAUTH_URL = config("SMS_OAUTH_URL")
SMS_SEND_URL = config("SMS_SEND_URL")
SMS_API_KEY = config("SMS_API_KEY")
SMS_SENDER_ID = config("SMS_SENDER_ID")

cached_sms_token = None
token_expiry = 0

def get_sms_access_token():
    global cached_sms_token, token_expiry

    if cached_sms_token and time.time() < token_expiry:
        print("[SMS] Access token (cached) still valid.")
        return cached_sms_token

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {SMS_API_KEY}'
    }
    body = {}

    try:
        print("[SMS] Requesting new access token...")
        response = requests.post(SMS_OAUTH_URL, json=body, headers=headers)
        print(f"[SMS] Token response: {response.status_code} - {response.text}")
        response.raise_for_status()

        data = response.json()
        token = data.get('access_token')
        expires_in = data.get('expires_in', 3600)

        if not token:
            print("[SMS ERROR] No access_token in response.")
            return None

        cached_sms_token = token
        token_expiry = time.time() + expires_in - 60
        print(f"[SMS] New token acquired. Expires in {expires_in} seconds.")
        return token

    except requests.HTTPError as e:
        print(f"[SMS ERROR] HTTP error while getting token: {e}")
        if e.response:
            print(f"[SMS ERROR] Token error response: {e.response.text}")
        return None
    except Exception as e:
        print(f"[SMS ERROR] Unexpected error getting token: {e}")
        return None

def send_sms(phone_number, message):
    print(f"[SMS] Preparing to send SMS to {phone_number}")
    token = get_sms_access_token()

    if not token:
        print("[SMS WARNING] SMS not sent. No valid token.")
        return False

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    payload = {
        "from": SMS_SENDER_ID,
        "to": phone_number,
        "message": message
    }

    try:
        print(f"[SMS] Sending SMS: {payload}")
        response = requests.post(SMS_SEND_URL, json=payload, headers=headers)
        print(f"[SMS] Send response: {response.status_code} - {response.text}")
        response.raise_for_status()

        print(f"[SMS SUCCESS] SMS successfully sent to {phone_number}")
        return True

    except requests.HTTPError as e:
        print(f"[SMS ERROR] HTTP error sending SMS: {e}")
        if e.response:
            print(f"[SMS ERROR] Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"[SMS ERROR] Unexpected error: {e}")
        return False
