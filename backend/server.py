from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, date
import jwt
import bcrypt
import shutil
import json
import pandas as pd
from io import BytesIO

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ---------------------------------------------------------------------------
# Supabase client (service role — full access, bypasses RLS)
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.environ['SUPABASE_URL']
SUPABASE_SERVICE_ROLE_KEY: str = os.environ['SUPABASE_SERVICE_ROLE_KEY']

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'campus_lost_found_secret_key')
JWT_ALGORITHM = "HS256"

# ---------------------------------------------------------------------------
# Helper: run synchronous supabase calls in a thread so we don't block the
# event loop (the supabase-py v2 client is synchronous).
# ---------------------------------------------------------------------------
async def run(fn, *args, **kwargs):
    """Execute a blocking function in a thread pool."""
    return await asyncio.to_thread(fn, *args, **kwargs)

# ---------------------------------------------------------------------------
# Supabase query helpers — wrap common patterns
# ---------------------------------------------------------------------------

async def sb_find_one(table: str, filters: dict) -> Optional[dict]:
    """Return first matching row or None."""
    def _q():
        q = supabase.table(table).select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        resp = q.limit(1).execute()
        return resp.data[0] if resp.data else None
    return await run(_q)


async def sb_find_one_select(table: str, filters: dict, columns: str) -> Optional[dict]:
    """Return first matching row with specific columns or None."""
    def _q():
        q = supabase.table(table).select(columns)
        for k, v in filters.items():
            q = q.eq(k, v)
        resp = q.limit(1).execute()
        return resp.data[0] if resp.data else None
    return await run(_q)


async def sb_find(table: str, filters: dict, order_col: str = "created_at",
                  order_asc: bool = False, limit: int = 1000,
                  columns: str = "*") -> list:
    """Return all matching rows."""
    def _q():
        q = supabase.table(table).select(columns)
        for k, v in filters.items():
            if v is None:
                q = q.is_(k, "null")
            else:
                q = q.eq(k, v)
        q = q.order(order_col, desc=not order_asc).limit(limit)
        resp = q.execute()
        return resp.data or []
    return await run(_q)


async def sb_insert(table: str, data: dict) -> dict:
    """Insert a row and return it."""
    def _q():
        resp = supabase.table(table).insert(data).execute()
        return resp.data[0] if resp.data else {}
    return await run(_q)


async def sb_update(table: str, filters: dict, updates: dict) -> list:
    """Update matching rows and return them."""
    def _q():
        q = supabase.table(table).update(updates)
        for k, v in filters.items():
            q = q.eq(k, v)
        resp = q.execute()
        return resp.data or []
    return await run(_q)


async def sb_delete(table: str, filters: dict) -> list:
    """Delete matching rows."""
    def _q():
        q = supabase.table(table).delete()
        for k, v in filters.items():
            q = q.eq(k, v)
        resp = q.execute()
        return resp.data or []
    return await run(_q)


async def sb_count(table: str, filters: dict) -> int:
    """Count matching rows using head=True exact count."""
    def _q():
        q = supabase.table(table).select("id", count="exact")
        for k, v in filters.items():
            if isinstance(v, dict) and "$in" in v:
                # Handle $in-style queries via .in_()
                q = q.in_(k, v["$in"])
            elif v is None:
                q = q.is_(k, "null")
            else:
                q = q.eq(k, v)
        resp = q.execute()
        return resp.count or 0
    return await run(_q)


async def sb_count_in(table: str, filters: dict, in_col: str, in_vals: list) -> int:
    """Count rows where column is IN a list of values + optional filters."""
    def _q():
        q = supabase.table(table).select("id", count="exact")
        for k, v in filters.items():
            q = q.eq(k, v)
        q = q.in_(in_col, in_vals)
        resp = q.execute()
        return resp.count or 0
    return await run(_q)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Campus Lost & Found API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Upload directories
UPLOAD_DIR = ROOT_DIR / "uploads"
ITEMS_DIR = UPLOAD_DIR / "items"
PROFILES_DIR = UPLOAD_DIR / "profiles"
ITEMS_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ===================== MODELS =====================

class StudentCreate(BaseModel):
    roll_number: str
    full_name: str
    department: str
    year: str
    dob: str  # DD-MM-YYYY format
    email: str
    phone_number: str

class StudentLogin(BaseModel):
    roll_number: str
    dob: str  # DD-MM-YYYY format

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminCreate(BaseModel):
    username: str
    password: str
    full_name: str

