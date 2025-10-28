# 📄 JSON Curriculum Support

## Overview

The scheduler now supports **JSON curriculum files** in addition to CSV files! This makes it easier to maintain and update course information using structured JSON format.

## ✨ New Features

### 1. **JSON Curriculum Files**
- Load complete curriculum from single JSON file
- Auto-converts to scheduler-compatible format
- Supports nested semester structure
- Includes elective courses

### 2. **Automatic Enrollment Generation**
- No separate enrollment file needed
- Generates realistic enrollment numbers
- Supports multiple blocks per year

### 3. **Smart Room Type Detection**
- Automatically determines required room types
- Based on course code and description
- Matches: networking, database, programming, systems, etc.

## 📋 JSON Format

### Basic Structure

```json
{
  "program": "Information Technology",
  "total_units": 152,
  "curriculum": {
    "first_year": {
      "first_semester": {
        "subjects": [...]
      },
      "second_semester": {
        "subjects": [...]
      }
    },
    "second_year": { ... },
    "third_year": { ... },
    "fourth_year": { ... }
  },
  "elective_courses": [...]
}
```

### Subject Format

```json
{
  "code": "IT 115",
  "description": "Networking 1",
  "lec": 2,
  "lab": 1,
  "units": 3,
  "prerequisite": "IT109"
}
```

**Fields:**
- `code`: Course code (e.g., "IT 115")
- `description`: Full course name
- `lec`: Lecture hours per week
- `lab`: Laboratory hours per week
- `units`: Credit units
- `prerequisite`: Prerequisites (optional)

## 🚀 How to Use

### Method 1: GUI (Easiest)

1. **Launch GUI**
   ```bash
   python scheduler_gui.py
   ```

2. **Select JSON File**
   - Click "Browse..." next to "Courses (CSV/JSON):"
   - Select your `.json` curriculum file
   - Example: `it_curriculum.json`

3. **Auto-Generated Enrollment**
   - Enrollment is automatically created from JSON
   - No need to select enrollment file
   - Default: 40 students per block (years 1-2), 35 (year 3), 25 (year 4)

4. **Select Rooms File**
   - Still need `room.csv` for room definitions
   - Use existing `room.csv`

5. **Run Optimization**
   - Click "▶ Run Optimization"
   - System auto-converts JSON → internal format
   - Schedules generated normally

### Method 2: Command Line

**Convert JSON to CSV first:**
```bash
python json_parser.py it_curriculum.json
```

**Output files:**
- `courses_from_json.csv` - Courses
- `enrollment_from_json.csv` - Enrollment

**Then run scheduler:**
```bash
python scheduler.py
```

### Method 3: Python Code

```python
from scheduler import SchedulingOptimizer

# Use JSON curriculum directly
optimizer = SchedulingOptimizer(
    courses_file='it_curriculum.json',  # JSON file!
    enrollment_file='it_curriculum.json',  # Same file
    rooms_file='room.csv'
)

optimizer.build_model()
optimizer.solve()
optimizer.export_all_schedules()
```

## 🎯 Room Type Detection

The system automatically assigns room types based on course characteristics:

| Course Contains | Assigned Room Type |
|----------------|-------------------|
| "network" | `networking` |
| "database" | `database` |
| "security", "cyber" | `security` |
| "mobile", "android" | `mobile_dev` |
| "web", "internet" | `web_dev` |
| "system admin" | `systems` |
| "programming" | `programming` |
| "graphic", "animation" | `multimedia` |
| Has lab hours | `programming` |
| None of above | `general` |

**Example:**
- "IT 115: Networking 1" → `networking`
- "IT 109: Database Systems" → `database`
- "IT 101: Programming 1" → `programming`

## 📊 Test Your JSON File

Run the test script to verify your JSON file:

```bash
python test_json.py
```

**Output:**
```
============================================================
TESTING JSON CURRICULUM PARSER
============================================================

📊 Curriculum Summary:
  Total Courses: 27
  Total Units: 152
  Courses by Year:
    Year 1: 5 courses
    Year 2: 7 courses
    Year 3: 12 courses
    Year 4: 3 courses

🏢 Courses by Room Type:
  programming: 17 courses
  networking: 2 courses
  database: 1 courses
  ...

✅ Conversion complete!
```

## 📁 Generated Files

When using JSON input, these files are auto-generated:

1. **`courses_from_json.csv`**
   ```csv
   code,name,program,year,lec_hours,lab_hours,room_type_required
   IT100,Introduction to Computing,IT,1,2,1,programming
   IT115,Networking 1,IT,3,2,1,networking
   ```

2. **`enrollment_from_json.csv`**
   ```csv
   program,year,block,students
   IT,1,A,40
   IT,1,B,40
   IT,3,A,35
   ```

## 🔧 Customizing Enrollment

To customize enrollment numbers, edit `scheduler.py`:

