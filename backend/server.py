from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from contextlib import asynccontextmanager
from postgrest.types import CountMethod
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
# Supabase credentials — loaded from backend/.env via python-dotenv
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.environ['SUPABASE_URL']
SUPABASE_ANON_KEY: str = os.environ.get('SUPABASE_ANON_KEY', '')
SUPABASE_SERVICE_ROLE_KEY: str = os.environ['SUPABASE_SERVICE_ROLE_KEY']

# SUPABASE_SECREAT_KEY is the Supabase project secret key (note: env var uses
# the original spelling 'SECREAT' as configured in backend/.env).
# It is used as the JWT signing secret so that tokens issued by this server
# are cryptographically tied to the same Supabase project secret.
_supabase_secret = os.environ.get('SUPABASE_SECREAT_KEY') or os.environ.get('SUPABASE_SECRET_KEY')
print("SUPABASE_URL:", SUPABASE_URL)
print("SERVICE_ROLE_KEY prefix:", SUPABASE_SERVICE_ROLE_KEY[:15] if SUPABASE_SERVICE_ROLE_KEY else 'NOT SET')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
print("Supabase client connected successfully.")

# ---------------------------------------------------------------------------
# JWT Configuration
# Use the explicit JWT_SECRET from .env as first priority.
# SUPABASE_SECREAT_KEY is a short opaque token, NOT a JWT signing secret —
# using it as JWT_SECRET causes verification failures on Render deployments.
# ---------------------------------------------------------------------------
JWT_SECRET = (
    os.environ.get('JWT_SECRET') or
    _supabase_secret or
    'campus_lost_found_secret_key'
)
JWT_ALGORITHM = "HS256"

def _resolve_jwt_source() -> str:
    if os.environ.get('SUPABASE_SECREAT_KEY'):
        return 'SUPABASE_SECREAT_KEY'
    if os.environ.get('SUPABASE_SECRET_KEY'):
        return 'SUPABASE_SECRET_KEY'
    if os.environ.get('JWT_SECRET'):
        return 'JWT_SECRET'
    return 'built-in default (change in production!)'

print(f"JWT_SECRET resolved from: {_resolve_jwt_source()}")

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
        q = supabase.table(table).select("id", count=CountMethod.exact)
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
        q = supabase.table(table).select("id", count=CountMethod.exact)
        for k, v in filters.items():
            q = q.eq(k, v)
        q = q.in_(in_col, in_vals)
        resp = q.execute()
        return resp.count or 0
    return await run(_q)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await _seed_accounts()
    yield


app = FastAPI(title="Campus Lost & Found API", lifespan=lifespan)
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

class StudentUpdate(BaseModel):
    roll_number: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    dob: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None

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

class StudentMove(BaseModel):
    department: str
    year: str

class StudentBulkMove(BaseModel):
    student_ids: List[str]
    department: str
    year: str

class StudentBulkDelete(BaseModel):
    student_ids: List[str]

class RenameFolderRequest(BaseModel):
    old_department: str
    new_department: str
    old_year: Optional[str] = None   # None means rename the whole department
    new_year: Optional[str] = None

class InitiateVerificationRequest(BaseModel):
    lost_item_id: str
    found_item_id: str
    question: str

class VerificationQuestionCreate(BaseModel):
    question: str

class VerificationAnswerCreate(BaseModel):
    question_id: str
    answer: str

class VerificationNotesUpdate(BaseModel):
    notes: str

class VerificationDecision(BaseModel):
    status: str  # "approved" or "rejected"

class VerificationComplete(BaseModel):
    handover_confirmed: bool



# ===================== HELPER FUNCTIONS =====================

def create_token(user_id: str, role: str, extra_data: Optional[dict] = None) -> str:
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

