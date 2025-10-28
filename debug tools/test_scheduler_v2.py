"""
Test script for the updated session-based scheduler
"""
import sys
sys.path.insert(0, r'c:\Users\Kenji\OneDrive\Documents\quanti')

from scheduler import SchedulingOptimizer
import pulp as pl

def test_scheduler():
    print("="*60)
    print("TESTING SESSION-BASED SCHEDULER")
    print("="*60)
    
    # Initialize optimizer
    optimizer = SchedulingOptimizer(
        courses_file=r'c:\Users\Kenji\OneDrive\Documents\quanti\courses_fixed.csv',
        enrollment_file=r'c:\Users\Kenji\OneDrive\Documents\quanti\enrollment_from_json.csv',
        rooms_file=r'c:\Users\Kenji\OneDrive\Documents\quanti\room_redesigned.csv'
    )
    
    # Build model
    print("\n" + "="*60)
    print("BUILDING MODEL")
    print("="*60)
    optimizer.build_model()
    
    # Print some stats
    print(f"\n\nMODEL STATISTICS:")
    print(f"  Total sessions created: {len(optimizer.classes)}")
    
    # Show breakdown
    lecture_sessions = [s for s in optimizer.classes if s['session_type'] == 'lecture']
    lab_sessions = [s for s in optimizer.classes if s['session_type'] == 'lab']
    print(f"  - Lecture sessions: {len(lecture_sessions)}")
    print(f"  - Lab sessions: {len(lab_sessions)}")
    
    # Show sample sessions
    print(f"\n\nSAMPLE SESSIONS (first 5):")
    for i, session in enumerate(optimizer.classes[:5]):
        print(f"  {i+1}. {session['course_code']} - {session['session_type']} session {session['session_number']}/{session['total_count']}")
        print(f"     Duration: {session['duration_slots']} slots ({session['duration_slots'] * 0.5} hours)")
        print(f"     Students: {session['students']} | Group: {session['program']}{session['year']}{session['block']}")
    
    # Solve
    print("\n" + "="*60)
    print("SOLVING")
    print("="*60)
    status = optimizer.solve(time_limit=300, gap_tolerance=0.05)
    
    if status == pl.LpStatusOptimal:
        print("\n✓ Schedule found successfully!")
    else:
        print("\n✗ No feasible schedule found")
        print("Status:", pl.LpStatus[status])
    
    return optimizer, status

if __name__ == "__main__":
    optimizer, status = test_scheduler()
