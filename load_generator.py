import requests
import time

URL = "http://127.0.0.1:5050/"

print("🚀 Sending continuous requests to Flask app...")

while True:
    try:
        response = requests.get(URL)
        print(f"Response: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(0.2)  # adjust to send ~5 requests/second