```python
def _generate_enrollment_from_json(self, json_file: str) -> pd.DataFrame:
    enrollment_data = [
        # Modify these numbers
        {'program': 'IT', 'year': 1, 'block': 'A', 'students': 50},  # Increase
        {'program': 'IT', 'year': 1, 'block': 'B', 'students': 45},
        # Add more blocks
        {'program': 'IT', 'year': 1, 'block': 'E', 'students': 40},
        # ...
    ]
    return pd.DataFrame(enrollment_data)
```

## 🎨 Creating Your Own JSON

### Template

```json
{
  "program": "Your Program Name",
  "total_units": 150,
  "curriculum": {
    "first_year": {
      "first_semester": {
        "subjects": [
          {
            "code": "COURSE101",
            "description": "Course Name",
            "lec": 3,
            "lab": 1,
            "units": 4,
            "prerequisite": "None"
          }
        ]
      },
      "second_semester": {
        "subjects": []
      }
    }
  },
  "elective_courses": []
}
```

### Best Practices

1. **Use consistent formatting**
   - 2-space indentation
   - Clear structure

2. **Course codes**
   - No spaces: Use "IT115" or "IT 115"
   - System removes spaces automatically

3. **Prerequisites**
   - Use "None" for none
   - Comma-separated for multiple

4. **Lab hours**
   - 0 for lecture-only courses
   - 1-3 for regular labs
   - 486 for practicum (special case)

## 💡 Example: Complete Curriculum

See `it_curriculum.json` for a complete example covering:
- ✅ All 4 years
- ✅ Both semesters
- ✅ Core courses
- ✅ Elective courses
- ✅ Various room types
- ✅ Prerequisites

## 🔄 CSV vs JSON Comparison

| Feature | CSV | JSON |
|---------|-----|------|
| **Structure** | Flat table | Nested hierarchy |
| **Files** | 3 files (courses, enrollment, rooms) | 1-2 files (JSON + rooms) |
| **Editing** | Excel, any editor | Text editor, JSON tools |
| **Enrollment** | Manual creation | Auto-generated |
| **Prerequisites** | Not included | Included |
| **Maintenance** | Update 3 files | Update 1 file |
| **Semester info** | Not preserved | Preserved |

## 🎯 When to Use JSON

**Use JSON when:**
- ✅ Managing complete curriculum
- ✅ Want structured data
- ✅ Need version control friendly format
- ✅ Don't want to maintain separate enrollment
- ✅ Want to preserve semester information

**Use CSV when:**
- ✅ Quick testing
- ✅ Excel-based workflows
- ✅ Need precise enrollment control
- ✅ Simpler requirements

## 🐛 Troubleshooting

### JSON Parse Error

**Error:** `Expecting value: line 1 column 1`

**Solution:**
- Check file is valid JSON
- Use JSON validator: https://jsonlint.com
- Ensure proper encoding (UTF-8)
- No trailing commas

### Room Type Issues

**Problem:** Courses assigned to wrong room types

**Solution:**
- Modify `_determine_room_type()` in `json_parser.py`
- Add custom keywords
- Or specify room types manually in CSV

### Missing Courses

**Problem:** Some courses not appearing

**Solution:**
- Check JSON structure matches format
- Verify all semesters have "subjects" array
- Ensure electives in "elective_courses" array

## 📈 Performance

**JSON parsing is fast:**
- 27 courses: < 0.1 seconds
- 100+ courses: < 0.5 seconds
- Negligible overhead vs CSV

## 🎉 Benefits

### For Administrators
- ✅ Single source of truth
- ✅ Easier curriculum updates
- ✅ Version control friendly
- ✅ No enrollment file maintenance

### For Developers
- ✅ Structured data
- ✅ Easy to parse
- ✅ Extensible format
- ✅ Better for APIs

### For Research
- ✅ Preserve curriculum structure
- ✅ Document prerequisites
- ✅ Track semester organization
- ✅ Easier data analysis

## 📚 Files Created

New files for JSON support:

1. **`json_parser.py`** (new)
   - Parses JSON curriculum
   - Converts to scheduler format
   - Auto-generates enrollment

2. **`scheduler.py`** (updated)
   - Supports JSON input
   - Auto-detects file type
   - Seamless integration

3. **`scheduler_gui.py`** (updated)
   - JSON file selection
   - Auto-enrollment handling
   - Enhanced validation

4. **`test_json.py`** (new)
   - Test JSON files
   - Verify conversion
   - Debug tool

5. **`it_curriculum.json`** (example)
   - Sample curriculum
   - Complete structure
   - Ready to use

## ✅ Ready to Use!

Your scheduler now supports both CSV and JSON files seamlessly!

**Quick Start:**
1. Use `it_curriculum.json` as template
2. Launch GUI: `python scheduler_gui.py`
3. Select JSON file
4. Run optimization
5. Get schedules!

---

**Questions? Check the main README.md or GUI_GUIDE.md**
