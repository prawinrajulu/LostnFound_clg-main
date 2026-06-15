# Excel Format Quick Reference

## EXACT FORMAT REQUIRED

### Column Headers (Case-Insensitive)

```
| A              | B         | C          | D    | E   | F     | G            |
|----------------|-----------|------------|------|-----|-------|--------------|
| Roll Number    | Full Name | Department | Year | DOB | Email | Phone Number |
```

### Data Format Rules

| Column | Format | Example | Notes |
|--------|--------|---------|-------|
| **Roll Number** | Numeric string | 112723205028 | Unique identifier, no decimals |
| **Full Name** | Text | Sam | Student's name |
| **Department** | Text | IT | Department code or name |
| **Year** | Numeric string | 3 | Academic year |
| **DOB** | DD-MM-YYYY | 17-04-2006 | **CRITICAL: Must be DD-MM-YYYY** |
| **Email** | Email format | sam@spcet.ac.in | Valid email address |
| **Phone Number** | Numeric string | 8925481638 | Phone number |

---

## Sample Excel File

```
Roll Number   | Full Name | Department | Year | DOB        | Email              | Phone Number
112723205028  | Sam       | IT         | 3    | 17-04-2006 | sam@spcet.ac.in    | 8925481638
112723205015  | Prawin    | IT         | 3    | 18-04-2006 | prawin@spcet.ac.in | 8925481639
112723205014  | Manoj     | IT         | 3    | 19-04-2006 | manoj@spcet.ac.in  | 8925481640
112723205013  | Majja     | IT         | 3    | 20-04-2006 | majja@spcet.ac.in  | 8925481641
```

---

## Python Script to Create Test File

```python
import pandas as pd

data = {
    "Roll Number": ["112723205028", "112723205015", "112723205014", "112723205013"],
    "Full Name": ["Sam", "Prawin", "Manoj", "Majja"],
    "Department": ["IT", "IT", "IT", "IT"],
    "Year": ["3", "3", "3", "3"],
    "DOB": ["17-04-2006", "18-04-2006", "19-04-2006", "20-04-2006"],
    "Email": ["sam@spcet.ac.in", "prawin@spcet.ac.in", "manoj@spcet.ac.in", "majja@spcet.ac.in"],
    "Phone Number": ["8925481638", "8925481639", "8925481640", "8925481641"]
}

df = pd.DataFrame(data)
df.to_excel("students.xlsx", index=False)
print("Excel file created successfully!")
```

---

## Common Mistakes to Avoid

❌ **Wrong DOB Format**
```
Bad:  2006-04-17 (YYYY-MM-DD)
Good: 17-04-2006 (DD-MM-YYYY)
```

❌ **Missing Columns**
```
Bad:  Skipping "Phone Number" column
Good: All 7 columns must be present
```

❌ **Wrong Column Names**
```
Bad:  "Roll No", "Name", "Birth Date"
Good: "Roll Number", "Full Name", "DOB"
```

❌ **Empty Rows**
```
Bad:  Empty rows between data
Good: Continuous data starting from row 2
```

---

## Upload Response Examples

### Successful Upload
```json
{
  "message": "Upload complete. Added: 4, Skipped (duplicates): 0",
  "added": 4,
  "skipped": 0,
  "errors": []
}
```

### With Duplicates
```json
{
  "message": "Upload complete. Added: 2, Skipped (duplicates): 2",
  "added": 2,
  "skipped": 2,
  "errors": []
}
```

### With Errors
```json
{
  "message": "Upload complete. Added: 3, Skipped (duplicates): 0",
  "added": 3,
  "skipped": 0,
  "errors": [
    "Row 5: Invalid DOB format. Expected DD-MM-YYYY, got: 2006-04-17"
  ]
}
```

---

## Student Login Format

**Input (JSON):**
```json
{
  "roll_number": "112723205028",
  "dob": "17-04-2006"
}
```

**Success Response:**
```json
{
  "token": "eyJhbG...",
  "user": {
    "roll_number": "112723205028",
    "full_name": "Sam",
    "dob": "17-04-2006",
    ...
  },
  "role": "student"
}
```

**Error Response:**
```json
{
  "detail": "Invalid credentials"
}
```

---

## DOB Format Examples

✅ **Valid Formats:**
- 17-04-2006
- 01-01-2005
- 31-12-2007

❌ **Invalid Formats:**
- 2006-04-17 (Wrong order)
- 17/04/2006 (Wrong separator)
- 17-4-2006 (Missing leading zero)
- April 17, 2006 (Text format)

---

## Testing Checklist

- [ ] Excel file has exactly 7 columns
- [ ] Column names match exactly (case-insensitive)
- [ ] DOB is in DD-MM-YYYY format
- [ ] Roll Numbers are unique
- [ ] No empty rows in data
- [ ] File extension is .xlsx or .xls
- [ ] Admin token is valid
- [ ] Backend server is running

---

## Quick Test Commands

### Upload Excel
```bash
curl -X POST http://localhost:8000/api/students/upload-excel \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@students.xlsx"
```

### Student Login
```bash
curl -X POST http://localhost:8000/api/auth/student/login \
  -H "Content-Type: application/json" \
  -d '{"roll_number": "112723205028", "dob": "17-04-2006"}'
```

### Get Students
```bash
curl -X GET http://localhost:8000/api/students \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

**REMEMBER: DOB format is DD-MM-YYYY everywhere!**
