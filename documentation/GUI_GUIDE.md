# 🎓 Classroom Scheduling Optimizer - GUI Guide

## Overview

The GUI application provides an intuitive interface for the classroom scheduling optimization system. No coding required - just select your files, click a button, and view the optimized schedules!

## ✨ Features

### 1. **File Selection** 📁
- Browse and select input CSV files
- One-click load default files
- Visual confirmation of selected files

### 2. **Live Progress Tracking** ⚙️
- Real-time optimization progress
- Animated progress bar
- Detailed status log with timestamps
- Performance metrics display

### 3. **Interactive Results Table** 📊
- Sortable columns (click headers)
- Filter by program/year/block
- View all course schedules in one place
- Professional table layout

### 4. **Export Functionality** 💾
- Export all schedules to CSV files
- Choose output directory
- Batch export for all combinations

## 🚀 How to Use

### Step 1: Launch the GUI

```bash
python scheduler_gui.py
```

The application window will open with:
- Title: "Classroom Scheduling Optimizer"
- Input file section
- Control buttons
- Progress display
- Results table

### Step 2: Select Input Files

**Option A: Browse for Files**
1. Click **"Browse..."** next to each file field
2. Navigate to your CSV files
3. Select:
   - `courses.csv` - Course definitions
   - `enrollment.csv` - Student enrollment
   - `room.csv` - Available rooms

**Option B: Load Default Files**
1. Click **"📂 Load Default Files"** button
2. Automatically loads files from current directory
3. Check status log for confirmation

### Step 3: Run Optimization

1. Click **"▶ Run Optimization"** button
2. Watch the progress:
   - Progress bar animates
   - Status log shows real-time updates
   - Model building progress
   - Solver progress
   - Performance metrics

**What happens:**
- Reads input files
- Builds BILP model (37,944+ binary variables)
- Solves using CBC Branch-and-Bound
- Generates all schedules
- Displays results in table

### Step 4: View Results

**Results Table:**
- **Columns**:
  - Course Code
  - Course Title
  - Time (slot)
  - Days (M, T, W, TH, F, S)
  - Room
  - Lecture Hours
  - Lab Hours
  - Units
  - Instructor
  - Program-Year-Block

**Sorting:**
- Click any column header to sort
- Click again to reverse sort

**Filtering:**
1. Use dropdown: "Filter by:"
2. Select specific program-year-block (e.g., IT3A)
3. Or choose "All Schedules"
4. Summary shows count of displayed schedules

### Step 5: Export Schedules

1. Click **"💾 Export All Schedules"** button
2. Choose output directory
3. CSV files generated for each program-year-block:
   - `schedule_IT1A.csv`
   - `schedule_IT1B.csv`
   - `schedule_IT3A.csv`
   - etc.

### Additional Controls

**⏹ Stop Button:**
- Stops optimization in progress (if needed)
- Enabled only during optimization

**🗑️ Clear Results:**
- Clears the results table
- Resets the interface
- Ready for new optimization

## 📋 GUI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🎓 Classroom Scheduling Optimizer                          │
│  Binary Integer Linear Programming - CCMS Optimization     │
├─────────────────────────────────────────────────────────────┤
│  📁 Input Files                                             │
│  Courses CSV:    [___________________] [Browse...]          │
│  Enrollment CSV: [___________________] [Browse...]          │
│  Rooms CSV:      [___________________] [Browse...]          │
│                [📂 Load Default Files]                      │
├─────────────────────────────────────────────────────────────┤
│  [▶ Run Optimization] [⏹ Stop] [💾 Export] [🗑️ Clear]     │
├─────────────────────────────────────────────────────────────┤
│  ⚙️ Optimization Progress                                   │
│  [================Progress Bar================]             │
│  ┌─────────────────────────────────────────────┐           │
│  │ Status Log (Real-time updates)              │           │
│  │ Building model...                           │           │
│  │ Solving optimization...                     │           │
│  └─────────────────────────────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│  📊 Generated Schedules                                     │
│  Filter by: [All Schedules ▼]                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Course │ Title │ Time │ Days │ Room │ ... │           │ │
│  │ IT114  │ QM    │ 7:00 │ MTH  │ NB-3 │     │           │ │
│  │ IT115  │ Net 1 │ 7:00 │ TW   │ NB-1 │     │           │ │
│  └───────────────────────────────────────────────────────┘ │
│  Total: 62 course schedules loaded                          │
├─────────────────────────────────────────────────────────────┤
│  Ready to optimize schedules              14:30:45         │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 Visual Features

### Color Coding
- **Title**: Bold, large font
- **Status Log**: Dark theme (code editor style)
- **Progress Bar**: Animated during optimization
- **Table**: Alternating row colors (auto)

### Real-Time Updates
- Progress bar animates during solving
- Status log scrolls automatically
- Timestamps in status bar
- Live metrics display

### User Feedback
- ✓ Success checkmarks
- ❌ Error indicators
- 📊 Data icons
- ⚙️ Process indicators

## 📊 Status Log Example

