import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config, Csv

# Load configuration from .env
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
FROM_EMAIL = config("FROM_EMAIL")
CC_EMAILS = config("CC_EMAILS", cast=Csv())

def send_email(to_email, subject, body):
 
    msg = MIMEMultipart()
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    
    if CC_EMAILS:
        msg['Cc'] = ', '.join(CC_EMAILS)
    
    msg.attach(MIMEText(body, 'plain'))
    
    recipients = [to_email] + CC_EMAILS

    try:
        if EMAIL_PORT == 465:
            server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)
        else:
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            if EMAIL_USE_TLS:
                server.starttls()

        # Login to the server
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)

        # Send the email
        server.sendmail(FROM_EMAIL, recipients, msg.as_string())
        
        # Close the server connection
        server.quit()

        print(f"[Email INFO] Successfully sent to {to_email}")
        return True

    except smtplib.SMTPException as e:
        print(f"[Email ERROR] SMTP error: {e}")
    except Exception as e:
        print(f"[Email ERROR] Failed to send email to {to_email}: {e}")
    finally:
        try:
            server.quit()
        except Exception:
            pass

    return False


