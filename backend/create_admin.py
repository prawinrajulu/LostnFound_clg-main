"""
One-off script: Create or reset the default admin account in Supabase.
Run from the backend directory:  python create_admin.py
"""
import os, uuid
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import bcrypt

load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

USERNAME = "Admin"
PASSWORD = "admin@123"

hashed = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

# Check if user already exists
resp = supabase.table("admins").select("*").eq("username", USERNAME).limit(1).execute()

if resp.data:
    # Update existing record's password
    admin_id = resp.data[0]["id"]
    supabase.table("admins").update({"password": hashed}).eq("id", admin_id).execute()
    print(f"✅ Admin '{USERNAME}' already existed — password reset to '{PASSWORD}'")
else:
    # Insert new record
    new_admin = {
        "id": str(uuid.uuid4()),
        "username": USERNAME,
        "password": hashed,
        "full_name": "Administrator",
        "role": "admin",
    }
    supabase.table("admins").insert(new_admin).execute()
    print(f"✅ Admin '{USERNAME}' created with password '{PASSWORD}'")

print("Done. You can now log in with:")
print(f"  Username : {USERNAME}")
print(f"  Password : {PASSWORD}")
