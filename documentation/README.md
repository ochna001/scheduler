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
4. **Room Type Matching**: Classes assigned to compatible rooms (Lecture/Lab)
5. **Contiguity Preference**: Multi-hour classes must be in consecutive slots
6. **Lunch Break**: No classes scheduled 12:00-13:00
7. **PathFit Rule**: 2-hour blocks scheduled on a single day
8. **Practicum Rule**: 2-hour weekly check-in for off-campus practicum courses

## System Architecture

### Solvers Supported
- **HiGHS**: High-performance open-source solver (Recommended for speed)
- **CBC**: Coin-OR Branch and Cut (Standard default)
- **GLPK/COIN**: Supported if installed

### Decomposition Strategies
To handle large datasets (full university schedules), the system implements two strategies:
1. **Global (All-at-Once)**: Solves the entire schedule as one massive MIP problem. Optimal but computationally expensive.
2. **Sequential (Year-by-Year)**: Decomposes the problem by year level (Year 1 → Year 2 → ...). Faster and scalable, respects previously occupied slots.

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
- Highspy (HiGHS solver bindings)

## Input Files

The system requires three CSV input files:

### 1. courses.csv
Defines courses with room requirements.
**Columns**: `code`, `name`, `program`, `year`, `semester`, `lec_hours`, `lab_hours`, `room_category`

### 2. enrollment.csv
Student enrollment by program/year/block.
**Columns**: `program`, `year`, `block`, `students`

### 3. room.csv
Available rooms and their specifications.
**Columns**: `room_id`, `building`, `floor`, `capacity`, `room_type`

## Usage

### GUI Application (Recommended)

Run the graphical interface:
```bash
python scheduler_gui_v3.py
```

**Features:**
- **Feasibility Check**: Analyze demand vs. supply before solving.
- **Dynamic Configuration**:
  - Override room counts (Lab/Lecture)
  - Adjust Time Limit (seconds/year)
  - Adjust Gap Tolerance (0.1% - 20%)
- **Visualizer**: Interactive timetable grid and list view.
- **Stop Simulation**: Gracefully stop between year iterations.

### Command Line Usage

Run the basic scheduler:
```bash
python scheduler.py
```

## Output Files

The system generates schedules in CSV format:

**Output format**:
`Course Code`, `Course Title`, `Time`, `Days`, `Room`, `Lec`, `Lab`, `Units`, `No. of Hours`, `ETL Units`, `Instructor/Professor`, `Program-Year-Block`

**Example outputs**:
- `schedule_IT3A.csv`
- `schedule_IS2C.csv`

## Solver Configuration

### Dynamic Parameters
The GUI allows runtime adjustment of:
- **Time Limit**: Controls max runtime per sub-problem.
- **Gap Tolerance**: Controls optimality vs. speed trade-off. Higher gap (e.g., 10%) = faster solution.

### Performance Expectations
- **HiGHS Solver**: ~10-20x faster than CBC.
- **Sequential Strategy**: Reduces complexity by ~75%.
- **Room Utilization**: Typically achieves 75-85%.

## Troubleshooting

**Long solve times**:
- Switch to **HiGHS** solver.
- Increase **Gap Tolerance** (e.g., to 10%).
- Use **Sequential** strategy.
- Reduce **Time Limit**.

**Infeasible Solution**:
- Run **Feasibility Check** in GUI first.
- Add more rooms or increase operating hours.

## License
Academic research implementation for CCMS, Camarines Norte State College.

## Contact
- Author: Kenji Mazo
- Institution: College of Computing and Multimedia Studies
- Location: Camarines Norte State College, Daet, Philippines
