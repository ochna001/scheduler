
from scheduler_large_dataset import solve_large_dataset
import os
import sys

def main():
    print("Starting Full Simulation Simulation...")
    print("Configuration: FULL DATASET")
    
    courses_file = 'courses_full.csv'
    enrollment_file = 'enrollment_full.csv'
    rooms_file = 'rooms_full.csv'
    
    # Verify files exist
    for f in [courses_file, enrollment_file, rooms_file]:
        if not os.path.exists(f):
            print(f"❌ Error: File not found: {f}")
            return

    try:
        print("\n--- Phase 1: Running 1st Semester Schedule ---")
        solve_large_dataset(
            courses_file=courses_file,
            enrollment_file=enrollment_file,
            rooms_file=rooms_file,
            semester=1,
            output_dir='output_full_simulation'
        )
        
        print("\n--- Phase 2: Running 2nd Semester Schedule ---")
        solve_large_dataset(
            courses_file=courses_file,
            enrollment_file=enrollment_file,
            rooms_file=rooms_file,
            semester=2,
            output_dir='output_full_simulation'
        )
        
        print("\n✅ Full Simulation Complete! Check 'output_full_simulation' folder.")
        
    except Exception as e:
        print(f"\n❌ Simulation Failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
