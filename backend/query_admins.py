import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

resp = supabase.table("admins").select("*").execute()
print("Admins:")
for row in resp.data:
    print(f"ID: {row['id']}, Username: {row['username']}, Role: {row['role']}")
