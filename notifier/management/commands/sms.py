import requests
import base64
import time
import uuid
from datetime import datetime
from decouple import config

# Load configuration from .env
SMS_OAUTH_URL = config("SMS_OAUTH_URL")  # URL for token generation (using GET)
SMS_SEND_URL = config("SMS_SEND_URL")    # URL for sending SMS
Username = config("SMS_API_KEY")         # API key
Password = config("CLIENT_KEY")          # Client key
SMS_SENDER_ID = config("SMS_SENDER_ID")  # Sender ID for SMS

cached_sms_token = None
token_expiry = 0

def get_sms_access_token():
    """
    Fetches a new access token from the SMS API using Basic Authentication.
    
    Returns:
        str: The access token, or None if an error occurs.
    """
    global cached_sms_token, token_expiry

    if cached_sms_token and time.time() < token_expiry:
        print("[SMS] Access token (cached) still valid.")
        return cached_sms_token

    credentials = f"{Username}:{Password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json',
    }

    try:
        print("[SMS] Requesting new access token via GET...")
        response = requests.get(SMS_OAUTH_URL, headers=headers)  # Changed to GET request for token

        print(f"[SMS] Token response: {response.status_code} - {response.text}")
        response.raise_for_status()

        data = response.json()
        token = data.get('accessToken')
        expires_in = data.get('expiresIn', 3599)

        if not token:
            print("[SMS ERROR] No access_token in response.")
            return None

        cached_sms_token = token
        token_expiry = time.time() + int(expires_in) - 60  
        print(f"[SMS] New token acquired. Expires in {expires_in} seconds.")
        return token

    except requests.exceptions.RequestException as e:
        print(f"[SMS ERROR] HTTP error while getting token: {e}")
        if e.response:
            print(f"[SMS ERROR] Token error response: {e.response.text}")
        return None
    except Exception as e:
        print(f"[SMS ERROR] Unexpected error getting token: {e}")
        return None


def send_sms(phone_number, message, schedule_time=None):
    """
    Sends an SMS using the obtained access token.
    
    Args:
        phone_number (str): The phone number to send the SMS to.
        message (str): The message content.
        schedule_time (str, optional): The time at which to send the SMS (in ISO 8601 format).
        
    Returns:
        bool: True if SMS was sent successfully, False otherwise.
    """
    token = get_sms_access_token()
    if not token:
        print("[SMS ERROR] Unable to send SMS: No valid token.")
        return False

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    message_id = str(uuid.uuid4()) 

    if not phone_number.startswith("+"):
        phone_number = "254" + phone_number.lstrip("0")  

    if not schedule_time:
        schedule_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S') 

    payload = {
        "senderId": SMS_SENDER_ID,
        "message": message,
        "phoneNumber": phone_number, 
        "messageId": message_id,  
        "sendOption": "NOW" ,  
        "description": "Dispatch Notification", 
        "callBackUrl": "https://your-callback-url.com/",  
        "scheduleTime": schedule_time,  
    }

    try:
        print(f"[SMS] Sending message to {phone_number}: {message} at {schedule_time}")
        response = requests.post(SMS_SEND_URL, json=payload, headers=headers)
        print(f"[SMS] Send response: {response.status_code} - {response.text}")
        response.raise_for_status()

        # Check the response status code and return True if successful
        if response.status_code == 200:
            print(f"[SMS SUCCESS] SMS successfully sent to {phone_number}")
            return True
        else:
            print(f"[SMS ERROR] Failed to send SMS to {phone_number}. Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[SMS ERROR] HTTP error sending SMS: {e}")
        if e.response:
            print(f"[SMS ERROR] Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"[SMS ERROR] Unexpected error: {e}")
        return False

