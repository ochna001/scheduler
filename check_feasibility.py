
import pandas as pd

def check_capacity(courses_file, enrollment_file, rooms_file):
    print(f"Checking capacity for:")
    print(f"  Courses: {courses_file}")
    print(f"  Enrollment: {enrollment_file}")
    print(f"  Rooms: {rooms_file}")

    courses = pd.read_csv(courses_file)
    enrollment = pd.read_csv(enrollment_file)
    rooms = pd.read_csv(rooms_file)

    # 1. Calculate Total Demand (Student-Hours or Room-Hours)
    # We need to know how many sections of each course are needed.
    # Join enrollment with courses based on program and year?
    # The enrollment file has program, year, block.
    # The courses file has program, year, semester.
    
    # Let's assume we are checking Semester 1
    semester = 1
    sem_courses = courses[courses['semester'] == semester]
    
    total_lab_hours_demand = 0
    total_lec_hours_demand = 0
    
    print(f"\nAnalyzing Semester {semester} Demand...")
    
    for _, group in enrollment.iterrows():
        # For each student group (e.g., IT 1-A), find their courses
        group_program = group['program']
        group_year = group['year']
        
        # Find courses for this group
        group_courses = sem_courses[
            (sem_courses['program'] == group_program) & 
            (sem_courses['year'] == group_year)
        ]
        
        for _, course in group_courses.iterrows():
            total_lec_hours_demand += course['lec_hours']
            total_lab_hours_demand += course['lab_hours']

    print(f"Total Lecture Hours Needed: {total_lec_hours_demand}")
    print(f"Total Lab Hours Needed: {total_lab_hours_demand}")

    # 2. Calculate Total Supply (Room-Hours)
    # Assume 5 days a week, 8am-5pm (9 hours) ? 
    # Scheduler says 8am-5pm = 9 hours.
    # But scheduler.py says:
    # times = [8:00, 8:30, ... 12:00, 1:00, ... 5:00] -> That's 8 hours + 4 hours?
    # Let's check scheduler.py generate_time_slots again.
    # Usually 8-12 (4 hrs) and 1-5 (4 hrs) = 8 hours/day * 5 days = 40 hours/week per room.
    
    HOURS_PER_WEEK = 40 
    
    lab_rooms = rooms[rooms['room_category'] == 'lab']
    non_lab_rooms = rooms[rooms['room_category'] == 'non-lab']
    
    total_lab_supply = len(lab_rooms) * HOURS_PER_WEEK
    total_lec_supply = len(non_lab_rooms) * HOURS_PER_WEEK 
    # Note: Labs can often host lectures, but non-labs usually can't host labs.
    # But usually we try to keep them separate.
    
    print(f"\nSupply (assuming 40 hours/week):")
    print(f"Lab Room Hours Available: {total_lab_supply} (from {len(lab_rooms)} rooms)")
    print(f"Lecture Room Hours Available: {total_lec_supply} (from {len(non_lab_rooms)} rooms)")
    
    # 3. Comparison
    print(f"\nFeasibility Check:")
    
    if total_lab_hours_demand > total_lab_supply:
        print(f"❌ CRITICAL: Lab demand ({total_lab_hours_demand}) exceeds supply ({total_lab_supply})!")
    else:
        print(f"✅ Lab demand fits in supply ({total_lab_hours_demand} / {total_lab_supply} = {total_lab_hours_demand/total_lab_supply:.2%})")
        
    if total_lec_hours_demand > total_lec_supply:
        print(f"⚠️ Lecture demand ({total_lec_hours_demand}) exceeds specialized lecture room supply ({total_lec_supply}).")
        print("   Checking if overflow can fit in labs...")
        surplus_lab_capacity = total_lab_supply - total_lab_hours_demand
        needed = total_lec_hours_demand - total_lec_supply
        if surplus_lab_capacity >= needed:
             print(f"   ✅ Overflow fits in empty lab slots (Net utilization: {(total_lec_hours_demand + total_lab_hours_demand) / (total_lab_supply + total_lec_supply):.2%})")
        else:
             print(f"   ❌ CRITICAL: Total demand exceeds Total supply!")
    else:
        print(f"✅ Lecture demand fits in supply ({total_lec_hours_demand} / {total_lec_supply} = {total_lec_hours_demand/total_lec_supply:.2%})")

if __name__ == "__main__":
    check_capacity('courses_full.csv', 'enrollment_full.csv', 'rooms_full.csv')
