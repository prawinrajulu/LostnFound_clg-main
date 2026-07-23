import urllib.request
import urllib.error
import json

base_url = "http://127.0.0.1:8010"

print("--- 1. Testing GET / ---")
req = urllib.request.Request(f"{base_url}/")
with urllib.request.urlopen(req) as resp:
    print("Status:", resp.status)
    print("Body:", resp.read().decode())

print("\n--- 2. Testing GET /docs ---")
req = urllib.request.Request(f"{base_url}/docs")
with urllib.request.urlopen(req) as resp:
    print("Status:", resp.status)

print("\n--- 3. Testing GET /api/items/public with CORS origin header ---")
req = urllib.request.Request(
    f"{base_url}/api/items/public",
    headers={"Origin": "https://lostn-found-clg-main.vercel.app"}
)
try:
    with urllib.request.urlopen(req) as resp:
        print("Status:", resp.status)
        print("CORS Allow-Origin:", resp.headers.get("access-control-allow-origin"))
        print("CORS Allow-Credentials:", resp.headers.get("access-control-allow-credentials"))
        body = resp.read().decode()
        print("Body (first 200 chars):", body[:200])
except urllib.error.HTTPError as e:
    print("HTTP Error Status:", e.code)
    print("CORS Allow-Origin:", e.headers.get("access-control-allow-origin"))
    print("Body:", e.read().decode())

print("\n--- 4. Testing OPTIONS preflight request ---")
req = urllib.request.Request(
    f"{base_url}/api/items/public",
    headers={
        "Origin": "https://lostn-found-clg-main.vercel.app",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type"
    },
    method="OPTIONS"
)
try:
    with urllib.request.urlopen(req) as resp:
        print("Preflight Status:", resp.status)
        print("CORS Allow-Origin:", resp.headers.get("access-control-allow-origin"))
        print("CORS Allow-Credentials:", resp.headers.get("access-control-allow-credentials"))
        print("CORS Allow-Methods:", resp.headers.get("access-control-allow-methods"))
except Exception as e:
    print("Preflight error:", e)
