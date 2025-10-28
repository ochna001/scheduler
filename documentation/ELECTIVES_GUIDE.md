# 🗳️ Elective Configuration Guide

## Problem: Too Many Electives = Infeasible

When the scheduler tries to schedule **all possible electives**, it becomes **infeasible** because:
- Year 3 has 12+ elective options (IT 129-140)
- But students only take 2-4 electives
- Not enough time slots to fit everything

**Result:** `Status: Infeasible` ❌

## Solution: Configure Based on Voting

In CCMS, students **vote** on which electives they want. The elective with the most votes gets scheduled for that block.

### How It Works

1. **Placeholder slots** in curriculum (ITELECT 001, 002, 003, 004)
2. **Students vote** on specific electives (IT 129-140)
3. **Winning electives** replace placeholders
4. **Scheduler** generates feasible schedule ✅

## 📋 Workflow

### Step 1: Generate Base Courses from JSON

```bash
python test_json.py
```

**Output:** `courses_from_json.csv`
- Contains core courses
- Contains placeholder electives (ITELECT 001, 002, etc.)
- **Does NOT contain** IT 129-140 (specific electives)

### Step 2: Conduct Student Voting

For each block (IT3A, IT3B, IT3C, etc.):

**Example Ballot:**
```
Which electives do you want for this semester?
Vote for your top 2 choices:

□ IT 129 - Integrative Programming 2
□ IT 130 - Platform Technologies
□ IT 131 - Web Systems
□ IT 135 - Game Programming
□ IT 138 - Computer Graphics
□ IT 139 - Artificial Intelligence
□ IT 140 - Data Mining
```

**Results:**
- IT3A: IT 139 (AI) - 32 votes, IT 135 (Game) - 28 votes
- IT3B: IT 140 (Data Mining) - 30 votes, IT 131 (Web) - 25 votes

### Step 3: Configure Electives

Run the configuration tool:

```bash
python configure_electives.py
```

**Example Output:**
```
🗳️ Example Voting Results:

IT3A voted for:
  Slot 1 (ITELECT001): IT139 - Introduction to AI
  Slot 2 (ITELECT002): IT135 - Game Programming

IT3B voted for:
  Slot 1 (ITELECT001): IT140 - Data Mining
  Slot 2 (ITELECT002): IT131 - Web Systems

✓ Generated courses with electives: courses_with_electives.csv
```

### Step 4: Run Scheduler

Use the configured courses file:

**In GUI:**
1. Launch: `python scheduler_gui.py`
2. Select `courses_with_electives.csv` (not courses_from_json.csv)
3. Select `enrollment_from_json.csv`
4. Select `room.csv`
5. Run optimization ✅

**Result:** Feasible schedule with voted electives!

## 🔧 Manual Configuration

You can also manually edit `courses_from_json.csv`:

### Before (Placeholder):
```csv
code,name,program,year,lec_hours,lab_hours,room_type_required
ITELECT001,IT Elective 1,IT,3,3,0,general
ITELECT002,IT Elective 2,IT,3,2,1,programming
```

### After (IT3A's voted choices):
```csv
code,name,program,year,lec_hours,lab_hours,room_type_required
IT139,Introduction to Artificial Intelligence,IT,3,3,0,general
IT135,Game Programming,IT,3,2,1,programming
```

## 📊 Course Distribution

### Realistic Year 3 Schedule

**Core Courses (10):**
- IT 114 - Quantitative Methods
- IT 115 - Networking 1
- IT 116 - Systems Analysis
- IT 117 - Systems Admin
- IT 118 - IoT
- IT 119 - Data Analytics
- IT 120 - Networking 2
- IT 121 - Capstone 1
- IT 122 - Systems Integration
- IT 123 - Security 2

**Voted Electives (2):**
- ITELECT 001 → Student-chosen elective
- ITELECT 002 → Student-chosen elective

**Total: 12 courses** ✅ Feasible!

## 🎯 Elective Options

### 3rd Year Electives
| Code | Name | Lec | Lab |
|------|------|-----|-----|
| IT 129 | Integrative Programming 2 | 2 | 1 |
| IT 130 | Platform Technologies | 2 | 1 |
| IT 131 | Web Systems | 2 | 1 |
| IT 132 | Object-Oriented Programming | 2 | 1 |
| IT 133 | Systems Integration 2 | 2 | 1 |
| IT 134 | HCI 2 | 2 | 1 |
| IT 135 | Game Programming | 2 | 1 |
| IT 137 | IT Trends Seminar | 3 | 0 |
| IT 138 | Computer Graphics | 2 | 1 |
| IT 139 | Artificial Intelligence | 3 | 0 |
| IT 140 | Data Mining | 3 | 0 |

### 4th Year Electives
| Code | Name | Lec | Lab |
|------|------|-----|-----|
| IT 136 | Enterprise Architecture | 2 | 1 |
| IT 137 | IT Trends Seminar | 3 | 0 |

## 💡 Pro Tips

### Different Blocks, Different Electives

**This is perfectly fine:**
- IT3A: AI + Game Programming
- IT3B: Data Mining + Web Systems
- IT3C: Graphics + Platform Tech

The scheduler handles this automatically!

### Changing Electives Semester to Semester

**First Semester:**
- IT3A elects: IT 139, IT 135

**Second Semester:**
- Same IT3A elects: IT 140, IT 131

Just update the CSV before running scheduler for the new semester.

### Handling Ties in Voting

If two electives tie:
1. **Faculty decides** which fits better with:
   - Available rooms
   - Faculty expertise
   - Lab availability
2. **Offer both** if demand is high (split blocks)
3. **Alternate semesters**

## 🚀 Quick Start Example

```python
# 1. Parse curriculum
python test_json.py
# → Creates courses_from_json.csv with placeholders

# 2. Configure based on voting
python configure_electives.py
# → Creates courses_with_electives.csv with actual electives

# 3. Run scheduler
python scheduler_gui.py
# → Load courses_with_electives.csv
# → Generate feasible schedule!
```

## ❓ FAQ

### Q: Can students choose any electives?
**A:** They vote from the available pool, but only the top-voted ones get scheduled.

### Q: What if a block wants 3 electives?
**A:** Add ITELECT 003 to the semester in JSON, then configure it.

### Q: Can we offer the same elective to multiple blocks?
**A:** Yes! If IT3A and IT3B both vote for IT 139, both get it (separate sections).

### Q: What if we don't know voting results yet?
**A:** Use the placeholder courses_from_json.csv to generate a "template schedule", then update later.

## 📈 Benefits of This Approach

✅ **Realistic schedules** - Only courses actually offered
✅ **Student choice** - Majority voting honored
✅ **Flexible** - Different blocks can have different electives
✅ **Feasible** - Doesn't overload the schedule
✅ **Maintainable** - Easy to update each semester

---

**This is how CCMS actually works!** 🎓
