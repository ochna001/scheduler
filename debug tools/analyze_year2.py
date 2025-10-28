import pandas as pd

courses_df = pd.read_csv('courses_fixed.csv')
year2_courses = courses_df[courses_df['year'] == 2]

print("Year 2 Courses:")
print("="*80)
total_hours = 0
total_slots = 0
for _, course in year2_courses.iterrows():
    lec = course['lec_hours']
    lab = course['lab_hours']
    total_hours_course = lec + lab
    
    # Calculate slots based on session config
    if lab == 3:
        slots = 6  # Two 1.5-hour sessions
    elif lec == 2 and lab == 0:
        slots = 4  # Two 1-hour sessions
    elif 'GEC' in course['code'] or 'GE Elec' in course['code']:
        slots = 6  # Two 1.5-hour sessions
    elif 'PathFit' in course['code']:
        slots = 4  # One 2-hour session
    elif lec + lab == 3:
        slots = 6  # Two 1.5-hour sessions
    else:
        slots = 0
    
    total_hours += total_hours_course
    total_slots += slots
    print(f"{course['code']:20} {course['name']:60} {lec}L {lab}Lab = {total_hours_course}hr -> {slots} slots")

print("="*80)
print(f"TOTAL: {total_hours} hours = {total_slots} slots (30-min slots)")
print(f"Available slots per week: 80 (16 per day × 5 days)")
print(f"PROBLEM: Need {total_slots} slots but only have 80 slots available!")