class AdminPasswordChange(BaseModel):
    old_password: str
    new_password: str

class ItemCreate(BaseModel):
    item_type: str  # "lost" or "found"
    description: str
    location: str

class ItemLike(BaseModel):
    item_id: str
    action: str  # "like" or "dislike"

class ClaimRequest(BaseModel):
    item_id: str
    message: Optional[str] = ""

class MessageCreate(BaseModel):
    recipient_id: str
    recipient_type: str  # "student" or "admin"
    content: str
    item_id: Optional[str] = None

class VerificationQuestion(BaseModel):
    claim_id: str
    question: str

class VerificationAnswer(BaseModel):
    claim_id: str
    answer: str

class DeleteReason(BaseModel):
    reason: str

class AdminNote(BaseModel):
    student_id: str
    note: str

class ClaimDecision(BaseModel):
    status: str  # "approved" or "rejected"
    notes: Optional[str] = ""

# ===================== HELPER FUNCTIONS =====================

def create_token(user_id: str, role: str, extra_data: dict = None) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7  # 7 days
    }
    if extra_data:
        payload.update(extra_data)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    return payload

async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def require_super_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return current_user

async def require_student(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return current_user

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ===================== STARTUP =====================

@app.on_event("startup")
async def startup_event():
    """Seed the superadmin and default admin accounts if they don't exist yet."""
    # --- Super Admin ---
    try:
        existing = await sb_find_one("admins", {"username": "superadmin"})
        if not existing:
            super_admin = {
                "id": str(uuid.uuid4()),
                "username": "superadmin",
                "password": hash_password("SuperAdmin@123"),
                "full_name": "Super Administrator",
                "role": "super_admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await sb_insert("admins", super_admin)
            logging.info("Super admin created with default credentials")
        else:
            logging.info("Super admin already exists")
    except Exception as exc:
        logging.error(f"Startup error (superadmin): {exc}")

    # --- Default Admin ---
    try:
        existing_admin = await sb_find_one("admins", {"username": "Admin"})
        if not existing_admin:
            default_admin = {
                "id": str(uuid.uuid4()),
                "username": "Admin",
                "password": hash_password("admin@123"),
                "full_name": "Administrator",
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await sb_insert("admins", default_admin)
            logging.info("Default admin created: username='Admin', password='admin@123'")
        else:
            logging.info("Default admin already exists")
    except Exception as exc:
        logging.error(f"Startup error (default admin): {exc}")

# ===================== TEMP SETUP (remove after use) =====================

@api_router.post("/setup/create-admin")
async def setup_create_admin():
    """Temporary one-time endpoint to seed the default admin. Remove after use."""
    existing = await sb_find_one("admins", {"username": "Admin"})
    hashed = hash_password("admin@123")
    if existing:
        await sb_update("admins", {"username": "Admin"}, {"password": hashed})
        return {"message": "Admin password reset", "username": "Admin", "password": "admin@123"}
    new_admin = {
        "id": str(uuid.uuid4()),
        "username": "Admin",
        "password": hashed,
        "full_name": "Administrator",
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await sb_insert("admins", new_admin)
    return {"message": "Admin created", "username": "Admin", "password": "admin@123"}

# ===================== AUTH ROUTES =====================

@api_router.post("/auth/student/login")
async def student_login(data: StudentLogin):
    student = await sb_find_one("students", {"roll_number": data.roll_number})

    if not student:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if student.get("is_deleted"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if student.get("dob") != data.dob:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Remove sensitive fields before returning
    user_data = {k: v for k, v in student.items() if k not in ["admin_notes"]}
    token = create_token(student["id"], "student", {"roll_number": student["roll_number"]})
    return {"token": token, "user": user_data, "role": "student"}


@api_router.post("/auth/admin/login")
async def admin_login(data: AdminLogin):
    logging.info(f"Admin login attempt - Username: '{data.username}', Password length: {len(data.password)}")

    admin = await sb_find_one("admins", {"username": data.username})
    if not admin:
        logging.warning(f"Admin not found: '{data.username}'")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    is_valid = verify_password(data.password, admin["password"])
    logging.info(f"Password verification result: {is_valid}")

    if not is_valid:
        logging.warning(f"Password verification failed for: '{data.username}'")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    admin_safe = {k: v for k, v in admin.items() if k != "password"}
    token = create_token(admin["id"], admin["role"], {"username": admin["username"]})
    logging.info(f"Login successful for: '{data.username}'")
    return {"token": token, "user": admin_safe, "role": admin["role"]}


@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    user_id = current_user.get("sub")

    if role == "student":
        user = await sb_find_one("students", {"id": user_id})
        if user:
            user.pop("admin_notes", None)
    else:
        user = await sb_find_one("admins", {"id": user_id})
        if user:
            user.pop("password", None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"user": user, "role": role}


@api_router.post("/auth/admin/change-password")
async def change_admin_password(data: AdminPasswordChange, current_user: dict = Depends(require_admin)):
    admin = await sb_find_one("admins", {"id": current_user["sub"]})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if not verify_password(data.old_password, admin["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = hash_password(data.new_password)
    await sb_update("admins", {"id": current_user["sub"]}, {"password": new_hash})
    return {"message": "Password changed successfully"}

# ===================== STUDENT MANAGEMENT =====================

@api_router.post("/students/upload-excel")
async def upload_students_excel(file: UploadFile = File(...), current_user: dict = Depends(require_admin)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed")

    content = await file.read()
    df = pd.read_excel(BytesIO(content))

    required_columns = ["Roll Number", "Full Name", "Department", "Year", "DOB", "Email", "Phone Number"]
    df_columns_lower = [col.strip().lower() for col in df.columns]

    missing = [col for col in required_columns if col.lower() not in df_columns_lower]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

    column_map = {}
    for req_col in required_columns:
        for df_col in df.columns:
            if df_col.strip().lower() == req_col.lower():
                column_map[req_col] = df_col
                break

    added = 0
    skipped = 0
    errors = []
    total_rows = len(df)

    for idx, row in df.iterrows():
        try:
            roll_number = str(row[column_map["Roll Number"]]).strip()

            existing = await sb_find_one("students", {"roll_number": roll_number})
            if existing and not existing.get("is_deleted"):
                skipped += 1
                continue

            dob_value = row[column_map["DOB"]]
            if isinstance(dob_value, datetime):
                dob_str = dob_value.strftime("%d-%m-%Y")
            else:
                dob_str = str(dob_value).strip()
                if dob_str and len(dob_str) == 10 and dob_str[2] == '-' and dob_str[5] == '-':
                    pass
                else:
                    errors.append(f"Row {idx + 2}: Invalid DOB format. Expected DD-MM-YYYY, got: {dob_str}")
                    continue

            now = datetime.now(timezone.utc)
            student = {
                "id": str(uuid.uuid4()),
                "roll_number": roll_number,
                "full_name": str(row[column_map["Full Name"]]).strip(),
                "department": str(row[column_map["Department"]]).strip(),
                "year": str(row[column_map["Year"]]).strip(),
                "dob": dob_str,
                "email": str(row[column_map["Email"]]).strip(),
                "phone_number": str(row[column_map["Phone Number"]]).strip(),
                "created_at": now.isoformat(),
                "created_date": now.strftime("%Y-%m-%d"),
                "created_time": now.strftime("%H:%M:%S"),
                "admin_notes": [],
                "is_deleted": False,
            }

            await sb_insert("students", student)
            added += 1

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")

    return {
        "message": f"Upload complete. Added: {added}, Skipped (duplicates): {skipped}",
        "total_rows": total_rows,
        "added": added,
        "skipped": skipped,
        "errors": errors
    }


@api_router.get("/students")
async def get_students(current_user: dict = Depends(require_admin)):
    """Get all non-deleted students."""
    students = await sb_find("students", {"is_deleted": False}, order_col="created_at", order_asc=False)
    return students


@api_router.get("/students/{student_id}")
async def get_student(student_id: str, current_user: dict = Depends(require_admin)):
    student = await sb_find_one("students", {"id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@api_router.post("/students/{student_id}/admin-note")
async def add_admin_note(student_id: str, data: AdminNote, current_user: dict = Depends(require_admin)):
    student = await sb_find_one("students", {"id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    note = {
        "id": str(uuid.uuid4()),
        "note": data.note,
        "added_by": current_user["sub"],
        "added_at": datetime.now(timezone.utc).isoformat()
    }

    existing_notes = student.get("admin_notes") or []
    if isinstance(existing_notes, str):
        existing_notes = json.loads(existing_notes)
    existing_notes.append(note)

    await sb_update("students", {"id": student_id}, {"admin_notes": existing_notes})
    return {"message": "Note added successfully"}


@api_router.delete("/students/{student_id}")
async def delete_student(student_id: str, current_user: dict = Depends(require_admin)):
    """Hard delete student — permanently removes from database."""
    student = await sb_find_one("students", {"id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    has_items = await sb_count("items", {"student_id": student_id}) > 0
    has_claims = await sb_count("claims", {"claimant_id": student_id}) > 0

    if has_items or has_claims:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete student with active items or claims. Please resolve them first."
        )

    await sb_delete("students", {"id": student_id})
    return {"message": "Student deleted successfully"}

# ===================== STUDENT PROFILE =====================

@api_router.get("/profile")
async def get_profile(current_user: dict = Depends(require_student)):
    student = await sb_find_one("students", {"id": current_user["sub"]})
    if not student:
        raise HTTPException(status_code=404, detail="Profile not found")
    student.pop("admin_notes", None)
    return student


@api_router.post("/profile/picture")
async def upload_profile_picture(file: UploadFile = File(...), current_user: dict = Depends(require_student)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{current_user['sub']}.{ext}"
    filepath = PROFILES_DIR / filename

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    picture_url = f"/uploads/profiles/{filename}"
    await sb_update("students", {"id": current_user["sub"]}, {"profile_picture": picture_url})
    return {"message": "Profile picture updated", "picture_url": picture_url}

# ===================== ITEMS MANAGEMENT =====================

@api_router.post("/items")
async def create_item(
    item_type: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    image: UploadFile = File(...),
    current_user: dict = Depends(require_student)
):
    if item_type not in ["lost", "found"]:
        raise HTTPException(status_code=400, detail="Item type must be 'lost' or 'found'")

    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    item_id = str(uuid.uuid4())
    ext = image.filename.split(".")[-1] if "." in image.filename else "jpg"
    image_filename = f"{item_id}.{ext}"
    image_path = ITEMS_DIR / image_filename

    with open(image_path, "wb") as f:
        content = await image.read()
        f.write(content)

    now = datetime.now(timezone.utc)
    item = {
        "id": item_id,
        "item_type": item_type,
        "description": description,
        "location": location,
        "image_url": f"/uploads/items/{image_filename}",
        "student_id": current_user["sub"],
        "status": "active",
        "is_deleted": False,
        "delete_reason": None,
        "deleted_at": None,
        "created_at": now.isoformat(),
        "created_date": now.strftime("%Y-%m-%d"),
        "created_time": now.strftime("%H:%M:%S"),
        "likes": 0,
        "dislikes": 0,
        "liked_by": [],
        "disliked_by": [],
    }

    await sb_insert("items", item)

    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "item_created",
        "item_id": item_id,
        "user_id": current_user["sub"],
        "user_role": "student",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Item reported successfully", "item_id": item_id}

# ===================== GET ITEMS =====================

@api_router.get("/items")
async def get_items(
    item_type: Optional[str] = None,
    status: Optional[str] = None,
    include_deleted: bool = False,
    current_user: dict = Depends(get_current_user)
):
    def _q():
        q = supabase.table("items").select("*")
        if current_user["role"] == "student":
            q = q.eq("student_id", current_user["sub"]).eq("is_deleted", False)
        elif not include_deleted:
            q = q.eq("is_deleted", False)
        if item_type:
            q = q.eq("item_type", item_type)
        if status:
            q = q.eq("status", status)
        q = q.order("created_at", desc=True).limit(1000)
        resp = q.execute()
        return resp.data or []

    items = await run(_q)

    if current_user["role"] in ["admin", "super_admin"]:
        for item in items:
            student = await sb_find_one_select(
                "students", {"id": item["student_id"]},
                "id,full_name,roll_number,department"
            )
            item["student"] = student

    return items


@api_router.get("/items/my")
async def get_my_items(current_user: dict = Depends(require_student)):
    items = await sb_find("items",
                          {"student_id": current_user["sub"], "is_deleted": False},
                          order_col="created_at", order_asc=False, limit=100)
    return items


@api_router.get("/items/public")
async def get_public_items():
    """Public endpoint — shows recently found items without sensitive data."""
    def _q():
        resp = (supabase.table("items")
                .select("id,item_type,description,location,image_url,status,created_at,created_date,created_time,likes,dislikes")
                .eq("item_type", "found")
                .eq("is_deleted", False)
                .eq("status", "active")
                .order("created_at", desc=True)
                .limit(50)
                .execute())
        return resp.data or []
    return await run(_q)


@api_router.get("/items/deleted/all")
async def get_deleted_items(current_user: dict = Depends(require_admin)):
    items = await sb_find("items", {"is_deleted": True}, order_col="deleted_at", order_asc=False, limit=500)
    for item in items:
        student = await sb_find_one_select(
            "students", {"id": item["student_id"]},
            "id,full_name,roll_number,department"
        )
        item["student"] = student
    return items


@api_router.get("/items/{item_id}")
async def get_item(item_id: str, current_user: dict = Depends(get_current_user)):
    item = await sb_find_one("items", {"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if current_user["role"] == "student" and item["student_id"] != current_user["sub"]:
        if item["is_deleted"]:
            raise HTTPException(status_code=404, detail="Item not found")

    if current_user["role"] in ["admin", "super_admin"]:
        student = await sb_find_one_select(
            "students", {"id": item["student_id"]},
            "id,full_name,roll_number,department"
        )
        item["student"] = student

    return item


@api_router.delete("/items/{item_id}")
async def soft_delete_item(item_id: str, data: DeleteReason, current_user: dict = Depends(require_student)):
    item = await sb_find_one("items", {"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item["student_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="You can only delete your own items")

    await sb_update("items", {"id": item_id}, {
        "is_deleted": True,
        "delete_reason": data.reason,
        "deleted_at": datetime.now(timezone.utc).isoformat()
    })

    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "item_soft_deleted",
        "item_id": item_id,
        "user_id": current_user["sub"],
        "user_role": "student",
        "reason": data.reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Item deleted successfully"}


@api_router.post("/items/{item_id}/restore")
async def restore_item(item_id: str, current_user: dict = Depends(require_admin)):
    rows = await sb_update("items", {"id": item_id, "is_deleted": True}, {
        "is_deleted": False,
        "delete_reason": None,
        "deleted_at": None
    })

    if not rows:
        raise HTTPException(status_code=404, detail="Item not found or not deleted")

    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "item_restored",
        "item_id": item_id,
        "user_id": current_user["sub"],
        "user_role": current_user["role"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Item restored successfully"}


@api_router.delete("/items/{item_id}/permanent")
async def permanent_delete_item(item_id: str, current_user: dict = Depends(require_admin)):
    item = await sb_find_one("items", {"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.get("image_url"):
        image_path = ROOT_DIR / item["image_url"].lstrip("/")
        if image_path.exists():
            image_path.unlink()

    await sb_delete("items", {"id": item_id})

    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "item_permanent_deleted",
        "item_id": item_id,
        "user_id": current_user["sub"],
        "user_role": current_user["role"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Item permanently deleted"}


@api_router.post("/items/{item_id}/like-dislike")
async def like_dislike_item(item_id: str, data: ItemLike, current_user: dict = Depends(get_current_user)):
    """Like or dislike an item."""
    item = await sb_find_one("items", {"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    user_id = current_user["sub"]
    action = data.action.lower()

    if action not in ["like", "dislike"]:
        raise HTTPException(status_code=400, detail="Action must be 'like' or 'dislike'")

    liked_by = item.get("liked_by") or []
    disliked_by = item.get("disliked_by") or []
    if isinstance(liked_by, str):
        liked_by = json.loads(liked_by)
    if isinstance(disliked_by, str):
        disliked_by = json.loads(disliked_by)

    if user_id in liked_by:
        liked_by.remove(user_id)
    if user_id in disliked_by:
        disliked_by.remove(user_id)

    if action == "like":
        liked_by.append(user_id)
    else:
        disliked_by.append(user_id)

    await sb_update("items", {"id": item_id}, {
        "likes": len(liked_by),
        "dislikes": len(disliked_by),
        "liked_by": liked_by,
        "disliked_by": disliked_by
    })

    return {
        "message": f"Item {action}d successfully",
        "likes": len(liked_by),
        "dislikes": len(disliked_by)
    }


@api_router.delete("/items/{item_id}/like-dislike")
async def remove_like_dislike(item_id: str, current_user: dict = Depends(get_current_user)):
    """Remove like/dislike from an item."""
    item = await sb_find_one("items", {"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    user_id = current_user["sub"]
    liked_by = item.get("liked_by") or []
    disliked_by = item.get("disliked_by") or []
    if isinstance(liked_by, str):
        liked_by = json.loads(liked_by)
    if isinstance(disliked_by, str):
        disliked_by = json.loads(disliked_by)

    if user_id in liked_by:
        liked_by.remove(user_id)
    if user_id in disliked_by:
        disliked_by.remove(user_id)

    await sb_update("items", {"id": item_id}, {
        "likes": len(liked_by),
        "dislikes": len(disliked_by),
        "liked_by": liked_by,
        "disliked_by": disliked_by
    })

    return {
        "message": "Like/Dislike removed successfully",
        "likes": len(liked_by),
        "dislikes": len(disliked_by)
    }

# ===================== CLAIMS =====================

@api_router.post("/claims")
async def create_claim(data: ClaimRequest, current_user: dict = Depends(require_student)):
    item = await sb_find_one("items", {"id": data.item_id})
    if not item or item.get("is_deleted"):
        raise HTTPException(status_code=404, detail="Item not found")

    # Check for existing pending/under_review claim
    def _check_existing():
        resp = (supabase.table("claims")
                .select("id")
                .eq("item_id", data.item_id)
                .eq("claimant_id", current_user["sub"])
                .in_("status", ["pending", "under_review"])
                .limit(1)
                .execute())
        return resp.data

    existing = await run(_check_existing)
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending claim for this item")

    claim = {
        "id": str(uuid.uuid4()),
        "item_id": data.item_id,
        "claimant_id": current_user["sub"],
        "message": data.message,
        "status": "pending",
        "verification_questions": [],
        "verification_answers": [],
        "admin_notes": "",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await sb_insert("claims", claim)
    return {"message": "Claim submitted successfully", "claim_id": claim["id"]}


@api_router.get("/claims")
async def get_claims(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    def _q():
        q = supabase.table("claims").select("*")
        if current_user["role"] == "student":
            q = q.eq("claimant_id", current_user["sub"])
        if status:
            q = q.eq("status", status)
        resp = q.order("created_at", desc=True).limit(500).execute()
        return resp.data or []

    claims = await run(_q)

    for claim in claims:
        item = await sb_find_one("items", {"id": claim["item_id"]})
        claim["item"] = item
        if current_user["role"] in ["admin", "super_admin"]:
            claimant = await sb_find_one_select(
                "students", {"id": claim["claimant_id"]},
                "id,full_name,roll_number,department"
            )
            claim["claimant"] = claimant

    return claims


@api_router.get("/claims/{claim_id}")
async def get_claim(claim_id: str, current_user: dict = Depends(get_current_user)):
    claim = await sb_find_one("claims", {"id": claim_id})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if current_user["role"] == "student" and claim["claimant_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    item = await sb_find_one("items", {"id": claim["item_id"]})
    claim["item"] = item

    if current_user["role"] in ["admin", "super_admin"]:
        claimant = await sb_find_one("students", {"id": claim["claimant_id"]})
        if claimant:
            claimant.pop("admin_notes", None)
        claim["claimant"] = claimant

    return claim


@api_router.post("/claims/{claim_id}/verification-question")
async def add_verification_question(claim_id: str, data: VerificationQuestion, current_user: dict = Depends(require_admin)):
    claim = await sb_find_one("claims", {"id": claim_id})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    question = {
        "id": str(uuid.uuid4()),
        "question": data.question,
        "asked_by": current_user["sub"],
        "asked_at": datetime.now(timezone.utc).isoformat()
    }

    existing_qs = claim.get("verification_questions") or []
    if isinstance(existing_qs, str):
        existing_qs = json.loads(existing_qs)
    existing_qs.append(question)

    await sb_update("claims", {"id": claim_id}, {
        "verification_questions": existing_qs,
        "status": "under_review"
    })

    await sb_insert("messages", {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["sub"],
        "sender_type": "admin",
        "recipient_id": claim["claimant_id"],
        "recipient_type": "student",
        "content": f"Verification question for your claim: {data.question}",
        "item_id": claim["item_id"],
        "claim_id": claim_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Verification question sent"}


@api_router.post("/claims/{claim_id}/answer")
async def answer_verification(claim_id: str, data: VerificationAnswer, current_user: dict = Depends(require_student)):
    claim = await sb_find_one("claims", {"id": claim_id})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim["claimant_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    answer = {
        "id": str(uuid.uuid4()),
        "answer": data.answer,
        "answered_at": datetime.now(timezone.utc).isoformat()
    }

    existing_ans = claim.get("verification_answers") or []
    if isinstance(existing_ans, str):
        existing_ans = json.loads(existing_ans)
    existing_ans.append(answer)

    await sb_update("claims", {"id": claim_id}, {"verification_answers": existing_ans})
    return {"message": "Answer submitted"}


@api_router.post("/claims/{claim_id}/decision")
async def claim_decision(claim_id: str, data: ClaimDecision, current_user: dict = Depends(require_admin)):
    if data.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    claim = await sb_find_one("claims", {"id": claim_id})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    await sb_update("claims", {"id": claim_id}, {
        "status": data.status,
        "admin_notes": data.notes or ""
    })

    if data.status == "approved":
        await sb_update("items", {"id": claim["item_id"]}, {"status": "claimed"})

    status_text = "approved" if data.status == "approved" else "rejected"
    await sb_insert("messages", {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["sub"],
        "sender_type": "admin",
        "recipient_id": claim["claimant_id"],
        "recipient_type": "student",
        "content": f"Your claim has been {status_text}. {data.notes or ''}",
        "item_id": claim["item_id"],
        "claim_id": claim_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": f"Claim {status_text}"}

# ===================== MESSAGING =====================

@api_router.post("/messages")
async def send_message(data: MessageCreate, current_user: dict = Depends(require_admin)):
    message = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["sub"],
        "sender_type": current_user["role"],
        "recipient_id": data.recipient_id,
        "recipient_type": data.recipient_type,
        "content": data.content,
        "item_id": data.item_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await sb_insert("messages", message)
    return {"message": "Message sent", "message_id": message["id"]}


@api_router.get("/messages")
async def get_messages(current_user: dict = Depends(get_current_user)):
    def _q():
        if current_user["role"] == "student":
            resp = (supabase.table("messages")
                    .select("*")
                    .eq("recipient_id", current_user["sub"])
                    .eq("recipient_type", "student")
                    .order("created_at", desc=True)
                    .limit(500)
                    .execute())
        else:
            # Admin: all messages where they are sender OR recipient
            uid = current_user["sub"]
            resp = (supabase.table("messages")
                    .select("*")
                    .or_(f"sender_id.eq.{uid},recipient_id.eq.{uid}")
                    .order("created_at", desc=True)
                    .limit(500)
                    .execute())
        return resp.data or []

    return await run(_q)


@api_router.get("/messages/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    def _q():
        resp = (supabase.table("messages")
                .select("id", count="exact")
                .eq("recipient_id", current_user["sub"])
                .eq("is_read", False)
                .execute())
        return resp.count or 0
    count = await run(_q)
    return {"count": count}


@api_router.post("/messages/{message_id}/read")
async def mark_message_read(message_id: str, current_user: dict = Depends(get_current_user)):
    await sb_update(
        "messages",
        {"id": message_id, "recipient_id": current_user["sub"]},
        {"is_read": True}
    )
    return {"message": "Marked as read"}


@api_router.post("/messages/mark-all-read")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    def _q():
        resp = (supabase.table("messages")
                .update({"is_read": True})
                .eq("recipient_id", current_user["sub"])
                .eq("is_read", False)
                .execute())
        return resp.data
    await run(_q)
    return {"message": "All messages marked as read"}

# ===================== AI MATCHING =====================

@api_router.get("/ai/matches")
async def get_ai_matches(current_user: dict = Depends(require_admin)):
    """Get AI-suggested matches between lost and found items."""
    lost_items = await sb_find("items",
                               {"item_type": "lost", "is_deleted": False, "status": "active"},
                               limit=100)
    found_items = await sb_find("items",
                                {"item_type": "found", "is_deleted": False, "status": "active"},
                                limit=100)

    if not lost_items or not found_items:
        return {"matches": [], "message": "Not enough items to match"}

    matches = []
    try:
        from openai import AsyncOpenAI

        api_key = os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {"matches": [], "message": "AI service not configured"}

        client = AsyncOpenAI(api_key=api_key)

        lost_summary = [
            {"id": i["id"], "desc": i["description"], "loc": i["location"],
             "date": i.get("created_date", "")}
            for i in lost_items[:20]
        ]
        found_summary = [
            {"id": i["id"], "desc": i["description"], "loc": i["location"],
             "date": i.get("created_date", "")}
            for i in found_items[:20]
        ]

        prompt = f"""Match these lost items with found items:

LOST ITEMS:
{json.dumps(lost_summary, indent=2)}

FOUND ITEMS:
{json.dumps(found_summary, indent=2)}

Return ONLY a JSON array of matches with confidence scores."""

        response_obj = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant helping match lost items with found items in a campus "
                        "lost and found system.\nCompare items based on description, location, date, and time.\n"
                        "Return ONLY valid JSON array with matches. Each match should have:\n"
                        "- lost_id: ID of the lost item\n"
                        "- found_id: ID of the found item\n"
                        "- confidence: Score from 0 to 100\n"
                        "- reason: Brief explanation of why they might match\n"
                        "Only include matches with confidence >= 50."
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )
        response = response_obj.choices[0].message.content or ""

        try:
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                matches_data = json.loads(json_match.group())
                for match in matches_data:
                    if match.get("confidence", 0) >= 50:
                        lost_item = next((i for i in lost_items if i["id"] == match["lost_id"]), None)
                        found_item = next((i for i in found_items if i["id"] == match["found_id"]), None)
                        if lost_item and found_item:
                            lost_student = await sb_find_one_select(
                                "students", {"id": lost_item["student_id"]},
                                "id,full_name,roll_number"
                            )
                            found_student = await sb_find_one_select(
                                "students", {"id": found_item["student_id"]},
                                "id,full_name,roll_number"
                            )
                            matches.append({
                                "lost_item": {**lost_item, "student": lost_student},
                                "found_item": {**found_item, "student": found_student},
                                "confidence": match.get("confidence", 0),
                                "reason": match.get("reason", "")
                            })
        except json.JSONDecodeError:
            logging.error(f"Failed to parse AI response: {response}")

    except Exception as e:
        logging.error(f"AI matching error: {str(e)}")
        return {"matches": [], "message": "AI matching temporarily unavailable"}

    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return {"matches": matches}

# ===================== ADMIN MANAGEMENT =====================

@api_router.post("/admins")
async def create_admin(data: AdminCreate, current_user: dict = Depends(require_super_admin)):
    existing = await sb_find_one("admins", {"username": data.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    admin = {
        "id": str(uuid.uuid4()),
        "username": data.username,
        "password": hash_password(data.password),
        "full_name": data.full_name,
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["sub"]
    }

    await sb_insert("admins", admin)
    return {"message": "Admin created successfully", "admin_id": admin["id"]}


@api_router.get("/admins")
async def get_admins(current_user: dict = Depends(require_super_admin)):
    def _q():
        resp = (supabase.table("admins")
                .select("id,username,full_name,role,created_at,created_by")
                .order("created_at", desc=False)
                .limit(100)
                .execute())
        return resp.data or []
    return await run(_q)


@api_router.delete("/admins/{admin_id}")
async def delete_admin(admin_id: str, current_user: dict = Depends(require_super_admin)):
    admin = await sb_find_one("admins", {"id": admin_id})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if admin["role"] == "super_admin":
        raise HTTPException(status_code=400, detail="Cannot delete super admin")

    await sb_delete("admins", {"id": admin_id})
    return {"message": "Admin deleted successfully"}

# ===================== DASHBOARD STATS =====================

@api_router.get("/stats")
async def get_stats(current_user: dict = Depends(require_admin)):
    def _count(table, **filters):
        q = supabase.table(table).select("id", count="exact")
        for k, v in filters.items():
            if isinstance(v, list):
                q = q.in_(k, v)
            else:
                q = q.eq(k, v)
        return q.execute().count or 0

    def _q():
        total_students = _count("students")
        total_lost = _count("items", item_type="lost", is_deleted=False)
        total_found = _count("items", item_type="found", is_deleted=False)
        pending_claims = _count("claims", status=["pending", "under_review"])
        resolved_items = _count("items", status="claimed")
        deleted_items = _count("items", is_deleted=True)
        return {
            "total_students": total_students,
            "total_lost": total_lost,
            "total_found": total_found,
            "pending_claims": pending_claims,
            "resolved_items": resolved_items,
            "deleted_items": deleted_items
        }

    return await run(_q)

# ===================== HEALTH CHECK =====================

@api_router.get("/")
async def root():
    return {"message": "Campus Lost & Found API", "status": "running"}


@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# ---------------------------------------------------------------------------
# Register router and middleware
# ---------------------------------------------------------------------------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
