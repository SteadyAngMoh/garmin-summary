import os
import requests
from dotenv import load_dotenv

ENV_FILE = os.path.expanduser("~/.garmin_env")

load_dotenv(ENV_FILE)

api_key = os.environ["RESEND_API_KEY"]
email_to = os.environ["EMAIL_TO"]

response = requests.post(
    "https://api.resend.com/emails",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    json={
        "from": "Garmin Report <glucose@precisionbiomodeling.com>",
        "to": [email_to],
        "subject": "Garmin Pixel Test",
        "text": (
            "Hello from the Pixel 2!\n\n"
            "Garmin collector email delivery is working."
        ),
    },
    timeout=30,
)

print("HTTP status:", response.status_code)
print("Response:", response.text)

response.raise_for_status()

print("Email sent successfully.")
