#!/usr/bin/env python3
"""
EMERGENCY ADMIN PASSWORD RESET TOOL
Use this to reset super admin password when login fails.
Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env
"""

import sys
import os
from pathlib import Path

# Load environment from backend/.env
ROOT_DIR = Path(__file__).parent
env_file = ROOT_DIR / "backend" / ".env"

if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)
else:
    print(f"Warning: {env_file} not found. Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.")

try:
    from supabase import create_client
except ImportError:
    print("supabase package not found. Run: pip install supabase")
    sys.exit(1)

try:
    import bcrypt
except ImportError:
    print("bcrypt package not found. Run: pip install bcrypt")
    sys.exit(1)

import uuid
from datetime import datetime, timezone


def emergency_reset():
    print("=" * 70)
    print("EMERGENCY SUPER ADMIN PASSWORD RESET")
    print("=" * 70)

    # Get credentials from environment
    supabase_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        print("\nERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        print("Please fill in backend/.env and try again.")
        sys.exit(1)

    supabase = create_client(supabase_url, service_role_key)

    # Get new password from user
    print("\nEnter new password for superadmin:")
    print("(or press Enter to use default: admin123)")
    new_password = input("> ").strip()

    if not new_password:
        new_password = "admin123"

    print(f"\nUsing password: {new_password}")

    # Hash the password
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    # Check if superadmin exists
    resp = supabase.table("admins").select("*").eq("username", "superadmin").limit(1).execute()
    existing = resp.data[0] if resp.data else None

    if existing:
        print("\n✓ Found existing superadmin")
        print(f"  ID: {existing.get('id')}")

        supabase.table("admins").update({"password": password_hash}).eq("username", "superadmin").execute()
        print("\n✓ Password updated successfully!")
    else:
        print("\n⚠ No superadmin found. Creating new one...")

        superadmin = {
            "id": str(uuid.uuid4()),
            "username": "superadmin",
            "password": password_hash,
            "full_name": "Super Administrator",
            "role": "super_admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        supabase.table("admins").insert(superadmin).execute()
        print("✓ New superadmin created!")

    # Verify
    print("\n" + "=" * 70)
    print("VERIFICATION TEST")
    print("=" * 70)

    resp2 = supabase.table("admins").select("*").eq("username", "superadmin").limit(1).execute()
    admin = resp2.data[0] if resp2.data else None

    if admin and bcrypt.checkpw(new_password.encode(), admin["password"].encode()):
        print("✓ Password verification: SUCCESS")
        print("\n" + "=" * 70)
        print("LOGIN CREDENTIALS")
        print("=" * 70)
        print(f"Username: superadmin")
        print(f"Password: {new_password}")
        print("=" * 70)
    else:
        print("✗ Password verification: FAILED")
        print("Something went wrong!")


if __name__ == "__main__":
    emergency_reset()
