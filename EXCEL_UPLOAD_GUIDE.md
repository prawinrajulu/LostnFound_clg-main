# Excel Upload Test Guide

## Creating Test Excel Files

### Sample Excel Structure
The Excel file must contain the following columns in this exact order:
- Roll Number
- Full Name
- Department
- Year
- DOB (format: YYYY-MM-DD)
- Email
- Phone Number

### Python Script to Create Test Excel

```python
import pandas as pd

# Test Case 1: New Students
data1 = {
    "Roll Number": ["CS101", "CS102", "CS103"],
    "Full Name": ["Student One", "Student Two", "Student Three"],
    "Department": ["Computer Science", "Information Technology", "Electronics"],
    "Year": ["2024", "2023", "2024"],
    "DOB": ["2002-01-15", "2001-06-20", "2002-09-10"],
    "Email": ["student1@spcet.ac.in", "student2@spcet.ac.in", "student3@spcet.ac.in"],
    "Phone Number": ["9876543210", "9876543211", "9876543212"]
}

df1 = pd.DataFrame(data1)
df1.to_excel("new_students.xlsx", index=False)
print("Created: new_students.xlsx")

# Test Case 2: Mixed (New + Duplicates)
data2 = {
    "Roll Number": ["CS101", "CS104", "CS105"],  # CS101 is duplicate
    "Full Name": ["Student One Duplicate", "Student Four", "Student Five"],
    "Department": ["Computer Science", "IT", "Electronics"],
    "Year": ["2024", "2023", "2024"],
    "DOB": ["2002-01-15", "2001-08-25", "2002-11-30"],
    "Email": ["duplicate@spcet.ac.in", "student4@spcet.ac.in", "student5@spcet.ac.in"],
    "Phone Number": ["9999999999", "9876543214", "9876543215"]
}

df2 = pd.DataFrame(data2)
df2.to_excel("mixed_students.xlsx", index=False)
print("Created: mixed_students.xlsx")
```

## Testing Excel Upload via cURL

### Step 1: Get Admin Token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin", "password": "SuperAdmin@123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
```

### Step 2: Upload Excel File
```bash
curl -X POST http://localhost:8000/api/students/upload-excel \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@new_students.xlsx"
```

**Expected Response:**
```json
{
  "message": "Upload complete. Added: 3, Skipped (duplicates): 0",
  "added": 3,
  "skipped": 0,
  "errors": []
}
```

### Step 3: Upload File with Duplicates
```bash
curl -X POST http://localhost:8000/api/students/upload-excel \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@mixed_students.xlsx"
```

**Expected Response:**
```json
{
  "message": "Upload complete. Added: 2, Skipped (duplicates): 1",
  "added": 2,
  "skipped": 1,
  "errors": []
}
```

### Step 4: Verify Students List
```bash
curl -s -X GET http://localhost:8000/api/students \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

## Testing Excel Upload via Frontend

### Step 1: Admin Login
1. Navigate to: `http://localhost:3000/admin/login`
2. Enter credentials:
   - Username: `superadmin`
   - Password: `SuperAdmin@123`
3. Click "Login"

### Step 2: Navigate to Students Page
1. Click "Students" in the sidebar
2. You should see the students management page

### Step 3: Upload Excel File
1. Look for "Upload Excel" or "Import Students" button
2. Click the button
3. Select your Excel file
4. Wait for upload to complete
5. Check the success message:
   - Should show: "Added: X, Skipped: Y"
   - Should display updated students list

### Step 4: Verify Results
1. Check the students table
2. New students should appear in the list
3. Existing students should remain unchanged
4. Total count should increase by the number of new students added

## Duplicate Prevention Rules

### How Duplicates are Detected
- **Primary Key:** Roll Number
- **Check:** Database query for existing roll number before insert
- **Action:** Skip insertion and increment skipped counter

### Example Scenarios

**Scenario 1: All New Students**
- Upload: CS101, CS102, CS103
- Database: (empty)
- Result: Added 3, Skipped 0

**Scenario 2: All Duplicates**
- Upload: CS101, CS102, CS103
- Database: CS101, CS102, CS103
- Result: Added 0, Skipped 3

**Scenario 3: Mixed**
- Upload: CS101, CS102, CS104
- Database: CS101, CS103
- Result: Added 2 (CS102, CS104), Skipped 1 (CS101)

**Scenario 4: Same Roll Number Multiple Times in Excel**
- Upload: CS101, CS102, CS101
- Database: (empty)
- Result: Added 2 (CS101 first occurrence, CS102), Skipped 1 (CS101 second occurrence)

