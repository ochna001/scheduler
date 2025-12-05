"""
Program-by-Program Sequential Scheduler

Solves scheduling problem by program (e.g., IT first, then IS).
This is faster than global solving while ensuring fair time slot distribution.

Key features:
- Solves larger program first, then smaller programs with remaining slots
- Reserves some prime time slots for later programs to ensure fairness
- Uses OR-Tools CP-SAT for fast solving
"""

import pandas as pd
import os
import time
from typing import Dict, List, Set, Tuple, Optional
from ortools.sat.python import cp_model


class ProgramSequentialScheduler:
    """
    Schedules courses program-by-program using OR-Tools CP-SAT.
    
    Strategy:
    1. Sort programs by size (largest first for efficiency)
    2. Reserve a portion of prime slots for later programs
    3. Solve each program, blocking used slots for next program
    """
    
    def __init__(self, courses_file: str, enrollment_file: str, rooms_file: str, semester: int = 1):
        self.courses_df = pd.read_csv(courses_file)
        self.enrollment_df = pd.read_csv(enrollment_file)
        self.rooms_df = pd.read_csv(rooms_file)
        self.semester = semester
        
        # Filter for semester
        self.courses_df = self.courses_df[self.courses_df['semester'] == semester]
        
        # Get unique programs sorted by total blocks (descending)
        program_sizes = self.enrollment_df.groupby('program').size().sort_values(ascending=False)
        self.programs = program_sizes.index.tolist()
        
        # Time slots (30-min intervals, 8AM-5PM, Mon-Fri)
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.time_slots = self._generate_time_slots()
        
        # Track occupied slots across programs
        self.occupied_slots: Set[Tuple[str, int]] = set()  # (room_id, slot_index)
        
        # Prime time slots (9AM-3PM) - reserve some for later programs
        self.prime_slots = self._get_prime_slot_indices()
        
        # Results
        self.all_schedules = []
        self.program_stats = {}
        
    def _generate_time_slots(self) -> List[Dict]:
        """Generate 30-minute time slots."""
        slots = []
        for day_idx, day in enumerate(self.days):
            for hour in range(8, 17):  # 8AM to 5PM
                for minute in [0, 30]:
                    if hour == 12:  # Skip lunch
                        continue
                    slot_idx = len(slots)
                    slots.append({
                        'index': slot_idx,
                        'day': day,
                        'day_idx': day_idx,
                        'hour': hour,
                        'minute': minute,
                        'time_str': f"{hour:02d}:{minute:02d}"
                    })
        return slots
    
    def _get_prime_slot_indices(self) -> Set[int]:
        """Get indices of prime time slots (9AM-3PM)."""
        prime = set()
        for slot in self.time_slots:
            if 9 <= slot['hour'] < 15:  # 9AM to 3PM
                prime.add(slot['index'])
        return prime
    
    def solve_all_programs(self, time_limit: int = 300, reserve_ratio: float = 0.3,
                          callback=None) -> Tuple[bool, Dict]:
        """
        Solve scheduling for all programs sequentially.
        
        Args:
            time_limit: Time limit per program in seconds
            reserve_ratio: Fraction of prime slots to reserve for later programs
            callback: Optional callback function for progress updates
            
        Returns:
            (success, stats_dict)
        """
        total_start = time.time()
        
        if callback:
            callback(f"Programs to schedule: {self.programs}")
            callback(f"Strategy: Program-by-Program Sequential")
            callback(f"Reserve ratio for fairness: {reserve_ratio:.0%}")
        
        for prog_idx, program in enumerate(self.programs):
            prog_start = time.time()
            
            if callback:
                callback(f"\n{'='*50}")
                callback(f"PROGRAM {prog_idx+1}/{len(self.programs)}: {program}")
                callback(f"{'='*50}")
            
            # Calculate reserved slots for remaining programs
            remaining_programs = len(self.programs) - prog_idx - 1
            reserved_lab_slots = set()
            if remaining_programs > 0:
                # Estimate lab needs for remaining programs
                remaining_progs = self.programs[prog_idx + 1:]
                remaining_lab_sessions = 0
                for rp in remaining_progs:
                    rp_enrollment = self.enrollment_df[self.enrollment_df['program'] == rp]
                    rp_courses = self.courses_df[self.courses_df['program'] == rp]
                    for _, course in rp_courses.iterrows():
                        lab_hours = course.get('lab_hours', 0) or 0
                        if lab_hours > 0:
                            year = course['year']
                            blocks_count = len(rp_enrollment[rp_enrollment['year'] == year])
                            remaining_lab_sessions += blocks_count
                
                # Reserve lab slots: pick best 3-hour blocks across days
                lab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') == 'lab']
                slots_per_day = len(self.time_slots) // 5
                reserved_count = 0
                for day_idx in range(5):  # Spread across days
                    if reserved_count >= remaining_lab_sessions:
                        break
                    day_start = day_idx * slots_per_day
                    for room in lab_rooms:
                        if reserved_count >= remaining_lab_sessions:
                            break
                        # Find a good 3-hour block (morning or afternoon)
                        for start_offset in [0, 8]:  # 8AM or 1PM
                            start = day_start + start_offset
                            if start + 6 <= day_start + slots_per_day:
                                # Check not lunch hour
                                if not any(self.time_slots[s]['hour'] == 12 for s in range(start, start + 6)):
                                    for s in range(start, start + 6):
                                        reserved_lab_slots.add((room, s))
                                    reserved_count += 1
                                    break
                
                if callback:
                    callback(f"Reserving {len(reserved_lab_slots)} lab slots ({reserved_count} 3hr blocks) for {remaining_programs} remaining program(s)")
            else:
                reserved_lab_slots = set()
            
            # Solve for this program
            success, schedule_df, stats = self._solve_program(
                program, time_limit, reserved_lab_slots, callback
            )
            
            if not success:
                if callback:
                    callback(f"❌ Failed to solve for {program}")
                return False, {'error': f'Failed to solve {program}'}
            
            # Store results
            self.all_schedules.append(schedule_df)
            self.program_stats[program] = {
                'solve_time': time.time() - prog_start,
                'components': stats.get('components', 0),
                'status': 'Optimal' if stats.get('optimal') else 'Feasible'
            }
            
            if callback:
                callback(f"✓ {program} solved in {time.time() - prog_start:.1f}s")
                # Show slot utilization after this program
                lab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') == 'lab']
                nonlab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') != 'lab']
                lab_occupied = sum(1 for (r, s) in self.occupied_slots if r in lab_rooms)
                nonlab_occupied = sum(1 for (r, s) in self.occupied_slots if r in nonlab_rooms)
                total_lab_slots = len(lab_rooms) * len(self.time_slots)
                total_nonlab_slots = len(nonlab_rooms) * len(self.time_slots)
                callback(f"  Slot usage: Labs {lab_occupied}/{total_lab_slots} ({100*lab_occupied/total_lab_slots:.1f}%), Lectures {nonlab_occupied}/{total_nonlab_slots} ({100*nonlab_occupied/total_nonlab_slots:.1f}%)")
                
                # Show remaining 3-hour lab blocks per day
                slots_per_day = len(self.time_slots) // 5
                for day_idx, day in enumerate(self.days):
                    day_start = day_idx * slots_per_day
                    day_end = day_start + slots_per_day
                    free_3hr_blocks = 0
                    for room in lab_rooms:
                        # Count contiguous 6-slot (3hr) blocks
                        for start in range(day_start, day_end - 5):
                            if all((room, s) not in self.occupied_slots for s in range(start, start + 6)):
                                # Check not crossing lunch
                                if not any(self.time_slots[s]['hour'] == 12 for s in range(start, start + 6)):
                                    free_3hr_blocks += 1
                    callback(f"    {day}: {free_3hr_blocks} free 3hr lab blocks")
        
        total_time = time.time() - total_start
        
        # Calculate final utilization
        lab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') == 'lab']
        nonlab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') != 'lab']
        lab_occupied = sum(1 for (r, s) in self.occupied_slots if r in lab_rooms)
        nonlab_occupied = sum(1 for (r, s) in self.occupied_slots if r in nonlab_rooms)
        total_lab_slots = len(lab_rooms) * len(self.time_slots)
        total_nonlab_slots = len(nonlab_rooms) * len(self.time_slots)
        
        return True, {
            'total_time': total_time,
            'programs': self.program_stats,
            'total_components': sum(s.get('components', 0) for s in self.program_stats.values()),
            'utilization': {
                'lab': 100 * lab_occupied / total_lab_slots if total_lab_slots > 0 else 0,
                'lecture': 100 * nonlab_occupied / total_nonlab_slots if total_nonlab_slots > 0 else 0,
                'lab_slots': f"{lab_occupied}/{total_lab_slots}",
                'lecture_slots': f"{nonlab_occupied}/{total_nonlab_slots}"
            }
        }
    
    def _solve_program(self, program: str, time_limit: int, reserved_lab_slots: Set[Tuple[str, int]],
                       callback=None) -> Tuple[bool, pd.DataFrame, Dict]:
        """Solve scheduling for a single program.
        
        Args:
            reserved_lab_slots: Set of (room_id, slot_idx) tuples that are reserved for later programs
        """
        
        # Filter data for this program
        prog_enrollment = self.enrollment_df[self.enrollment_df['program'] == program]
        prog_courses = self.courses_df[self.courses_df['program'] == program]
        
        if callback:
            callback(f"  Blocks: {len(prog_enrollment)}, Courses: {len(prog_courses)}")
        
        # Build and solve CP-SAT model
        model = cp_model.CpModel()
        
        # Generate components and sessions for this program
        components, sessions = self._generate_components(prog_courses, prog_enrollment)
        
        if callback:
            callback(f"  Components: {len(components)}, Sessions: {len(sessions)}")
            # Show sessions per block
            from collections import Counter
            block_counts = Counter(s['block'] for s in sessions)
            for block, count in sorted(block_counts.items()):
                lab_count = sum(1 for s in sessions if s['block'] == block and s['room_type'] == 'lab')
                lec_count = count - lab_count
                callback(f"    {block}: {count} sessions ({lec_count} lec, {lab_count} lab)")
        
        # Get available rooms
        rooms = self.rooms_df.to_dict('records')
        
        # Create decision variables
        # X[session_id, room_id, slot] = 1 if session assigned to room at slot
        X = {}
        for session in sessions:
            session_id = session['id']
            duration_slots = session['duration_slots']
            room_type = session['room_type']
            students = session['students']
            
            for room in rooms:
                room_id = room['room_id']
                
                # Check room compatibility
                # room_category: 'lab' or 'non-lab' (lecture rooms)
                room_cat = room.get('room_category', 'non-lab')
                if room_type == 'lab' and room_cat != 'lab':
                    continue
                # Lectures can use any room (lab or non-lab)
                if students > room['capacity']:
                    continue
                
                # For each valid start slot
                for slot in self.time_slots:
                    slot_idx = slot['index']
                    
                    # Check if all required slots are available
                    end_slot = slot_idx + duration_slots
                    if end_slot > len(self.time_slots):
                        continue
                    
                    # Check same day
                    if self.time_slots[end_slot - 1]['day_idx'] != slot['day_idx']:
                        continue
                    
                    # Check not crossing lunch (slot 8-9 on each day is lunch)
                    crosses_lunch = False
                    for s in range(slot_idx, end_slot):
                        if self.time_slots[s]['hour'] == 12:
                            crosses_lunch = True
                            break
                    if crosses_lunch:
                        continue
                    
                    # Check if any slot is already occupied or reserved
                    occupied = False
                    for s in range(slot_idx, end_slot):
                        if (room_id, s) in self.occupied_slots:
                            occupied = True
                            break
                        # Check reserved slots (only for lab rooms)
                        if (room_id, s) in reserved_lab_slots:
                            occupied = True
                            break
                    if occupied:
                        continue
                    
                    X[(session_id, room_id, slot_idx)] = model.NewBoolVar(
                        f'X_{session_id}_{room_id}_{slot_idx}'
                    )
        
        if callback:
            callback(f"  Variables: {len(X)}")
        
        if len(X) == 0:
            if callback:
                callback(f"  ❌ No valid room-slot assignments possible for any session")
            return False, pd.DataFrame(), {'error': 'No valid assignments possible'}
        
        # Check which sessions have no valid assignments
        unassignable_sessions = []
        for session in sessions:
            session_id = session['id']
            session_vars = [k for k in X if k[0] == session_id]
            if len(session_vars) == 0:
                unassignable_sessions.append(session)
        
        if unassignable_sessions:
            if callback:
                callback(f"  ⚠ {len(unassignable_sessions)} sessions have no valid room-slot options:")
                for s in unassignable_sessions[:10]:  # Show first 10
                    callback(f"    - {s['course_code']} ({s['room_type']}) for {s['block']}")
                if len(unassignable_sessions) > 10:
                    callback(f"    ... and {len(unassignable_sessions) - 10} more")
            return False, pd.DataFrame(), {'error': f'{len(unassignable_sessions)} sessions cannot be assigned'}
        
        # Constraints
        
        # 1. Each session must be assigned exactly once
        for session in sessions:
            session_id = session['id']
            session_vars = [X[k] for k in X if k[0] == session_id]
            if session_vars:
                model.Add(sum(session_vars) == 1)
            else:
                # This should not happen if we checked above, but log it
                if callback:
                    callback(f"  ⚠ Session {session_id} ({session['course_code']}) has no valid assignments")
        
        # 2. No room conflicts (same room, overlapping time)
        for room in rooms:
            room_id = room['room_id']
            for slot in self.time_slots:
                slot_idx = slot['index']
                
                # All sessions that could occupy this room-slot
                occupying_vars = []
                for session in sessions:
                    session_id = session['id']
                    duration = session['duration_slots']
                    
                    # Check all start slots that would cover this slot
                    for start in range(max(0, slot_idx - duration + 1), slot_idx + 1):
                        if (session_id, room_id, start) in X:
                            occupying_vars.append(X[(session_id, room_id, start)])
                
                if occupying_vars:
                    model.Add(sum(occupying_vars) <= 1)
        
        # 3. No student group conflicts (same block, overlapping time)
        blocks = prog_enrollment[['program', 'year', 'block']].drop_duplicates()
        for _, block_row in blocks.iterrows():
            block_id = f"{block_row['program']}-{block_row['year']}{block_row['block']}"
            block_sessions = [s for s in sessions if s['block'] == block_id]
            
            for slot in self.time_slots:
                slot_idx = slot['index']
                
                occupying_vars = []
                for session in block_sessions:
                    session_id = session['id']
                    duration = session['duration_slots']
                    
                    for start in range(max(0, slot_idx - duration + 1), slot_idx + 1):
                        for room in rooms:
                            room_id = room['room_id']
                            if (session_id, room_id, start) in X:
                                occupying_vars.append(X[(session_id, room_id, start)])
                
                if occupying_vars:
                    model.Add(sum(occupying_vars) <= 1)
        
        # Objective: Maximize scheduled sessions (should be all)
        model.Maximize(sum(X.values()))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        solver.parameters.num_search_workers = 8
        
        status = solver.Solve(model)
        
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_name = {
                cp_model.UNKNOWN: "UNKNOWN",
                cp_model.MODEL_INVALID: "MODEL_INVALID",
                cp_model.INFEASIBLE: "INFEASIBLE",
            }.get(status, f"STATUS_{status}")
            if callback:
                callback(f"  ❌ Solver status: {status_name}")
                # Count available slots per room type
                lab_rooms = [r['room_id'] for r in rooms if r.get('room_category') == 'lab']
                lab_sessions = [s for s in sessions if s['room_type'] == 'lab']
                lab_vars = sum(1 for k in X if k[1] in lab_rooms)
                callback(f"  Lab sessions: {len(lab_sessions)}, Lab variables: {lab_vars}")
            return False, pd.DataFrame(), {'error': f'Solver status: {status_name}'}
        
        # Extract solution
        schedule_rows = []
        for (session_id, room_id, slot_idx), var in X.items():
            if solver.Value(var) == 1:
                session = next(s for s in sessions if s['id'] == session_id)
                slot = self.time_slots[slot_idx]
                duration = session['duration_slots']
                
                # Mark slots as occupied for next program
                for s in range(slot_idx, slot_idx + duration):
                    self.occupied_slots.add((room_id, s))
                
                end_slot = self.time_slots[slot_idx + duration - 1]
                end_hour = end_slot['hour']
                end_min = end_slot['minute'] + 30
                if end_min >= 60:
                    end_hour += 1
                    end_min = 0
                
                schedule_rows.append({
                    'Program-Year-Block': session['block'],
                    'Course': session['course_code'],
                    'Component': session['component'],
                    'Day': slot['day'],
                    'Start': slot['time_str'],
                    'End': f"{end_hour:02d}:{end_min:02d}",
                    'Room': room_id,
                    'Instructor': session.get('instructor', 'TBA')
                })
        
        df = pd.DataFrame(schedule_rows)
        
        return True, df, {
            'components': len(sessions),
            'optimal': status == cp_model.OPTIMAL,
            'objective': solver.ObjectiveValue()
        }
    
    def _generate_components(self, courses_df: pd.DataFrame, 
                            enrollment_df: pd.DataFrame) -> Tuple[List, List]:
        """Generate course components and sessions."""
        components = []
        sessions = []
        session_id = 0
        
        for _, course in courses_df.iterrows():
            # Handle both 'code' and 'course_code' column names
            course_code = course.get('code') or course.get('course_code')
            year = course['year']
            lec_hours = course.get('lec_hours', 0) or 0
            lab_hours = course.get('lab_hours', 0) or 0
            
            # Get blocks for this year
            year_blocks = enrollment_df[enrollment_df['year'] == year]
            
            for _, block in year_blocks.iterrows():
                block_id = f"{block['program']}-{year}{block['block']}"
                students = block.get('students', 40)
                
                # Lecture component
                if lec_hours > 0:
                    comp_id = f"{course_code}_LEC_{block_id}"
                    components.append({
                        'id': comp_id,
                        'course': course_code,
                        'type': 'lecture',
                        'hours': lec_hours,
                        'block': block_id
                    })
                    
                    # Generate sessions based on hours
                    # 3 hours = 2 sessions of 1.5hr or 3 sessions of 1hr
                    if lec_hours == 3:
                        # 3x 1hr sessions (MWF pattern)
                        for i in range(3):
                            sessions.append({
                                'id': session_id,
                                'component': comp_id,
                                'course_code': course_code,
                                'block': block_id,
                                'room_type': 'lecture',
                                'duration_slots': 2,  # 1 hour = 2 slots
                                'students': students
                            })
                            session_id += 1
                    elif lec_hours == 2:
                        # 2x 1hr sessions
                        for i in range(2):
                            sessions.append({
                                'id': session_id,
                                'component': comp_id,
                                'course_code': course_code,
                                'block': block_id,
                                'room_type': 'lecture',
                                'duration_slots': 2,
                                'students': students
                            })
                            session_id += 1
                
                # Lab component
                if lab_hours > 0:
                    comp_id = f"{course_code}_LAB_{block_id}"
                    components.append({
                        'id': comp_id,
                        'course': course_code,
                        'type': 'lab',
                        'hours': lab_hours,
                        'block': block_id
                    })
                    
                    # Lab: typically 1x 3hr session
                    sessions.append({
                        'id': session_id,
                        'component': comp_id,
                        'course_code': course_code,
                        'block': block_id,
                        'room_type': 'lab',
                        'duration_slots': 6,  # 3 hours = 6 slots
                        'students': students
                    })
                    session_id += 1
        
        return components, sessions
    
    def export_schedules(self, output_dir: str):
        """Export all schedules to CSV files."""
        if not self.all_schedules:
            return
        
        combined = pd.concat(self.all_schedules, ignore_index=True)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Export per block
        if 'Program-Year-Block' in combined.columns:
            for block in combined['Program-Year-Block'].unique():
                block_df = combined[combined['Program-Year-Block'] == block]
                filename = os.path.join(output_dir, f"schedule_{block}.csv")
                block_df.to_csv(filename, index=False)
        
        # Export combined
        combined.to_csv(os.path.join(output_dir, '_schedule_ALL.csv'), index=False)
        
        return combined


