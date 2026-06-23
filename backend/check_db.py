import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / '.env')

from supabase import create_client

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_SERVICE_ROLE_KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

try:
    resp = supabase.table("matches").select("*").limit(1).execute()
    print("SUCCESS: Matches table exists. Data:", resp.data)
except Exception as e:
    print("ERROR: Matches table query failed:", e)
