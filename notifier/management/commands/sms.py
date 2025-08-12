import requests
import time
from decouple import config
import uuid
from datetime import datetime

SMS_OAUTH_URL = config("SMS_OAUTH_URL")  
SMS_SEND_URL = config("SMS_SEND_URL")    
SMS_API_KEY = config("SMS_API_KEY")      
CLIENT_KEY = config("CLIENT_KEY")       
SMS_SENDER_ID = config("SMS_SENDER_ID") 

cached_sms_token = None
token_expiry = 0

def get_sms_access_token():
    """
    Fetches a new access token from the SMS API.
    
    Returns:
        str: The access token, or None if an error occurs.
    """
    global cached_sms_token, token_expiry

    if cached_sms_token and time.time() < token_expiry:
        print("[SMS] Access token (cached) still valid.")
        return cached_sms_token

    headers = {
        'Content-Type': 'application/json',
    }

    body = {
        "Username": SMS_API_KEY, 
        "Password": CLIENT_KEY,    
    }

    try:
        print("[SMS] Requesting new access token...")
        response = requests.post(SMS_OAUTH_URL, json=body, headers=headers)

        # Log the response for debugging
        print(f"[SMS] Token response: {response.status_code} - {response.text}")
        response.raise_for_status()

        # Parse the response JSON
        data = response.json()
        token = data.get('accessToken')
        expires_in = data.get('expiresIn', 3599)

        if not token:
            print("[SMS ERROR] No access_token in response.")
            return None

        # Cache the token and set the expiry
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

def send_sms(phone, message, schedule_time=None):
    if not phone:
        print("[SMS ERROR] No phone number provided. SMS not sent.")
        return False
    
    print(f"[SMS] Preparing to send SMS to {phone}...")

    # Get the access token
    token = get_sms_access_token()

    if not token:
        print("[SMS WARNING] SMS not sent. No valid token.")
        return False

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}' 
    }

    message_id = str(uuid.uuid4())

    if not schedule_time:
        schedule_time = datetime.now().strftime("%d/%m/%Y %H:%M")

    payload = {
        "senderId": SMS_SENDER_ID,
        "message": message,
        "phoneNumber": phone, 
        "messageId": message_id,  
        "scheduleTime": schedule_time,  
        "sendOption": "NOW",  
        "description": "Message description",
        "callBackUrl": "https://url.com/" 
    }

    try:
        print(f"[SMS] Sending SMS: {payload}")
        response = requests.post(SMS_SEND_URL, json=payload, headers=headers)
        print(f"[SMS] Send response: {response.status_code} - {response.text}")
        response.raise_for_status()

        if response.status_code == 200:
            print(f"[SMS SUCCESS] SMS successfully sent to {phone}")
            return True
        else:
            print(f"[SMS ERROR] Failed to send SMS to {phone}. Response: {response.text}")
            return False

    except requests.HTTPError as e:
        print(f"[SMS ERROR] HTTP error sending SMS: {e}")
        if e.response:
            print(f"[SMS ERROR] Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"[SMS ERROR] Unexpected error: {e}")
        return False