def solve_by_program(courses_file: str, enrollment_file: str, rooms_file: str,
                    semester: int = 1, output_dir: str = "schedules",
                    time_limit: int = 300, reserve_ratio: float = 0.3,
                    callback=None) -> Tuple[bool, Dict]:
    """
    Convenience function to solve scheduling program-by-program.
    
    Args:
        courses_file: Path to courses CSV
        enrollment_file: Path to enrollment CSV
        rooms_file: Path to rooms CSV
        semester: Semester number (1 or 2)
        output_dir: Output directory for schedules
        time_limit: Time limit per program in seconds
        reserve_ratio: Fraction of prime slots to reserve for later programs
        callback: Optional callback for progress updates
        
    Returns:
        (success, stats_dict)
    """
    scheduler = ProgramSequentialScheduler(
        courses_file, enrollment_file, rooms_file, semester
    )
    
    success, stats = scheduler.solve_all_programs(
        time_limit=time_limit,
        reserve_ratio=reserve_ratio,
        callback=callback
    )
    
    if success:
        sem_folder = f"{'1st' if semester == 1 else '2nd'}_Sem_Schedule"
        full_output = os.path.join(output_dir, sem_folder)
        scheduler.export_schedules(full_output)
        if callback:
            callback(f"\n✓ Schedules exported to {full_output}")
    
    return success, stats


if __name__ == "__main__":
    # Test run
    def print_callback(msg):
        print(msg)
    
    success, stats = solve_by_program(
        courses_file="courses_full.csv",
        enrollment_file="enrollment_full.csv",
        rooms_file="rooms_full.csv",
        semester=1,
        output_dir="test_program_seq",
        time_limit=120,
        callback=print_callback
    )
    
    print(f"\nSuccess: {success}")
    print(f"Stats: {stats}")