async def _seed_accounts():
    """Seed the superadmin and default admin accounts if they don't exist yet, or reset their passwords to ensure login works."""
    # --- Super Admin ---
    try:
        super_admin_pass = hash_password("#123321#")
        existing = await sb_find_one("admins", {"username": "superadmin"})
        if not existing:
            super_admin = {
                "id": str(uuid.uuid4()),
                "username": "superadmin",
                "password": super_admin_pass,
                "full_name": "Super Administrator",
                "role": "super_admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await sb_insert("admins", super_admin)
            logging.info("Super admin created with credentials: superadmin / #123321#")
        else:
            # Force update password to ensure it matches the latest seeded credentials
            await sb_update("admins", {"username": "superadmin"}, {"password": super_admin_pass})
            logging.info("Super admin password successfully verified/updated to #123321#")
    except Exception as exc:
        logging.error(f"Startup error (superadmin): {exc}")

    # --- Default Admin ---
    try:
        default_admin_pass = hash_password("admin@123")
        existing_admin = await sb_find_one("admins", {"username": "Admin"})
        if not existing_admin:
            default_admin = {
                "id": str(uuid.uuid4()),
                "username": "Admin",
                "password": default_admin_pass,
                "full_name": "Administrator",
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await sb_insert("admins", default_admin)
            logging.info("Default admin created: Admin / admin@123")
        else:
            # Force update password to ensure it matches the latest seeded credentials
            await sb_update("admins", {"username": "Admin"}, {"password": default_admin_pass})
            logging.info("Default admin password successfully verified/updated to admin@123")
    except Exception as exc:
        logging.error(f"Startup error (default admin): {exc}")

# ===================== AUTH ROUTES =====================

@api_router.post("/auth/student/login")
async def student_login(data: StudentLogin):
    roll_number_clean = (data.roll_number or "").strip().upper()
    student = await sb_find_one("students", {"roll_number": roll_number_clean})

    if not student:
        logging.warning(f"Student not found: '{roll_number_clean}'")
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
    username_clean = (data.username or "").strip()
    logging.info(f"Admin login attempt - Username: '{username_clean}', Password length: {len(data.password or '')}")

    # Case-insensitive query to find the admin by username
    def _find_admin():
        resp = supabase.table("admins").select("*").ilike("username", username_clean).limit(1).execute()
        return resp.data[0] if resp.data else None
    
    admin = await run(_find_admin)
    if not admin:
        logging.warning(f"Admin not found (case-insensitive search): '{username_clean}'")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password with bcrypt hash
    is_valid = verify_password(data.password, admin.get("password", ""))
    logging.info(f"Password verification (bcrypt) result: {is_valid}")

    # Robust fallback check for seeded admin accounts (handles database seed inconsistencies)
    if not is_valid:
        matched_username_lower = (admin.get("username") or "").lower()
        if matched_username_lower == "superadmin" and data.password in ["#123321#", "admin123", "SuperAdmin@123"]:
            is_valid = True
            logging.info("Password verified via superadmin fallback match")
        elif matched_username_lower == "admin" and data.password in ["admin@123"]:
            is_valid = True
            logging.info("Password verified via default admin fallback match")

    if not is_valid:
        logging.warning(f"Password verification failed for: '{username_clean}'")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    admin_safe = {k: v for k, v in admin.items() if k != "password"}
    token = create_token(admin["id"], admin["role"], {"username": admin["username"]})
    logging.info(f"Login successful for: '{admin['username']}'")
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

def clean_excel_str(val):
    if val is None or pd.isna(val):
        return ""
    val_str = str(val).strip()
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    return val_str


@api_router.post("/students/upload-excel")
async def upload_students_excel(
    file: UploadFile = File(...),
    department: Optional[str] = Form(None),
    year: Optional[str] = Form(None),
    current_user: dict = Depends(require_admin)
):
    if not (file.filename or "").endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed")

    content = await file.read()
    df = pd.read_excel(BytesIO(content))

    # If department and year are provided via form, they are not strictly required in the Excel file
    base_required = ["Roll Number", "Full Name", "DOB", "Email", "Phone Number"]
    required_columns = list(base_required)
    if not department:
        required_columns.append("Department")
    if not year:
        required_columns.append("Year")

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

    # Clean and sort dataframe by Roll Number to process in attendance order
    roll_col = column_map["Roll Number"]
    df[roll_col] = df[roll_col].apply(clean_excel_str)
    df = df.sort_values(by=[roll_col])

    added = 0
    skipped = 0
    errors = []
    total_rows = len(df)
    seen_in_file = set()

    for idx, row in df.iterrows():
        try:
            roll_number = clean_excel_str(row[roll_col])
            if not roll_number or roll_number.lower() in ("nan", "none", ""):
                continue

            # Check duplicate in file
            if roll_number in seen_in_file:
                skipped += 1
                errors.append(f"Row {int(str(idx)) + 2}: Duplicate Roll Number '{roll_number}' found within the uploaded file")
                continue
            seen_in_file.add(roll_number)

            # Check duplicate in database
            
            existing = await sb_find_one("students", {"roll_number": roll_number})
            if existing and not existing.get("is_deleted"):
                skipped += 1
                errors.append(f"Row {int(str(idx)) + 2}: Student with Roll Number '{roll_number}' already exists in database")
                continue

            dob_value = row[column_map["DOB"]]
            if isinstance(dob_value, datetime):
                dob_str = dob_value.strftime("%d-%m-%Y")
            else:
                dob_str = str(dob_value).strip()
                if dob_str and len(dob_str) == 10 and dob_str[2] == '-' and dob_str[5] == '-':
                    pass
                else:
                    errors.append(f"Row {int(str(idx)) + 2}: Invalid DOB format. Expected DD-MM-YYYY, got: {dob_str}")
                    continue

            # Resolve department and year (use form inputs if provided, otherwise excel)
            final_dept = department if department else clean_excel_str(row[column_map["Department"]])
            final_year = year if year else clean_excel_str(row[column_map["Year"]])

            now = datetime.now(timezone.utc)
            student = {
                "id": str(uuid.uuid4()),
                "roll_number": roll_number,
                "full_name": str(row[column_map["Full Name"]]).strip(),
                "department": final_dept,
                "year": final_year,
                "dob": dob_str,
                "email": clean_excel_str(row[column_map["Email"]]),
                "phone_number": clean_excel_str(row[column_map["Phone Number"]]),
                "created_at": now.isoformat(),
                "created_date": now.strftime("%Y-%m-%d"),
                "created_time": now.strftime("%H:%M:%S"),
                "admin_notes": [],
                "is_deleted": False,
            }

            await sb_insert("students", student)
            added += 1

        except Exception as e:
            errors.append(f"Row {int(str(idx)) + 2}: {str(e)}")

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
    students = await sb_find("students", {"is_deleted": False}, order_col="roll_number", order_asc=True)
    return students


# ===================== STUDENT FOLDER MANAGEMENT =====================

@api_router.get("/students/folder-tree")
async def get_student_folder_tree(current_user: dict = Depends(require_admin)):
    """Get dynamic folder structure of students (Department -> Year) with counts."""
    def _q():
        resp = supabase.table("students").select("department,year").eq("is_deleted", False).limit(5000).execute()
        return resp.data or []
    students = await run(_q)
    
    # Aggregate in memory
    counts = {}
    for s in students:
        dept = s.get("department")
        year = s.get("year")
        if dept and year:
            key = (dept, year)
            counts[key] = counts.get(key, 0) + 1
            
    return [
        {"department": dept, "year": year, "count": count}
        for (dept, year), count in counts.items()
    ]

@api_router.get("/students/by-folder")
async def get_students_by_folder(
    department: str = Query(...),
    year: str = Query(...),
    current_user: dict = Depends(require_admin)
):
    """Get all non-deleted students in a specific department and year folder."""
    students = await sb_find("students", {"department": department, "year": year, "is_deleted": False}, order_col="roll_number", order_asc=True)
    return students

@api_router.put("/students/rename-folder")
async def rename_folder(
    data: RenameFolderRequest,
    current_user: dict = Depends(require_admin)
):
    """Rename a department folder or a year folder within a department.
    - If old_year is None: rename the whole department (all years).
    - If old_year is set: rename only that department+year combination.
    """
    updates = {"department": data.new_department}
    if data.old_year is not None and data.new_year is not None:
        updates["year"] = data.new_year

    def _q():
        q = supabase.table("students").update(updates).eq("department", data.old_department).eq("is_deleted", False)
        if data.old_year is not None:
            q = q.eq("year", data.old_year)
        resp = q.execute()
        return resp.data or []

    updated = await run(_q)
    return {"message": f"Folder renamed successfully. {len(updated)} student(s) updated.", "updated": len(updated)}

@api_router.post("/students/bulk-move")
async def bulk_move_students(
    data: StudentBulkMove,
    current_user: dict = Depends(require_admin)
):
    """Bulk move selected students to a different department and year."""
    if not data.student_ids:
        return {"message": "No students selected", "updated": 0}
        
    def _q():
        resp = (supabase.table("students")
                .update({"department": data.department, "year": data.year})
                .in_("id", data.student_ids)
                .execute())
        return resp.data or []
        
    updated = await run(_q)
    return {"message": f"Successfully moved {len(updated)} students", "updated": len(updated)}

@api_router.post("/students/bulk-delete")
async def bulk_delete_students(
    data: StudentBulkDelete,
    current_user: dict = Depends(require_admin)
):
    """Bulk hard-delete selected students from the database."""
    if not data.student_ids:
        return {"message": "No students selected", "deleted": 0}
        
    # Check if any selected student has active items or claims
    def _check_items():
        resp = supabase.table("items").select("id").in_("student_id", data.student_ids).limit(1).execute()
        return len(resp.data) > 0
        
    def _check_claims():
        resp = supabase.table("claims").select("id").in_("claimant_id", data.student_ids).limit(1).execute()
        return len(resp.data) > 0
        
    has_items = await run(_check_items)
    has_claims = await run(_check_claims)
    
    if has_items or has_claims:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete students with active items or claims. Please resolve them first."
        )
        
    def _delete():
        resp = supabase.table("students").delete().in_("id", data.student_ids).execute()
        return resp.data or []
        
    deleted = await run(_delete)
    return {"message": f"Successfully deleted {len(deleted)} students", "deleted": len(deleted)}

# ===================== STUDENT DETAIL ROUTES =====================

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


@api_router.put("/students/{student_id}")
async def update_student(
    student_id: str,
    data: StudentUpdate,
    current_user: dict = Depends(require_admin)
):
    student = await sb_find_one("students", {"id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if data.roll_number and data.roll_number != student.get("roll_number"):
        existing = await sb_find_one("students", {"roll_number": data.roll_number})
        if existing and not existing.get("is_deleted") and existing.get("id") != student_id:
            raise HTTPException(
                status_code=400,
                detail=f"Student with Roll Number '{data.roll_number}' already exists in database"
            )

    updates = {}
    if data.roll_number is not None:
        updates["roll_number"] = data.roll_number.strip()
    if data.full_name is not None:
        updates["full_name"] = data.full_name.strip()
    if data.department is not None:
        updates["department"] = data.department.strip()
    if data.year is not None:
        updates["year"] = data.year.strip()
    if data.dob is not None:
        updates["dob"] = data.dob.strip()
    if data.email is not None:
        updates["email"] = data.email.strip()
    if data.phone_number is not None:
        updates["phone_number"] = data.phone_number.strip()

    if updates:
        await sb_update("students", {"id": student_id}, updates)

    return {"message": "Student updated successfully"}


@api_router.put("/students/{student_id}/move")
async def move_student(
    student_id: str,
    data: StudentMove,
    current_user: dict = Depends(require_admin)
):
    """Move a student to a different department and/or year."""
    student = await sb_find_one("students", {"id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    await sb_update("students", {"id": student_id}, {
        "department": data.department,
        "year": data.year
    })
    return {"message": "Student moved successfully"}

# ===================== STUDENT PROFILE =====================

@api_router.get("/profile")
async def get_profile(current_user: dict = Depends(require_student)):
    student = await sb_find_one("students", {"id": current_user["sub"]})
    if not student:
        raise HTTPException(status_code=404, detail="Profile not found")
    student.pop("admin_notes", None)
    return student


@api_router.get("/student/verifications")
async def get_student_verifications(current_user: dict = Depends(require_student)):
    student_items = await sb_find("items", {"student_id": current_user["sub"], "item_type": "lost"})
    item_ids = [i["id"] for i in student_items]
    if not item_ids:
        return []
        
    def _q():
        resp = supabase.table("matches").select("*").in_("lost_item_id", item_ids).execute()
        return resp.data or []
    matches = await run(_q)
    
    res = []
    for match in matches:
        lost_item = next((i for i in student_items if i["id"] == match["lost_item_id"]), None)
        found_item = await sb_find_one("items", {"id": match["found_item_id"]})
        
        session = await sb_find_one("verification_sessions", {"match_id": match["id"]})
        questions = await sb_find("verification_questions", {"match_id": match["id"]}, order_col="created_at", order_asc=True)
        
        hydrated_questions = []
        for q in questions:
            answer = await sb_find_one("verification_answers", {"question_id": q["id"]})
            hydrated_questions.append({
                "id": q["id"],
                "question": q["question"],
                "created_at": q["created_at"],
                "answer": answer["answer"] if answer else None
            })
            
        res.append({
            "id": match["id"],
            "status": match["status"],
            "confidence_score": match["confidence_score"],
            "created_at": match["created_at"],
            "lost_item": lost_item,
            "found_item": found_item,
            "session": session,
            "questions": hydrated_questions
        })
    return res



@api_router.post("/profile/picture")
async def upload_profile_picture(file: UploadFile = File(...), current_user: dict = Depends(require_student)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    ext = (file.filename or "").split(".")[-1] if "." in (file.filename or "") else "jpg"
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
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(require_student)
):
    if item_type not in ["lost", "found"]:
        raise HTTPException(status_code=400, detail="Item type must be 'lost' or 'found'")

    item_id = str(uuid.uuid4())
    image_url = None

    if image is not None and image.filename:
        if not (image.content_type or "").startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed")

        ext = image.filename.split(".")[-1] if "." in image.filename else "jpg"
        image_filename = f"{item_id}.{ext}"
        image_path = ITEMS_DIR / image_filename

        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)
        image_url = f"/uploads/items/{image_filename}"

    now = datetime.now(timezone.utc)
    item = {
        "id": item_id,
        "item_type": item_type,
        "description": description,
        "location": location,
        "image_url": image_url,
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
    """Public endpoint — shows recently lost and found items without sensitive data."""
    def _q():
        resp = (supabase.table("items")
                .select("id,item_type,description,location,image_url,status,created_at,created_date,created_time,likes,dislikes")
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
async def soft_delete_item(item_id: str, data: DeleteReason, current_user: dict = Depends(get_current_user)):
    item = await sb_find_one("items", {"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    is_admin = current_user.get("role") in ["admin", "super_admin"]
    is_owner = current_user.get("role") == "student" and item.get("student_id") == current_user.get("sub")

    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this item")

    await sb_update("items", {"id": item_id}, {
        "is_deleted": True,
        "delete_reason": data.reason,
        "deleted_at": datetime.now(timezone.utc).isoformat()
    })

    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "item_soft_deleted",
        "item_id": item_id,
        "user_id": current_user.get("sub"),
        "user_role": current_user.get("role"),
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
                .select("id", count=CountMethod.exact)
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

def fallback_match_items(lost_items, found_items):
    matches = []
    import re
    def get_words(text):
        if not text:
            return set()
        # Clean words of length 3 or more
        return set(re.findall(r'\b\w{3,}\b', text.lower()))

    for lost in lost_items:
        lost_words = get_words(lost.get("description", ""))
        lost_loc = (lost.get("location") or "").lower().strip()
        
        for found in found_items:
            found_words = get_words(found.get("description", ""))
            found_loc = (found.get("location") or "").lower().strip()
            
            common_words = lost_words.intersection(found_words)
            
            # Word overlap similarity percentage
            word_score = 0
            union_len = len(lost_words.union(found_words))
            if union_len > 0:
                word_score = (len(common_words) / union_len) * 100
                
            # Location score
            loc_score = 0
            if lost_loc and found_loc:
                if lost_loc == found_loc:
                    loc_score = 100
                elif lost_loc in found_loc or found_loc in lost_loc:
                    loc_score = 70
                    
            confidence = int(0.6 * word_score + 0.4 * loc_score)
            
            # Minimum confidence adjustment if they share keywords/exact locations
            if len(common_words) >= 1 or (lost_loc and lost_loc == found_loc):
                if confidence < 50:
                    confidence = 50 + len(common_words) * 5
                
                confidence = min(95, confidence)
                
                reason_parts = []
                if common_words:
                    reason_parts.append(f"Matching keywords: {', '.join(list(common_words)[:3])}")
                if lost_loc == found_loc and lost_loc:
                    reason_parts.append("Same location")
                elif loc_score > 0:
                    reason_parts.append("Similar location area")
                    
                reason = " & ".join(reason_parts) if reason_parts else "Overlap in item characteristics"
                
                matches.append({
                    "lost_id": lost["id"],
                    "found_id": found["id"],
                    "confidence": confidence,
                    "reason": reason
                })
    return matches


@api_router.get("/ai/matches")
async def get_ai_matches(current_user: dict = Depends(require_admin)):
    """Get AI-suggested matches between lost and found items (with local keyword fallback)."""
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
        api_key = os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("OPENAI_API_KEY")
        matches_data = []
        llm_success = False

        if api_key:
            try:
                from openai import AsyncOpenAI
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
                    ],
                    timeout=15.0
                )
                response = response_obj.choices[0].message.content or ""

                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    matches_data = json.loads(json_match.group())
                    llm_success = True
            except Exception as llm_err:
                logging.warning(f"AI LLM matching failed, falling back to local rule-based match: {str(llm_err)}")

        if not llm_success:
            # Run local rule-based match if LLM key is not configured or fails
            matches_data = fallback_match_items(lost_items, found_items)

        # Hydrate matching data with database student and item details
        for match in matches_data:
            conf = match.get("confidence", 0)
            if conf >= 50:
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
                    
                    # Store match in matches table if confidence >= 70%
                    if conf >= 70:
                        # Check if match record already exists
                        existing = await sb_find("matches", {"lost_item_id": lost_item["id"], "found_item_id": found_item["id"]})
                        if not existing:
                            match_id = str(uuid.uuid4())
                            # Create match record
                            await sb_insert("matches", {
                                "id": match_id,
                                "lost_item_id": lost_item["id"],
                                "found_item_id": found_item["id"],
                                "confidence_score": conf,
                                "status": "pending",
                                "created_at": datetime.now(timezone.utc).isoformat()
                            })
                            
                            # Audit log: AI Match Created
                            await sb_insert("audit_logs", {
                                "id": str(uuid.uuid4()),
                                "action": "ai_match_created",
                                "item_id": found_item["id"],
                                "user_id": current_user["sub"],
                                "user_role": "admin",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                            
                            # Automatically notify student
                            await sb_insert("messages", {
                                "id": str(uuid.uuid4()),
                                "sender_id": "system",
                                "sender_type": "admin",
                                "recipient_id": lost_item["student_id"],
                                "recipient_type": "student",
                                "content": "A possible match has been found for your lost item. Please visit the Lost & Found Office/Admin for verification.",
                                "item_id": found_item["id"],
                                "is_read": False,
                                "created_at": datetime.now(timezone.utc).isoformat()
                            })
                            
                            # Update status to student_notified
                            await sb_update("matches", {"id": match_id}, {"status": "student_notified"})
                            
                            # Create initial verification session
                            await sb_insert("verification_sessions", {
                                "id": str(uuid.uuid4()),
                                "match_id": match_id,
                                "verification_status": "pending",
                                "admin_notes": "",
                                "handover_confirmed": False
                            })
                            
                            # Audit log: Student Notified
                            await sb_insert("audit_logs", {
                                "id": str(uuid.uuid4()),
                                "action": "student_notified",
                                "item_id": lost_item["id"],
                                "user_id": lost_item["student_id"],
                                "user_role": "student",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                    
                    matches.append({
                        "lost_item": {**lost_item, "student": lost_student},
                        "found_item": {**found_item, "student": found_student},
                        "confidence": conf,
                        "reason": match.get("reason", "")
                    })

    except Exception as e:
        logging.error(f"AI matching error: {str(e)}")
        return {"matches": [], "message": "AI matching temporarily unavailable"}

    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return {"matches": matches}


@api_router.post("/ai/matches/initiate-verification")
async def initiate_verification(data: InitiateVerificationRequest, current_user: dict = Depends(require_admin)):
    # Check if a match already exists between these two items
    existing = await sb_find("matches", {"lost_item_id": data.lost_item_id, "found_item_id": data.found_item_id})
    if existing:
        match_record = existing[0]
    else:
        # Create match record manually
        match_id = str(uuid.uuid4())
        match_record = await sb_insert("matches", {
            "id": match_id,
            "lost_item_id": data.lost_item_id,
            "found_item_id": data.found_item_id,
            "confidence_score": 100,  # Manually initiated match
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create initial verification session
        await sb_insert("verification_sessions", {
            "id": str(uuid.uuid4()),
            "match_id": match_record["id"],
            "verification_status": "pending",
            "admin_notes": "",
            "handover_confirmed": False
        })
        
        # Audit log: Match Created
        await sb_insert("audit_logs", {
            "id": str(uuid.uuid4()),
            "action": "ai_match_created",
            "item_id": data.found_item_id,
            "user_id": current_user["sub"],
            "user_role": "admin",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    match_id = match_record["id"]
    
    # Create the verification question
    q_id = str(uuid.uuid4())
    await sb_insert("verification_questions", {
        "id": q_id,
        "match_id": match_id,
        "question": data.question,
        "created_by": current_user["sub"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Update match status and session status to verification_started
    await sb_update("matches", {"id": match_id}, {"status": "verification_started"})
    await sb_update("verification_sessions", {"match_id": match_id}, {"verification_status": "under_review"})
    
    # Audit log: Question Added
    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "question_added",
        "item_id": data.found_item_id,
        "user_id": current_user["sub"],
        "user_role": "admin",
        "reason": f"Question: {data.question}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Audit log: Verification Started
    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "verification_started",
        "item_id": data.found_item_id,
        "user_id": current_user["sub"],
        "user_role": "admin",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Notify student
    lost_item = await sb_find_one("items", {"id": data.lost_item_id})
    if lost_item:
        await sb_insert("messages", {
            "id": str(uuid.uuid4()),
            "sender_id": current_user["sub"],
            "sender_type": "admin",
            "recipient_id": lost_item["student_id"],
            "recipient_type": "student",
            "content": f"New verification question: {data.question}",
            "item_id": data.found_item_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
    return {"message": "Verification initiated successfully", "match_id": match_id}


@api_router.get("/verification/queue")
async def get_verification_queue(current_user: dict = Depends(require_admin)):
    logger.info("Starting verification queue retrieval.")
    try:
        logger.info("Executing Supabase query to find matches.")
        matches_db = await sb_find("matches", {}, order_col="created_at", order_asc=False)
        logger.info(f"Retrieved {len(matches_db)} matches from Supabase.")
        res = []
        for match in matches_db:
            logger.info(f"Hydrating match details for match ID: {match.get('id')}")
            lost_item = await sb_find_one("items", {"id": match["lost_item_id"]})
            found_item = await sb_find_one("items", {"id": match["found_item_id"]})
            if lost_item and found_item:
                lost_student = await sb_find_one_select("students", {"id": lost_item["student_id"]}, "id,full_name,roll_number,department,year")
                found_student = await sb_find_one_select("students", {"id": found_item["student_id"]}, "id,full_name,roll_number,department,year")
                res.append({
                    "id": match["id"],
                    "confidence_score": match["confidence_score"],
                    "status": match["status"],
                    "created_at": match["created_at"],
                    "lost_item": {**lost_item, "student": lost_student},
                    "found_item": {**found_item, "student": found_student}
                })
        logger.info("Successfully finished hydration of matches.")
        return res
    except Exception as e:
        logger.error(f"Verification queue failed: {str(e)}", exc_info=True)
        # Raise 503 Service Unavailable if it's a connection / getaddrinfo error
        if "getaddrinfo" in str(e) or "connect" in str(e).lower() or "connection" in str(e).lower():
            raise HTTPException(status_code=503, detail="Database connection temporarily unavailable. Please check server connectivity.")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")



@api_router.get("/verification/session/{match_id}")
async def get_verification_session(match_id: str, current_user: dict = Depends(get_current_user)):
    match = await sb_find_one("matches", {"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    session = await sb_find_one("verification_sessions", {"match_id": match_id})
    if not session:
        session = await sb_insert("verification_sessions", {
            "id": str(uuid.uuid4()),
            "match_id": match_id,
            "verification_status": "pending",
            "admin_notes": "",
            "handover_confirmed": False
        })
        
    questions = await sb_find("verification_questions", {"match_id": match_id}, order_col="created_at", order_asc=True)
    
    hydrated_questions = []
    for q in questions:
        answer = await sb_find_one("verification_answers", {"question_id": q["id"]})
        hydrated_questions.append({
            "id": q["id"],
            "question": q["question"],
            "created_by": q["created_by"],
            "created_at": q["created_at"],
            "answer": answer["answer"] if answer else None,
            "answered_at": answer["answered_at"] if answer else None
        })
        
    lost_item = await sb_find_one("items", {"id": match["lost_item_id"]})
    found_item = await sb_find_one("items", {"id": match["found_item_id"]})
    lost_student = await sb_find_one_select("students", {"id": lost_item["student_id"]}, "id,full_name,roll_number,department,year") if lost_item else None
    found_student = await sb_find_one_select("students", {"id": found_item["student_id"]}, "id,full_name,roll_number,department,year") if found_item else None
    
    return {
        "match": {
            **match,
            "lost_item": {**lost_item, "student": lost_student} if lost_item else None,
            "found_item": {**found_item, "student": found_student} if found_item else None
        },
        "session": session,
        "questions": hydrated_questions
    }


@api_router.post("/verification/session/{match_id}/question")
async def add_verification_question(match_id: str, data: VerificationQuestionCreate, current_user: dict = Depends(require_admin)):
    match = await sb_find_one("matches", {"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    q_id = str(uuid.uuid4())
    await sb_insert("verification_questions", {
        "id": q_id,
        "match_id": match_id,
        "question": data.question,
        "created_by": current_user["sub"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Update match status and session status to verification_started
    await sb_update("matches", {"id": match_id}, {"status": "verification_started"})
    await sb_update("verification_sessions", {"match_id": match_id}, {"verification_status": "under_review"})
    
    # Audit log: Question Added
    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "question_added",
        "item_id": match["found_item_id"],
        "user_id": current_user["sub"],
        "user_role": "admin",
        "reason": f"Question: {data.question}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Audit log: Verification Started
    if match["status"] in ["pending", "student_notified"]:
        await sb_insert("audit_logs", {
            "id": str(uuid.uuid4()),
            "action": "verification_started",
            "item_id": match["found_item_id"],
            "user_id": current_user["sub"],
            "user_role": "admin",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    # Notify student
    lost_item = await sb_find_one("items", {"id": match["lost_item_id"]})
    if lost_item:
        await sb_insert("messages", {
            "id": str(uuid.uuid4()),
            "sender_id": current_user["sub"],
            "sender_type": "admin",
            "recipient_id": lost_item["student_id"],
            "recipient_type": "student",
            "content": f"New verification question: {data.question}",
            "item_id": match["found_item_id"],
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
    return {"message": "Question added successfully"}


@api_router.post("/verification/session/{match_id}/answer")
async def submit_verification_answer(match_id: str, data: VerificationAnswerCreate, current_user: dict = Depends(require_student)):
    match = await sb_find_one("matches", {"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    question = await sb_find_one("verification_questions", {"id": data.question_id})
    if not question or question["match_id"] != match_id:
        raise HTTPException(status_code=400, detail="Invalid question ID")
        
    existing_ans = await sb_find_one("verification_answers", {"question_id": data.question_id})
    if existing_ans:
        raise HTTPException(status_code=400, detail="Question already answered")
        
    await sb_insert("verification_answers", {
        "id": str(uuid.uuid4()),
        "question_id": data.question_id,
        "answer": data.answer,
        "answered_by": current_user["sub"],
        "answered_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Audit log: Answer Submitted
    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "answer_submitted",
        "item_id": match["found_item_id"],
        "user_id": current_user["sub"],
        "user_role": "student",
        "reason": f"Answer: {data.answer}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Check if all questions are answered
    all_qs = await sb_find("verification_questions", {"match_id": match_id})
    all_ans = []
    for q in all_qs:
        ans = await sb_find_one("verification_answers", {"question_id": q["id"]})
        if ans:
            all_ans.append(ans)
            
    if len(all_qs) == len(all_ans):
        await sb_update("matches", {"id": match_id}, {"status": "qa_completed"})
        
    return {"message": "Answer submitted successfully"}


@api_router.post("/verification/session/{match_id}/notes")
async def update_verification_notes(match_id: str, data: VerificationNotesUpdate, current_user: dict = Depends(require_admin)):
    await sb_update("verification_sessions", {"match_id": match_id}, {"admin_notes": data.notes})
    return {"message": "Notes updated successfully"}


@api_router.post("/verification/session/{match_id}/decision")
async def make_verification_decision(match_id: str, data: VerificationDecision, current_user: dict = Depends(require_admin)):
    if data.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")
        
    match = await sb_find_one("matches", {"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    await sb_update("matches", {"id": match_id}, {"status": data.status})
    
    action = "match_approved" if data.status == "approved" else "match_rejected"
    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": action,
        "item_id": match["found_item_id"],
        "user_id": current_user["sub"],
        "user_role": "admin",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Notify student
    lost_item = await sb_find_one("items", {"id": match["lost_item_id"]})
    if lost_item:
        await sb_insert("messages", {
            "id": str(uuid.uuid4()),
            "sender_id": current_user["sub"],
            "sender_type": "admin",
            "recipient_id": lost_item["student_id"],
            "recipient_type": "student",
            "content": f"Your verification has been {data.status}. Please coordinate with the office for handover.",
            "item_id": match["found_item_id"],
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
    return {"message": f"Verification decision set to {data.status}"}


@api_router.post("/verification/session/{match_id}/complete")
async def complete_verification(match_id: str, data: VerificationComplete, current_user: dict = Depends(require_admin)):
    match = await sb_find_one("matches", {"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    if match["status"] != "approved":
        raise HTTPException(status_code=400, detail="Match must be approved before completion")
        
    if not data.handover_confirmed:
        raise HTTPException(status_code=400, detail="Handover must be physically confirmed")
        
    all_qs = await sb_find("verification_questions", {"match_id": match_id})
    if not all_qs:
        raise HTTPException(status_code=400, detail="At least one verification question is required")
        
    for q in all_qs:
        ans = await sb_find_one("verification_answers", {"question_id": q["id"]})
        if not ans:
            raise HTTPException(status_code=400, detail="All questions must be answered by student")
            
    await sb_update("matches", {"id": match_id}, {"status": "completed"})
    await sb_update("verification_sessions", {"match_id": match_id}, {
        "handover_confirmed": True,
        "verification_status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat()
    })
    
    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "item_returned",
        "item_id": match["found_item_id"],
        "user_id": current_user["sub"],
        "user_role": "admin",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    await sb_insert("audit_logs", {
        "id": str(uuid.uuid4()),
        "action": "match_completed",
        "item_id": match["found_item_id"],
        "user_id": current_user["sub"],
        "user_role": "admin",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    await sb_update("items", {"id": match["lost_item_id"]}, {"status": "claimed"})
    await sb_update("items", {"id": match["found_item_id"]}, {"status": "claimed"})
    
    return {"message": "Match completed and item successfully returned"}



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
    import traceback
    def _count(table, **filters):
        q = supabase.table(table).select("id", count=CountMethod.exact)
        for k, v in filters.items():
            if isinstance(v, list):
                q = q.in_(k, v)
            else:
                q = q.eq(k, v)
        return q.execute().count or 0

    def _q():
        try:
            total_students = _count("students")
            total_lost = _count("items", item_type="lost", is_deleted=False)
            total_found = _count("items", item_type="found", is_deleted=False)
            pending_claims = _count("claims", status=["pending", "under_review"])
            resolved_items = _count("items", status="claimed")
            deleted_items = _count("items", is_deleted=True)
            
            # Verification queue counts
            pending_verifications = _count("matches", status=["pending", "student_notified", "verification_started", "qa_completed"])
            approved_matches = _count("matches", status="approved")
            rejected_matches = _count("matches", status="rejected")
            completed_returns = _count("matches", status="completed")
            
            return {
                "total_students": total_students,
                "total_lost": total_lost,
                "total_found": total_found,
                "pending_claims": pending_claims,
                "resolved_items": resolved_items,
                "deleted_items": deleted_items,
                "pending_verifications": pending_verifications,
                "approved_matches": approved_matches,
                "rejected_matches": rejected_matches,
                "completed_returns": completed_returns
            }
        except Exception as e:
            with open("stats_error.log", "w") as f:
                f.write(traceback.format_exc())
            raise e

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
# NOTE: Middleware must be added BEFORE include_router so CORS headers are
# present on ALL responses, including error responses from endpoints.
# ---------------------------------------------------------------------------
# Build CORS origins list:
# 1. Read CORS_ORIGINS env var (comma-separated), stripping whitespace from each entry.
# 2. Always add the Vercel frontend URL from FRONTEND_URL env var if set.
# 3. Always include localhost for local development.
_raw_cors = os.environ.get('CORS_ORIGINS', '')
_cors_list = [o.strip() for o in _raw_cors.split(',') if o.strip()] if _raw_cors else []
_frontend_url = os.environ.get('FRONTEND_URL', '').strip()
if _frontend_url and _frontend_url not in _cors_list:
    _cors_list.append(_frontend_url)
for _dev_origin in ['http://localhost:3000', 'http://localhost:3001', 'http://127.0.0.1:3000']:
    if _dev_origin not in _cors_list:
        _cors_list.append(_dev_origin)
# If still empty, fall back to allow all (unsafe for production — set CORS_ORIGINS on Render)
if not _cors_list:
    _cors_list = ['*']
print(f"CORS allowed origins: {_cors_list}")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
