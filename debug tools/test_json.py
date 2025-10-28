"""Test JSON parser with all it course.json"""

from json_parser import CurriculumJSONParser, create_sample_enrollment_from_json

print("="*60)
print("TESTING JSON CURRICULUM PARSER")
print("="*60)

# Parse the JSON file
json_file = "it_curriculum.json"
print(f"\nParsing: {json_file}")

try:
    parser = CurriculumJSONParser(json_file)
    
    # Get summary
    summary = parser.get_summary()
    print("\n📊 Curriculum Summary:")
    print(f"  Total Courses: {summary['total_courses']}")
    print(f"  Total Units: {summary['total_units']}")
    print(f"  Total Lecture Hours: {summary['total_lec_hours']}")
    print(f"  Total Lab Hours: {summary['total_lab_hours']}")
    
    print("\n📚 Courses by Year:")
    for year, count in sorted(summary['courses_by_year'].items()):
        print(f"  Year {year}: {count} courses")
    
    print("\n🏢 Courses by Room Type:")
    for room_type, count in sorted(summary['courses_by_room_type'].items()):
        print(f"  {room_type}: {count} courses")
    
    # Save to CSV
    output_csv = 'courses_from_json.csv'
    courses_df = parser.save_to_csv(output_csv)
    print(f"\n✓ Saved courses to: {output_csv}")
    print(f"  ({len(courses_df)} courses)")
    
    # Show sample courses
    print("\n📖 Sample Courses:")
    print(courses_df.head(10).to_string(index=False))
    
    # Create enrollment file
    enrollment_file = 'enrollment_from_json.csv'
    enrollment_df = create_sample_enrollment_from_json(json_file, enrollment_file)
    print(f"\n✓ Generated sample enrollment: {enrollment_file}")
    print(f"  Total students: {enrollment_df['students'].sum()}")
    
    print("\n" + "="*60)
    print("✅ Conversion complete! Files ready for scheduler.")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