```
============================================================
CLASSROOM SCHEDULING OPTIMIZATION
============================================================

📂 Loading input files...

🔧 Building optimization model...
   Classes: 62
   Rooms: 12
   Time slots: 51
   Binary variables: 37944

⚙️ Solving optimization problem...
   Solver: CBC (Branch-and-Bound)
   Time limit: 600 seconds

============================================================
OPTIMIZATION RESULTS
============================================================
Status: Optimal
Solve time: 2.28 seconds
Objective value: 18.5824

📊 Performance Metrics:
   Room Utilization: 30.4%
   Idle Time: 69.6%
   IT Program: 100.0%
   IS Program: 0.0%
   Total Assignments: 186

📋 Loading schedules into table...
   ✓ 62 course schedules loaded
```

## 🎯 Key Benefits

### For Users:
- ✅ **No coding required** - Point and click interface
- ✅ **Visual feedback** - See progress in real-time
- ✅ **Easy data exploration** - Sort, filter, search schedules
- ✅ **Quick exports** - One-click CSV generation

### For Administrators:
- ✅ **Fast workflow** - Minutes instead of hours
- ✅ **Reproducible** - Same inputs = same results
- ✅ **Flexible** - Easy to update input files
- ✅ **Professional** - Publication-ready outputs

## 🔧 Technical Details

### Threading
- Optimization runs in separate thread
- GUI remains responsive during solving
- Can monitor progress without freezing

### Data Display
- Efficient treeview widget
- Handles hundreds of schedules
- Smooth scrolling
- Fast filtering

### Error Handling
- Validates all inputs
- Clear error messages
- Graceful failure recovery
- Detailed error logging

## 💡 Tips & Tricks

### Performance Tips
1. **Close other applications** for faster solving
2. **Use default files** for quick testing
3. **Filter results** for easier viewing
4. **Export early** - save results before closing

### Data Tips
1. **Verify CSV format** before loading
2. **Check room types** match course requirements
3. **Ensure enrollment numbers** are realistic
4. **Validate course hours** (lec + lab)

### Display Tips
1. **Maximize window** for better table view
2. **Sort by Time** to see schedule blocks
3. **Filter by program** to focus on specific schedules
4. **Read status log** for detailed insights

## 🐛 Troubleshooting

### GUI Won't Start
```bash
# Check Python version
python --version  # Should be 3.9+

# Reinstall dependencies
pip install pulp pandas openpyxl numpy
```

### Files Won't Load
- Check file paths are correct
- Verify files exist in directory
- Ensure CSV format is valid
- Look for error messages in log

### Optimization Fails
- Check status log for error details
- Verify input data is complete
- Ensure room capacities > enrollment
- Check course requirements match room types

### Table Shows No Data
- Verify optimization completed successfully
- Check filter dropdown (might be filtered)
- Look for "Total: X schedules" message
- Try clicking "Clear Results" and re-run

## 🎓 Example Workflow

**Complete workflow example:**

1. **Launch GUI**
   ```bash
   python scheduler_gui.py
   ```

2. **Load files**
   - Click "Load Default Files"
   - Status shows: "✓ Default files loaded"

3. **Run optimization**
   - Click "▶ Run Optimization"
   - Watch progress bar
   - Read status updates
   - Wait 2-5 minutes

4. **View results**
   - 62 schedules loaded
   - Sort by "Program-Year-Block"
   - Filter to "IT3A"
   - See 7 courses for IT3A

5. **Export**
   - Click "💾 Export All Schedules"
   - Choose folder
   - 23 CSV files created

6. **Done!**
   - Schedules ready for use
   - Can re-run with new data
   - Or close application

## 📈 Performance Expectations

### Typical Run Time
- Small dataset (50 classes): **1-2 seconds**
- Medium dataset (100 classes): **2-5 seconds**
- Large dataset (200 classes): **5-10 minutes**

### Memory Usage
- GUI: ~50 MB
- Solver: ~200-500 MB during optimization
- Results table: ~10 MB per 1000 schedules

### File Sizes
- Input CSVs: < 1 MB each
- Output CSVs: ~5-20 KB each
- Total exports: < 1 MB for all schedules

## 🎉 Success Indicators

**You'll know it worked when:**
- ✅ Status shows "Optimal"
- ✅ Solve time displayed
- ✅ Performance metrics shown
- ✅ Table populated with schedules
- ✅ Export button enabled
- ✅ No error messages

## 📚 Next Steps

After successful optimization:

1. **Review Schedules**
   - Check for reasonableness
   - Verify room assignments
   - Validate time slots

2. **Export Data**
   - Save CSV files
   - Share with stakeholders
   - Import to other systems

3. **Iterate**
   - Adjust input data
   - Re-run optimization
   - Compare results

4. **Customize**
   - Modify objective weights in `scheduler.py`
   - Add constraints
   - Adjust time slots

## 🆘 Support

For issues or questions:
- Check status log for error details
- Review input CSV formats
- Verify all dependencies installed
- Consult README.md for technical details

---

**Enjoy your optimized schedules! 🎓📊✨**
