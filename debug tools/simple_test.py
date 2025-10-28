"""Test with just a few classes to see if basic model works"""
import pulp as pl
import pandas as pd

# Simplified test: 2 classes, 2 rooms, 20 time slots (1 day)
print("=== SIMPLE FEASIBILITY TEST ===\n")

# Create simple data
classes = [
    {'id': 0, 'course': 'IT100', 'students': 40, 'slots_needed': 6, 'room_type': 'lab'},
    {'id': 1, 'course': 'GEC1', 'students': 40, 'slots_needed': 6, 'room_type': 'non-lab'}
]

rooms = [
    {'id': 0, 'name': 'NB-101', 'capacity': 50, 'type': 'lab'},
    {'id': 1, 'name': 'NB-102', 'capacity': 45, 'type': 'lab'}
]

time_slots = list(range(20))  # 20 slots in one day

print(f"Classes: {len(classes)}")
print(f"Rooms: {len(rooms)}")
print(f"Time slots: {len(time_slots)}")
print(f"Total slots needed: {sum(c['slots_needed'] for c in classes)}")
print(f"Total capacity: {len(rooms) * len(time_slots)}")

# Build model
model = pl.LpProblem("Simple_Test", pl.LpMaximize)

# Decision variables
X = {}
for i in range(len(classes)):
    for j in range(len(rooms)):
        for k in time_slots:
            X[(i, j, k)] = pl.LpVariable(f"X_{i}_{j}_{k}", cat='Binary')

# Objective: maximize assignments
model += pl.lpSum(X[(i, j, k)] for i in range(len(classes)) for j in range(len(rooms)) for k in time_slots)

# Constraint 1: One class per room per slot
for j in range(len(rooms)):
    for k in time_slots:
        model += pl.lpSum(X[(i, j, k)] for i in range(len(classes))) <= 1

# Constraint 2: Each class needs exact number of slots
for i, cls in enumerate(classes):
    model += pl.lpSum(X[(i, j, k)] for j in range(len(rooms)) for k in time_slots) == cls['slots_needed']

# Constraint 3: Capacity
for i, cls in enumerate(classes):
    for j, room in enumerate(rooms):
        for k in time_slots:
            if cls['students'] > room['capacity']:
                model += X[(i, j, k)] == 0

# Constraint 4: Room type compatibility (labs can host non-lab, but not vice versa)
for i, cls in enumerate(classes):
    for j, room in enumerate(rooms):
        if room['type'] == 'non-lab' and cls['room_type'] == 'lab':
            for k in time_slots:
                model += X[(i, j, k)] == 0

print("\nSolving...")
solver = pl.HiGHS(timeLimit=30)
status = model.solve(solver)

print(f"\nStatus: {pl.LpStatus[status]}")
print(f"Objective: {pl.value(model.objective)}")

if status == pl.LpStatusOptimal:
    print("\nSolution found!")
    for i, cls in enumerate(classes):
        print(f"\n{cls['course']}:")
        assigned_slots = [(j, k) for j in range(len(rooms)) for k in time_slots if pl.value(X[(i, j, k)]) == 1]
        for j, k in assigned_slots:
            print(f"  Room {rooms[j]['name']}, Slot {k}")
else:
    print("\nNo feasible solution!")