## Error Handling

### Invalid Excel Format
**Problem:** Missing required columns
**Response:**
```json
{
  "detail": "Missing columns: DOB, Email"
}
```

### Invalid Date Format
**Problem:** DOB in wrong format
**Result:** Row-level error in errors array
**Response:**
```json
{
  "message": "Upload complete. Added: 2, Skipped: 0",
  "added": 2,
  "skipped": 0,
  "errors": ["Row 3: Invalid date format"]
}
```

### Empty Excel File
**Problem:** Excel file with no data rows
**Response:**
```json
{
  "message": "Upload complete. Added: 0, Skipped: 0",
  "added": 0,
  "skipped": 0,
  "errors": []
}
```

## Database Schema

### Student Document Structure
```json
{
  "id": "uuid-string",
  "roll_number": "CS101",
  "full_name": "Student Name",
  "department": "Computer Science",
  "year": "2024",
  "dob": "2002-01-15",
  "email": "student@spcet.ac.in",
  "phone_number": "9876543210",
  "profile_picture": null,
  "admin_notes": [],
  "created_at": "2025-01-11T05:30:05.441732+00:00"
}
```

### Important Notes
- `id`: Auto-generated UUID (not roll number)
- `roll_number`: Unique identifier for duplicate detection
- `dob`: Stored as string in YYYY-MM-DD format
- `created_at`: ISO format timestamp with timezone

## Best Practices

### Excel File Preparation
1. ✅ Use first row for column headers
2. ✅ Match column names exactly (case-sensitive)
3. ✅ Use YYYY-MM-DD format for dates
4. ✅ Remove empty rows at the end
5. ✅ Ensure roll numbers are unique within the file
6. ✅ Use .xlsx or .xls file format

### Data Entry Guidelines
1. Roll Number: Alphanumeric, no special characters
2. Full Name: Complete name with proper capitalization
3. Department: Full department name
4. Year: 4-digit year (2024, 2023, etc.)
5. DOB: Must be YYYY-MM-DD format
6. Email: Valid email format
7. Phone Number: Numeric, 10 digits recommended

## Troubleshooting

### Upload Fails
1. Check file format (.xlsx or .xls)
2. Verify all required columns are present
3. Check admin authentication token
4. Verify backend server is running

### All Students Skipped
- This means all roll numbers already exist in database
- This is EXPECTED behavior for duplicate prevention
- Check existing students before uploading

### Some Rows Have Errors
- Check the errors array in response
- Fix the problematic rows in Excel
- Re-upload the corrected file

### Students Not Appearing in UI
1. Refresh the page
2. Check browser console for errors
3. Verify API call succeeded
4. Check backend logs

## Testing Checklist

- [ ] Create test Excel file with proper format
- [ ] Upload file with all new students (should add all)
- [ ] Upload same file again (should skip all)
- [ ] Create file with mix of new and existing students
- [ ] Upload mixed file (should add new, skip existing)
- [ ] Verify correct counts in response message
- [ ] Verify students appear in UI
- [ ] Verify database contains correct data
- [ ] Test with invalid Excel format (should show error)
- [ ] Test delete student functionality
- [ ] Verify deleted student cannot be logged in
- [ ] Re-upload deleted student (should add successfully)

## Complete Test Workflow

```bash
# 1. Create test files
python3 create_test_excel.py

# 2. Get admin token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin", "password": "SuperAdmin@123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

# 3. Check initial count
echo "Initial students:"
curl -s -X GET http://localhost:8000/api/students \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"

# 4. Upload first file
echo "Uploading new students..."
curl -s -X POST http://localhost:8000/api/students/upload-excel \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@new_students.xlsx"

# 5. Check count after first upload
echo "\nStudents after first upload:"
curl -s -X GET http://localhost:8000/api/students \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"

# 6. Upload file with duplicates
echo "\nUploading mixed students (with duplicates)..."
curl -s -X POST http://localhost:8000/api/students/upload-excel \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@mixed_students.xlsx"

# 7. Final count
echo "\nFinal student count:"
curl -s -X GET http://localhost:8000/api/students \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"
```

## Expected Output
```
Initial students:
4

Uploading new students...
{"message":"Upload complete. Added: 3, Skipped (duplicates): 0","added":3,"skipped":0,"errors":[]}

Students after first upload:
7

Uploading mixed students (with duplicates)...
{"message":"Upload complete. Added: 2, Skipped (duplicates): 1","added":2,"skipped":1,"errors":[]}

Final student count:
9
```

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-11  
**Status:** Tested and Verified ✅
