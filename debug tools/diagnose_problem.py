import pandas as pd
from scheduler import SchedulingOptimizer

print("=== DIAGNOSTIC TEST ===\n")

# Check rooms file
print("1. Checking rooms file:")
rooms_df = pd.read_csv('room_final.csv')
print(f"   Columns: {list(rooms_df.columns)}")
print(f"   Number of rooms: {len(rooms_df)}")
print(f"\n   Sample room:")
print(rooms_df.head(3))

# Check if room_category column exists
if 'room_category' not in rooms_df.columns:
    print("\n   ERROR: 'room_category' column missing!")
    print("   Need to add room_category based on room_type or equipment")

print("\n2. Checking courses file:")
courses_df = pd.read_csv('courses_fixed.csv')
print(f"   Columns: {list(courses_df.columns)}")
print(f"   Number of courses: {len(courses_df)}")
print(f"   Room categories: {courses_df['room_category'].unique()}")

print("\n3. Checking enrollment file:")
enrollment_df = pd.read_csv('enrollment_from_json.csv')
print(f"   Columns: {list(enrollment_df.columns)}")
print(f"   Number of groups: {len(enrollment_df)}")
print(f"   Total students: {enrollment_df['students'].sum()}")

print("\n4. Creating optimizer and checking class generation:")
try:
    optimizer = SchedulingOptimizer('courses_fixed.csv', 'enrollment_from_json.csv', 'room_final.csv')
    print("   ERROR: Should have failed without room_category column!")
except Exception as e:
    print(f"   Expected error: {e}")

print("\n=== END DIAGNOSTIC ===")
