"""
Test scheduling with semester filtering - 1st semester only
"""
from scheduler import SchedulingOptimizer
import pandas as pd

print("="*60)
print("TESTING SEMESTER-BASED SCHEDULING")
print("="*60)

# Use the new courses file with semester column
optimizer = SchedulingOptimizer(
    'courses_with_semester.csv', 
    'enrollment_reduced.csv', 
    'room_final.csv'
)

# Build model for 1st semester only
print("\nBuilding model for 1ST SEMESTER only...")
optimizer.build_model(semester=1)

print(f"\nGenerated sessions: {len(optimizer.classes)}")

# Analyze by year
year_counts = {}
for session in optimizer.classes:
    year = session['year']
    year_counts[year] = year_counts.get(year, 0) + 1

print("\nSessions per year (1st semester):")
for year in sorted(year_counts.keys()):
    print(f"  Year {year}: {year_counts[year]} sessions")

# Check Year 3 specifically
year3_sessions = [s for s in optimizer.classes if s['year'] == 3]
print(f"\nYear 3 details:")
print(f"  Total sessions: {len(year3_sessions)}")

# Count unique courses
unique_courses = set()
for s in year3_sessions:
    unique_courses.add((s['course_code'], s['session_type']))

print(f"  Unique courses: {len(unique_courses)}")
print("\n  Course breakdown:")
for code, stype in sorted(unique_courses):
    meetings = len([s for s in year3_sessions if s['course_code'] == code and s['session_type'] == stype])
    print(f"    {code} ({stype}): {meetings} meetings")

print("\n" + "="*60)
print("This should match the real schedule example!")
print("Expected for Year 3, 1st sem: 7 courses (IT114-IT119, GEC9)")
print("="*60)

# Now try to solve
print("\nAttempting to solve...")
optimizer.solve(time_limit=300, gap_tolerance=0.05)
