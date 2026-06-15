# Supabase Setup Guide — Campus Lost & Found

## 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up / log in.
2. Click **New project**.
3. Choose your organisation, give it a name (e.g. `lostnfound`), set a strong database password, pick a region close to you.
4. Click **Create new project** and wait ~1–2 minutes for it to provision.

---

## 2. Run the SQL Schema

1. In your Supabase dashboard, go to **SQL Editor** (left sidebar).
2. Click **New query**.
3. Open `backend/schema.sql` from this project and paste the entire contents into the editor.
4. Click **Run** (or press `Ctrl+Enter`).

You should see a success message. This creates the six tables (`admins`, `students`, `items`, `claims`, `messages`, `audit_logs`) along with indexes and Row Level Security policies.

---

## 3. Collect Your Credentials

Go to **Project Settings → API** and copy:

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | "Project URL" |
| `SUPABASE_ANON_KEY` | "anon public" key under "Project API keys" |
| `SUPABASE_SERVICE_ROLE_KEY` | "service_role" key (keep this secret!) |

---

## 4. Fill In `backend/.env`

Open `backend/.env` and set the three Supabase values:

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...

JWT_SECRET=campus_lost_found_secret_key_change_this

CORS_ORIGINS=http://localhost:3000

# Optional — for AI matching feature
EMERGENT_LLM_KEY=
OPENAI_API_KEY=
```

> ⚠️ **Never commit `SUPABASE_SERVICE_ROLE_KEY` to Git.** It is already in `.gitignore` via `*.env`.

---

## 5. Install Python Dependencies

```bash
cd backend

# Activate your virtual environment first
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```

---

## 6. Start the Backend

```bash
# From the backend/ directory with venv active
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

On first startup the application automatically creates a **superadmin** account:

| Field | Value |
|---|---|
| Username | `superadmin` |
| Password | `SuperAdmin@123` |

Change this password immediately after first login via **Admin → Change Password**.

---

## 7. Start the Frontend

```bash
cd frontend
npm start          # or: yarn start
```

The React app runs at `http://localhost:3000` and connects to the FastAPI backend at `http://localhost:8000`.

---

## 8. Emergency Admin Password Reset

If you ever get locked out:

```bash
cd /path/to/project
python emergency_admin_reset.py
```

Follow the prompts to set a new password.

---

## 9. Supabase Free Tier Limits

| Resource | Free Tier |
|---|---|
| Database | 500 MB |
| Storage | 1 GB |
| Auth MAU | 50,000 |
| Edge Functions | 500K invocations/month |
| API requests | Unlimited |

The app stores uploaded images locally (in `backend/uploads/`) — not in Supabase Storage — so storage usage is minimal.

---

## 10. Verifying the Setup

After starting the backend, test these endpoints:

```bash
# Health check
curl http://localhost:8000/api/health

# Admin login
curl -X POST http://localhost:8000/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin", "password": "SuperAdmin@123"}'
```

A successful login returns a JWT token. Use it with `Authorization: Bearer <token>` for protected routes.

---

## 11. Row Level Security

RLS is enabled on all tables. The backend uses the **service_role** key which bypasses RLS entirely, giving the FastAPI server full access. This is the correct pattern — your FastAPI app acts as the trusted backend, not individual users.

If you later add Supabase Auth or Edge Functions that make client-side database calls, add more specific RLS policies as needed.

---

## 12. PostgreSQL vs MongoDB Mapping

| MongoDB operation | Supabase equivalent |
|---|---|
| `find_one({"key": val})` | `.select("*").eq("key", val).limit(1)` |
| `find({})` | `.select("*")` |
| `insert_one(doc)` | `.insert(doc)` |
| `update_one(filter, {"$set": ...})` | `.update(...).eq(...)` |
| `delete_one(filter)` | `.delete().eq(...)` |
| `count_documents(filter)` | `.select("id", count="exact").eq(...)` |
| `{"$push": {arr: item}}` | fetch → append → `.update({arr: new_list})` |
| `{"$or": [...]}` | `.or_("col1.eq.val1,col2.eq.val2")` |
| `sort("col", -1)` | `.order("col", desc=True)` |
| `to_list(n)` | `.limit(n).execute().data` |
