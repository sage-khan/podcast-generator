import requests
import json
import time
import os

# Configuration
BASE_URL = os.getenv("API_URL", "https://example.com")  # Change to your server URL
USERNAME = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
PASSWORD = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin1234")

# Get authentication token
auth_response = requests.post(
    f"{BASE_URL}/api/token/",
    data={"username": USERNAME, "password": PASSWORD}
)
print(f"Auth response: {auth_response.status_code}")
print(json.dumps(auth_response.json(), indent=2))

# Extract the token (uses 'token' instead of 'access')
token = auth_response.json()["token"]

# Headers for authenticated requests
headers = {
    "Authorization": f"Token {token}",  # Note: using 'Token' prefix instead of 'Bearer'
    "Content-Type": "application/json"
}

# Test Flux Kontext Portrait-Series API
test_data = {
    "input_image": "https://aicc.nyc3.cdn.digitaloceanspaces.com/avatars/austin/images/austin.jpg",
    "background": "neutral",
    "num_images": 3,
    "randomization": True,
    "safety_tolerance": 1,
    "output_format": "png"
    # "webhook_url": "https://your-webhook-endpoint.com/callback"  # Optional
}

# Make the API request
print("\nSending request to Flux Kontext Portrait-Series API...")
response = requests.post(
    f"{BASE_URL}/api/images/generate/flux/kontext/portrait-series/",
    headers=headers,
    json=test_data
)

# Print the response
print(f"Status Code: {response.status_code}")
if response.status_code < 500:
    try:
        print(json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        print(f"Response content (not JSON):\n{response.text}")
else:
    print(response.text)

# If successful, get the job ID and monitor status
if response.status_code == 202:
    job_id = response.json()["id"]
    print(f"\nJob ID: {job_id}")
    
    # Monitor job status
    for i in range(5):  # Check status 5 times
        time.sleep(5)  # Wait 5 seconds between checks
        print(f"\nChecking job status (attempt {i+1})...")
        status_response = requests.get(
            f"{BASE_URL}/api/images/generate/flux/kontext/portrait-series/{job_id}/",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Status: {status_data.get('status')}")
            print(json.dumps(status_data, indent=2))
            
            if status_data.get('status') in ['succeeded', 'failed']:
                print("\nJob processing completed!")
                break
        else:
            print(f"Failed to get status. Code: {status_response.status_code}")
            try:
                print(json.dumps(status_response.json(), indent=2))
            except:
                print(status_response.text)
else:
    print("\nAPI request failed. Cannot monitor job status.")