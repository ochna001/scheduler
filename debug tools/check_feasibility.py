"""
Feasibility Checker - Diagnose scheduling constraints
"""

import pandas as pd

def check_feasibility(courses_file, enrollment_file, rooms_file):
    """Check if scheduling is theoretically feasible."""
    
    print("="*60)
    print("FEASIBILITY DIAGNOSTIC")
    print("="*60)
    
    # Load data
    courses = pd.read_csv(courses_file)
    enrollment = pd.read_csv(enrollment_file)
    rooms = pd.read_csv(rooms_file)
    
    print(f"\n📊 Input Summary:")
    print(f"   Courses: {len(courses)}")
    print(f"   Enrollment blocks: {len(enrollment)}")
    print(f"   Rooms: {len(rooms)}")
    
    # Calculate total class sections
    print(f"\n📚 Class Sections by Year:")
    total_sections = 0
    for year in [1, 2, 3, 4]:
        year_courses = courses[courses['year'] == year]
        year_blocks = enrollment[enrollment['year'] == year]
        sections = len(year_courses) * len(year_blocks)
        print(f"   Year {year}: {len(year_courses)} courses × {len(year_blocks)} blocks = {sections} sections")
        total_sections += sections
    
    print(f"\n   TOTAL SECTIONS: {total_sections}")
    
    # Room type analysis
    print(f"\n🏢 Room Types Needed vs Available:")
    course_room_needs = courses[courses['lab_hours'] > 0]['room_type_required'].value_counts()
    room_availability = rooms['room_type'].value_counts()
    
    all_types = set(course_room_needs.index) | set(room_availability.index)
    
    issues = []
    for room_type in sorted(all_types):
        needed = course_room_needs.get(room_type, 0)
        available = room_availability.get(room_type, 0)
        status = "✓" if available >= needed else "⚠"
        print(f"   {status} {room_type:15s}: need {needed:2d} rooms, have {available:2d}")
        if available < needed:
            issues.append(f"{room_type}: need {needed}, only have {available}")
    
    # Capacity analysis
    print(f"\n👥 Capacity Check:")
    max_enrollment = enrollment['students'].max()
    min_room_capacity = rooms['capacity'].min()
    
    print(f"   Max enrollment: {max_enrollment} students")
    print(f"   Min room capacity: {min_room_capacity} seats")
    
    if min_room_capacity < max_enrollment:
        print(f"   ⚠ Room {rooms.loc[rooms['capacity'].idxmin(), 'room_id']} too small!")
        issues.append(f"Smallest room ({min_room_capacity} seats) < largest class ({max_enrollment} students)")
    else:
        print(f"   ✓ All rooms can handle largest class")
    
    # Time slot analysis
    time_slots = 51  # Hard-coded from scheduler
    total_capacity = len(rooms) * time_slots
    utilization = (total_sections / total_capacity) * 100
    
    print(f"\n⏰ Time Slot Analysis:")
    print(f"   Available slots: {time_slots}")
    print(f"   Total capacity: {len(rooms)} rooms × {time_slots} slots = {total_capacity}")
    print(f"   Needed sections: {total_sections}")
    print(f"   Utilization: {utilization:.1f}%")
    
    if utilization > 80:
        print(f"   ⚠ Very high utilization - may be tight!")
        issues.append(f"High utilization ({utilization:.1f}%) - reduce blocks or add rooms")
    elif utilization > 60:
        print(f"   ⚠ High utilization - should work but might be challenging")
    else:
        print(f"   ✓ Reasonable utilization")
    
    # Special cases
    print(f"\n🔍 Special Cases:")
    practicum = courses[courses['lab_hours'] > 100]
    if len(practicum) > 0:
        print(f"   ⚠ Found {len(practicum)} practicum/OJT courses (should be removed):")
        for _, course in practicum.iterrows():
            print(f"      - {course['code']}: {course['lab_hours']} hours")
            issues.append(f"{course['code']} has {course['lab_hours']} lab hours (OJT/Practicum)")
    else:
        print(f"   ✓ No practicum courses found")
    
    # Final verdict
    print(f"\n" + "="*60)
    if issues:
        print("❌ LIKELY INFEASIBLE - Issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print(f"\n💡 Suggestions:")
        if any("need" in i and "only have" in i for i in issues):
            print("   - Add more rooms or make general rooms multi-purpose")
        if any("utilization" in i.lower() for i in issues):
            print("   - Reduce number of blocks in enrollment")
        if any("lab hours" in i for i in issues):
            print("   - Remove practicum/OJT courses from schedule")
    else:
        print("✅ LIKELY FEASIBLE")
        print("   All basic constraints look good!")
        print("   If still infeasible, may be due to:")
        print("   - Specific time conflicts")
        print("   - Room type combinations")
        print("   - Constraint tightness")
    
    print("="*60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 4:
        check_feasibility(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Testing with default files...")
        print()
        
        # Test original
        print("TEST 1: Original files")
        try:
            check_feasibility(
                'courses_with_electives.csv',
                'enrollment_from_json.csv',
                'room_fixed.csv'
            )
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "="*60)
        print("\nTEST 2: Fixed files (expanded rooms, no IT128)")
        try:
            check_feasibility(
                'courses_fixed.csv',
                'enrollment_from_json.csv',
                'room_expanded.csv'
            )
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "="*60)
        print("\nTEST 3: Fixed files + reduced enrollment")
        try:
            check_feasibility(
                'courses_fixed.csv',
                'enrollment_reduced.csv',
                'room_expanded.csv'
            )
        except Exception as e:
            print(f"Error: {e}")
