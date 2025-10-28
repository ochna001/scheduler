from scheduler import SchedulingOptimizer
import pandas as pd

print("=== TESTING OPTIMIZATION ===\n")

# Create optimizer
optimizer = SchedulingOptimizer('courses_fixed.csv', 'enrollment_from_json.csv', 'room_final.csv')

print("\n1. Initial Data Summary:")
print(f"   Loaded courses: {len(optimizer.courses_df)}")
print(f"   Loaded enrollments: {len(optimizer.enrollment_df)}")
print(f"   Loaded rooms: {len(optimizer.rooms_df)}")
print(f"   Time slots per day: {optimizer.time_slots_per_day}")
print(f"   Total time slots: {len(optimizer.time_slots)}")
print(f"   Days: {optimizer.days}")

print("\n2. Room capacities:")
for _, room in optimizer.rooms_df.iterrows():
    print(f"   {room['room_id']}: capacity={room['capacity']}, category={room['room_category']}")

print("\n3. Building model to generate classes...")
optimizer.build_model()

print("\n4. Classes generated:")
print(f"   Total classes: {len(optimizer.classes)}")
print(f"   Total rooms: {len(optimizer.rooms)}")
for i, cls in enumerate(optimizer.classes[:5]):
    print(f"   Class {i}: {cls['course_code']} - {cls['program']}{cls['year']}{cls['block']}")
    print(f"      Students: {cls['students']}, Slots needed: {cls['total_slots_needed']}")
    print(f"      Sessions: {cls['session_configs']}, Room category: {cls['room_category_required']}")

print("\n5. Computing resource requirements:")
total_slots_needed = sum(cls['total_slots_needed'] for cls in optimizer.classes)
total_capacity = len(optimizer.rooms) * len(optimizer.time_slots)
print(f"   Total slots needed: {total_slots_needed}")
print(f"   Total capacity: {total_capacity}")
print(f"   Utilization: {total_slots_needed / total_capacity * 100:.1f}%")

# Check for potential issues
print("\n6. Checking for potential conflicts:")
# Check if any student group has overlapping classes
from collections import defaultdict
group_slots = defaultdict(int)
for cls in optimizer.classes:
    group_key = f"{cls['program']}{cls['year']}{cls['block']}"
    group_slots[group_key] += cls['total_slots_needed']

print("   Slots needed per group:")
for group, slots in sorted(group_slots.items()):
    print(f"      {group}: {slots} slots")
    if slots > len(optimizer.time_slots):
        print(f"         WARNING: Exceeds total available slots ({len(optimizer.time_slots)})!")

print("\n7. Solving model...")
try:
    status = optimizer.solve(time_limit=60, gap_tolerance=0.10)  # 60 sec, 10% gap
    print(f"\nFinal status: {status}")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
