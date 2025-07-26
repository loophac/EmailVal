import requests
import random
import string
import time

API_URL = "https://da180767-a1ef-48fa-ba97-7ceef227560b-00-37l153y9puy9.picard.replit.dev/validate"  # Change if deployed
API_KEY = "35830d297dc79fcdacfbc2247587ff61"  # Replace with your test key
REQUESTS_PER_MIN = 600  # Try exceeding your tier's limit
SPAM_DURATION_SEC = 120  # How long to run the test


def random_email():
    user = ''.join(random.choices(string.ascii_lowercase, k=7))
    domain = random.choice(["example.com", "test.com", "mail.org"])
    return f"{user}@{domain}"


def spam():
    start = time.time()
    count = 0
    while time.time() - start < SPAM_DURATION_SEC:
        email = random_email()
        headers = {"x-api-key": API_KEY}
        params = {"email": email}

        response = requests.get(API_URL, headers=headers, params=params)
        print(f"{count + 1}. {email} - {response.status_code}")

        try:
            print("   →", response.json())
        except Exception:
            print("   → Non-JSON response")

        count += 1
        time.sleep(60 / REQUESTS_PER_MIN)  # Spread evenly across a minute


if __name__ == "__main__":
    spam()
