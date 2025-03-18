import requests
import json

data = {
    "token": "test_token",
    "challenge": "test_challenge_value",
    "type": "url_verification"
}

url = "https://asia-northeast1-my-kotonaru-project.cloudfunctions.net/new_collector/slack/events"
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=data, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")