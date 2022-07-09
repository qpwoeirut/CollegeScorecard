import requests


with open(".env") as f:
    API_KEY = f.read().strip()

ENDPOINT = f"https://api.data.gov/ed/collegescorecard/v1/schools?api_key={API_KEY}"

resp = requests.get(ENDPOINT)
print(resp.json())
