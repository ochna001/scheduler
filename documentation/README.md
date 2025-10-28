# Classroom Scheduling Optimization System

Binary Integer Linear Programming implementation for optimal classroom space allocation.

## Overview

This software implements the mathematical model from the research paper: *"Modelling and Simulating Classroom Space Allocation in CCMS New Building and Old Laboratory: A Binary Integer Linear Programming Approach"*

### Mathematical Model

- **Decision Variables**: X_ijk (binary) = 1 if class i assigned to room j at time slot k
- **Variables**: 99,360+ binary variables (classes × rooms × time slots)
- **Objective Function**: Maximize Z = αU - βC - γI + δF
  - U = Room utilization (weight: 0.4)
  - C = Scheduling conflicts (weight: 0.3)
  - I = Idle time (weight: 0.2)
  - F = Program fairness (weight: 0.1)

### Constraints

1. **Assignment Constraint**: Each class assigned required hours
2. **Capacity Constraint**: Room capacity not exceeded
3. **No Double-Booking**: One class per room per time slot
4. **Room Type Matching**: Classes assigned to compatible rooms
5. **Contiguity Preference**: Multi-hour classes prefer consecutive slots

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Setup

1. Install required packages:
```bash
pip install -r requirements.txt
```

This installs:
- PuLP 2.7.0 (optimization modeling)
- Pandas 1.5.3 (data processing)
- OpenPyXL 3.1.2 (Excel support)
- NumPy (numerical computing)

## Input Files

The system requires three CSV input files:

### 1. courses.csv
Defines courses with room requirements.

**Columns**:
- `code`: Course code (e.g., IT100)
- `name`: Course name
- `program`: Program (IT/IS)
- `year`: Year level (1-4)
- `lec_hours`: Lecture hours per week
- `lab_hours`: Laboratory hours per week
- `room_type_required`: Required room type (programming, database, networking, etc.)

### 2. enrollment.csv
Student enrollment by program/year/block.

**Columns**:
- `program`: Program name (IT/IS)
- `year`: Year level
- `block`: Block section (A, B, C, etc.)
- `students`: Number of students

### 3. room.csv
Available rooms and their specifications.

**Columns**:
- `room_id`: Room identifier
- `building`: Building name
- `floor`: Floor number
- `capacity`: Maximum students
- `room_type`: Room type (matches course requirements)
- `equipment`: Equipment description

## Usage

### Basic Usage

Run the optimizer:
```bash
python scheduler.py
```

This will:
1. Read input CSV files
2. Build the optimization model
3. Solve using CBC (Branch-and-Bound algorithm)
4. Generate schedule CSV files for all program-year-block combinations

### Output Files

The system generates schedules in CSV format matching the example files:

**Output format**:
- `Course Code`: Course identifier
- `Course Title`: Full course name
- `Time`: Time slot (e.g., "8:00 - 11:00")
- `Days`: Days of week (MW, TTH, F, S)
- `Room`: Assigned room
- `Lec`: Lecture hours
- `Lab`: Laboratory hours
- `Credit Units`: Total credit units
- `Units`: Weighted units
- `Instructor/Professor`: Assigned instructor

**Example outputs**:
- `schedule_IT3A.csv` - IT Year 3 Block A
- `schedule_IT3B.csv` - IT Year 3 Block B
- `schedule_IS2C.csv` - IS Year 2 Block C
- etc.

### Advanced Usage

Use as a Python module:

```python
from scheduler import SchedulingOptimizer

# Initialize
optimizer = SchedulingOptimizer(
    courses_file='courses.csv',
    enrollment_file='enrollment.csv',
    rooms_file='room.csv'
)

# Build and solve
optimizer.build_model()
status = optimizer.solve(time_limit=600, gap_tolerance=0.01)

# Export specific schedule
optimizer.export_schedule(
    output_file='custom_schedule.csv',
    program='IT',
    year=3,
    block='A'
)

# Export all schedules
optimizer.export_all_schedules(output_dir='./schedules')
```

## Solver Configuration

### CBC Solver Parameters

- **Time Limit**: 600 seconds (10 minutes) - adjustable
- **Gap Tolerance**: 1% (0.01) - optimality gap
- **Algorithm**: Branch-and-Bound
- **Problem Class**: NP-hard binary integer programming

### Performance Expectations

Based on paper validation:
- **Room Utilization**: 75-85% target, typically achieves ~81%
- **Conflicts**: 0 (guaranteed by constraints)
- **Solve Time**: 4-5 minutes for 99,360 variables
- **Idle Time**: <20%
- **Fairness Score**: >0.90

## Model Scalability

The system handles:
- **Classes**: Up to 200+ class sections
- **Rooms**: Up to 15+ rooms
- **Time Slots**: 45 weekly slots (M-F 9 slots/day, S 6 slots)
- **Enrollment Growth**: Tested up to +15% growth

For larger problems:
- Increase `time_limit` parameter
- Adjust `gap_tolerance` (larger = faster, less optimal)
- Consider problem decomposition

## Customization

### Modify Objective Weights

Edit in `SchedulingOptimizer.__init__()`:
```python
self.alpha = 0.4  # Utilization weight
self.beta = 0.3   # Conflict minimization weight
self.gamma = 0.2  # Idle time reduction weight
self.delta = 0.1  # Fairness weight
```

### Adjust Time Slots

Modify `_generate_time_slots()` method to change:
- Days of week
- Number of slots per day
- Time slot duration
- Start/end times

### Add Constraints

Add custom constraints in `_add_constraints()` method using PuLP syntax:
```python
self.model += (constraint_expression, "Constraint_Name")
```

## Validation & Testing

The implementation follows the paper's validation approach:

1. **Sensitivity Analysis**: Test with ±10-20% enrollment variations
2. **Room Unavailability**: Simulate maintenance scenarios
3. **Constraint Validation**: Verify all hard constraints satisfied
4. **Stakeholder Review**: Compare against manual schedules

## Troubleshooting

### Common Issues

**No feasible solution**:
- Check room capacities vs enrollment
- Verify sufficient time slots
- Review room type compatibility
- Reduce required hours if over-constrained

**Long solve times**:
- Increase gap tolerance
- Reduce problem size (fewer classes/rooms)
- Use more powerful hardware
- Consider time limit adjustment

**Import errors**:
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version >= 3.9
- Verify CSV file formats

## References

Based on research paper by Kenji Mazo, implementing mathematical model adapted from:

Niyonzima, E., & Mukasekuru, A. (2021). "Modelling classroom space allocation at University of Rwanda: A linear programming approach." *Applied Mathematics*, 16(1), 40-52.

## License

Academic research implementation for CCMS, Camarines Norte State College.

## Contact

For questions or issues:
- Author: Kenji Mazo
- Institution: College of Computing and Multimedia Studies
- Location: Camarines Norte State College, Daet, Philippines
