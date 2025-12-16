import requests

url = "http://localhost:5000/activity"  # Update port if needed
headers = {"Accept": "application/json"}

try:
    response = requests.get(url, headers=headers)
    data = response.json()
    print(data)  # Print the data to see it
except Exception as e:
    print(f"Error: {e}")