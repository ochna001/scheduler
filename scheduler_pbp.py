"""
Program-by-Program (PBP) Sequential Scheduler - Unified Version

Supports multiple solver backends:
- OR-Tools CP-SAT (fast constraint programming)
- PuLP with CBC (open-source MILP)
- PuLP with HiGHS (fast open-source MILP)

Key features:
- Solves larger programs first, then smaller programs with remaining slots
- Reserves lab slots for later programs to ensure fairness
- Unified interface regardless of solver backend
"""

import pandas as pd
import os
import time
from typing import Dict, List, Set, Tuple, Optional, Callable
from abc import ABC, abstractmethod

# Conditional imports
try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False

try:
    import pulp as pl
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False


class PBPScheduler:
    """
    Program-by-Program Sequential Scheduler with pluggable solver backends.
    
    Strategy:
    1. Sort programs by size (largest first)
    2. Reserve lab slots for later programs
    3. Solve each program sequentially, blocking used slots
    """
    
    def __init__(self, courses_file: str, enrollment_file: str, rooms_file: str, 
                 semester: int = 1, solver: str = "OR_TOOLS_CP_SAT"):
        """
        Initialize the PBP scheduler.
        
        Args:
            courses_file: Path to courses CSV
            enrollment_file: Path to enrollment CSV
            rooms_file: Path to rooms CSV
            semester: Semester number (1 or 2)
            solver: Solver to use - "OR_TOOLS_CP_SAT", "PULP_CBC_CMD", or "HiGHS_CMD"
        """
        self.courses_df = pd.read_csv(courses_file)
        self.enrollment_df = pd.read_csv(enrollment_file)
        self.rooms_df = pd.read_csv(rooms_file)
        self.semester = semester
        self.solver_name = solver
        
        # Filter for semester
        self.courses_df = self.courses_df[self.courses_df['semester'] == semester]
        
        # Get unique programs sorted by total blocks (descending)
        program_sizes = self.enrollment_df.groupby('program').size().sort_values(ascending=False)
        self.programs = program_sizes.index.tolist()
        
        # Time slots (30-min intervals, 8AM-5PM, Mon-Fri)
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.time_slots = self._generate_time_slots()
        
        # Track occupied slots across programs
        self.occupied_slots: Set[Tuple[str, int]] = set()
        
        # Results
        self.all_schedules = []
        self.program_stats = {}
    
    def _generate_time_slots(self) -> List[Dict]:
        """Generate 30-minute time slots."""
        slots = []
        for day_idx, day in enumerate(self.days):
            for hour in range(8, 17):
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
    
    def _calculate_reserved_lab_slots(self, remaining_programs: List[str]) -> Set[Tuple[str, int]]:
        """Calculate lab slots to reserve for remaining programs."""
        reserved = set()
        if not remaining_programs:
            return reserved
        
        # Count lab sessions needed by remaining programs
        remaining_lab_sessions = 0
        for prog in remaining_programs:
            prog_enrollment = self.enrollment_df[self.enrollment_df['program'] == prog]
            prog_courses = self.courses_df[self.courses_df['program'] == prog]
            for _, course in prog_courses.iterrows():
                lab_hours = course.get('lab_hours', 0) or 0
                if lab_hours > 0:
                    year = course['year']
                    blocks_count = len(prog_enrollment[prog_enrollment['year'] == year])
                    remaining_lab_sessions += blocks_count
        
        if remaining_lab_sessions == 0:
            return reserved
        
        # Reserve lab slots across days
        lab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') 
                     if r.get('room_category') == 'lab']
        slots_per_day = len(self.time_slots) // 5
        reserved_count = 0
        
        for day_idx in range(5):
            if reserved_count >= remaining_lab_sessions:
                break
            day_start = day_idx * slots_per_day
            for room in lab_rooms:
                if reserved_count >= remaining_lab_sessions:
                    break
                # Find a good 3-hour block
                for start_offset in [0, 8]:  # 8AM or 1PM
                    start = day_start + start_offset
                    if start + 6 <= day_start + slots_per_day:
                        if not any(self.time_slots[s]['hour'] == 12 for s in range(start, start + 6)):
                            for s in range(start, start + 6):
                                reserved.add((room, s))
                            reserved_count += 1
                            break
        
        return reserved
    
    def _generate_sessions(self, program: str) -> List[Dict]:
        """Generate sessions for a program."""
        prog_enrollment = self.enrollment_df[self.enrollment_df['program'] == program]
        prog_courses = self.courses_df[self.courses_df['program'] == program]
        
        sessions = []
        session_id = 0
        
        for _, course in prog_courses.iterrows():
            course_code = course.get('code') or course.get('course_code')
            year = course['year']
            lec_hours = course.get('lec_hours', 0) or 0
            lab_hours = course.get('lab_hours', 0) or 0
            
            year_blocks = prog_enrollment[prog_enrollment['year'] == year]
            
            for _, block in year_blocks.iterrows():
                block_id = f"{block['program']}-{year}{block['block']}"
                students = block.get('students', 40)
                
                # Lecture sessions
                if lec_hours > 0:
                    comp_id = f"{course_code}_LEC_{block_id}"
                    if lec_hours == 3:
                        for _ in range(3):  # 3x 1hr
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
                    elif lec_hours == 2:
                        for _ in range(2):  # 2x 1hr
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
                
                # Lab sessions
                if lab_hours > 0:
                    comp_id = f"{course_code}_LAB_{block_id}"
                    sessions.append({
                        'id': session_id,
                        'component': comp_id,
                        'course_code': course_code,
                        'block': block_id,
                        'room_type': 'lab',
                        'duration_slots': 6,  # 3 hours
                        'students': students
                    })
                    session_id += 1
        
        return sessions
    
    def solve_all_programs(self, time_limit: int = 300, reserve_ratio: float = 0.3,
                          callback: Callable = None) -> Tuple[bool, Dict]:
        """
        Solve scheduling for all programs sequentially.
        
        Returns:
            (success, stats_dict)
        """
        total_start = time.time()
        
        if callback:
            callback(f"Programs to schedule: {self.programs}")
            callback(f"Strategy: Program-by-Program Sequential")
            callback(f"Solver: {self.solver_name}")
        
        for prog_idx, program in enumerate(self.programs):
            prog_start = time.time()
            
            if callback:
                callback(f"\n{'='*50}")
                callback(f"PROGRAM {prog_idx+1}/{len(self.programs)}: {program}")
                callback(f"{'='*50}")
            
            # Calculate reserved slots for remaining programs
            remaining_programs = self.programs[prog_idx + 1:]
            reserved_lab_slots = self._calculate_reserved_lab_slots(remaining_programs)
            
            if callback and reserved_lab_slots:
                callback(f"Reserving {len(reserved_lab_slots)} lab slots for {len(remaining_programs)} remaining program(s)")
            
            # Generate sessions for this program
            sessions = self._generate_sessions(program)
            prog_enrollment = self.enrollment_df[self.enrollment_df['program'] == program]
            
            if callback:
                callback(f"  Sessions: {len(sessions)}")
            
            # Solve using selected backend
            success, schedule_rows, stats = self._solve_with_backend(
                sessions, reserved_lab_slots, prog_enrollment, time_limit, callback
            )
            
            if not success:
                if callback:
                    callback(f"❌ Failed to solve for {program}: {stats.get('error', 'Unknown')}")
                return False, {'error': f'Failed to solve {program}'}
            
            # Update occupied slots
            if 'new_occupied' in stats:
                self.occupied_slots.update(stats['new_occupied'])
            
            # Store results
            self.all_schedules.append(pd.DataFrame(schedule_rows))
            self.program_stats[program] = {
                'solve_time': time.time() - prog_start,
                'components': stats.get('components', 0),
                'status': 'Optimal' if stats.get('optimal') else 'Feasible'
            }
            
            if callback:
                callback(f"✓ {program} solved in {time.time() - prog_start:.1f}s")
                self._log_utilization(callback)
        
        total_time = time.time() - total_start
        
        # Calculate final utilization
        utilization = self._calculate_utilization()
        
        return True, {
            'total_time': total_time,
            'programs': self.program_stats,
            'total_components': sum(s.get('components', 0) for s in self.program_stats.values()),
            'utilization': utilization
        }
    
    def _solve_with_backend(self, sessions: List[Dict], reserved_lab_slots: Set,
                           enrollment_df: pd.DataFrame, time_limit: int,
                           callback: Callable) -> Tuple[bool, List[Dict], Dict]:
        """Dispatch to appropriate solver backend."""
        
        rooms = self.rooms_df.to_dict('records')
        
        if self.solver_name == "OR_TOOLS_CP_SAT":
            return self._solve_cpsat(sessions, rooms, reserved_lab_slots, enrollment_df, time_limit, callback)
        else:
            return self._solve_pulp(sessions, rooms, reserved_lab_slots, enrollment_df, time_limit, callback)
    
    def _solve_cpsat(self, sessions, rooms, reserved_lab_slots, enrollment_df, time_limit, callback):
        """Solve using OR-Tools CP-SAT."""
        if not ORTOOLS_AVAILABLE:
            return False, [], {'error': 'OR-Tools not installed'}
        
        model = cp_model.CpModel()
        X = {}
        
        # Create decision variables
        for session in sessions:
            session_id = session['id']
            duration_slots = session['duration_slots']
            room_type = session['room_type']
            students = session['students']
            
            for room in rooms:
                room_id = room['room_id']
                room_cat = room.get('room_category', 'non-lab')
                
                if room_type == 'lab' and room_cat != 'lab':
                    continue
                if students > room['capacity']:
                    continue
                
                for slot in self.time_slots:
                    slot_idx = slot['index']
                    end_slot = slot_idx + duration_slots
                    
                    if end_slot > len(self.time_slots):
                        continue
                    if self.time_slots[end_slot - 1]['day_idx'] != slot['day_idx']:
                        continue
                    if any(self.time_slots[s]['hour'] == 12 for s in range(slot_idx, end_slot)):
                        continue
                    
                    is_blocked = False
                    for s in range(slot_idx, end_slot):
                        if (room_id, s) in self.occupied_slots or (room_id, s) in reserved_lab_slots:
                            is_blocked = True
                            break
                    if is_blocked:
                        continue
                    
                    X[(session_id, room_id, slot_idx)] = model.NewBoolVar(f'X_{session_id}_{room_id}_{slot_idx}')
        
        if callback:
            callback(f"  Variables: {len(X)}")
        
        if not X:
            return False, [], {'error': 'No valid assignments'}
        
        # Check unassignable sessions
        for session in sessions:
            if not any(k[0] == session['id'] for k in X):
                return False, [], {'error': f"Session {session['course_code']} cannot be assigned"}
        
        # Constraints: each session once
        for session in sessions:
            session_vars = [X[k] for k in X if k[0] == session['id']]
            if session_vars:
                model.Add(sum(session_vars) == 1)
        
        # Room conflicts
        for room in rooms:
            room_id = room['room_id']
            for slot in self.time_slots:
                slot_idx = slot['index']
                occupying = []
                for session in sessions:
                    for start in range(max(0, slot_idx - session['duration_slots'] + 1), slot_idx + 1):
                        if (session['id'], room_id, start) in X:
                            occupying.append(X[(session['id'], room_id, start)])
                if occupying:
                    model.Add(sum(occupying) <= 1)
        
        # Group conflicts
        blocks = enrollment_df[['program', 'year', 'block']].drop_duplicates()
        for _, br in blocks.iterrows():
            block_id = f"{br['program']}-{br['year']}{br['block']}"
            block_sessions = [s for s in sessions if s['block'] == block_id]
            for slot in self.time_slots:
                slot_idx = slot['index']
                occupying = []
                for session in block_sessions:
                    for start in range(max(0, slot_idx - session['duration_slots'] + 1), slot_idx + 1):
                        for room in rooms:
                            if (session['id'], room['room_id'], start) in X:
                                occupying.append(X[(session['id'], room['room_id'], start)])
                if occupying:
                    model.Add(sum(occupying) <= 1)
        
        model.Maximize(sum(X.values()))
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)
        
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return False, [], {'error': f'Solver status: {status}'}
        
        # Extract solution
        schedule_rows = []
        new_occupied = set()
        
        for (session_id, room_id, slot_idx), var in X.items():
            if solver.Value(var) == 1:
                session = next(s for s in sessions if s['id'] == session_id)
                slot = self.time_slots[slot_idx]
                duration = session['duration_slots']
                
                for s in range(slot_idx, slot_idx + duration):
                    new_occupied.add((room_id, s))
                
                end_slot = self.time_slots[slot_idx + duration - 1]
                end_hour, end_min = end_slot['hour'], end_slot['minute'] + 30
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
                    'Instructor': 'TBA'
                })
        
        return True, schedule_rows, {
            'components': len(sessions),
            'optimal': status == cp_model.OPTIMAL,
            'new_occupied': new_occupied
        }
    
    def _solve_pulp(self, sessions, rooms, reserved_lab_slots, enrollment_df, time_limit, callback):
        """Solve using PuLP (CBC or HiGHS)."""
        if not PULP_AVAILABLE:
            return False, [], {'error': 'PuLP not installed'}
        
        model = pl.LpProblem("PBP_Schedule", pl.LpMaximize)
        X = {}
        
        # Create decision variables
        for session in sessions:
            session_id = session['id']
            duration_slots = session['duration_slots']
            room_type = session['room_type']
            students = session['students']
            
            for room in rooms:
                room_id = room['room_id']
                room_cat = room.get('room_category', 'non-lab')
                
                if room_type == 'lab' and room_cat != 'lab':
                    continue
                if students > room['capacity']:
                    continue
                
                for slot in self.time_slots:
                    slot_idx = slot['index']
                    end_slot = slot_idx + duration_slots
                    
                    if end_slot > len(self.time_slots):
                        continue
                    if self.time_slots[end_slot - 1]['day_idx'] != slot['day_idx']:
                        continue
                    if any(self.time_slots[s]['hour'] == 12 for s in range(slot_idx, end_slot)):
                        continue
                    
                    is_blocked = False
                    for s in range(slot_idx, end_slot):
                        if (room_id, s) in self.occupied_slots or (room_id, s) in reserved_lab_slots:
                            is_blocked = True
                            break
                    if is_blocked:
                        continue
                    
                    X[(session_id, room_id, slot_idx)] = pl.LpVariable(f'X_{session_id}_{room_id}_{slot_idx}', cat='Binary')
        
        if callback:
            callback(f"  Variables: {len(X)}")
        
        if not X:
            return False, [], {'error': 'No valid assignments'}
        
        # Check unassignable sessions
        for session in sessions:
            if not any(k[0] == session['id'] for k in X):
                return False, [], {'error': f"Session {session['course_code']} cannot be assigned"}
        
        # Precompute slot occupation
        slot_occ = {}
        for session in sessions:
            for slot_idx in range(len(self.time_slots)):
                end = slot_idx + session['duration_slots']
                if end <= len(self.time_slots):
                    slot_occ[(session['id'], slot_idx)] = list(range(slot_idx, end))
        
        # Constraints: each session once
        for session in sessions:
            session_vars = [X[k] for k in X if k[0] == session['id']]
            if session_vars:
                model += pl.lpSum(session_vars) == 1, f"Assign_{session['id']}"
        
        # Room conflicts
        room_slot_vars = {}
        for (sid, rid, start), var in X.items():
            session = next(s for s in sessions if s['id'] == sid)
            for s in slot_occ.get((sid, start), []):
                key = (rid, s)
                if key not in room_slot_vars:
                    room_slot_vars[key] = []
                room_slot_vars[key].append(var)
        
        for (rid, slot), vlist in room_slot_vars.items():
            if len(vlist) > 1:
                model += pl.lpSum(vlist) <= 1, f"Room_{rid}_{slot}"
        
        # Group conflicts
        group_slot_vars = {}
        for (sid, rid, start), var in X.items():
            session = next(s for s in sessions if s['id'] == sid)
            for s in slot_occ.get((sid, start), []):
                key = (session['block'], s)
                if key not in group_slot_vars:
                    group_slot_vars[key] = []
                group_slot_vars[key].append(var)
        
        for (blk, slot), vlist in group_slot_vars.items():
            if len(vlist) > 1:
                model += pl.lpSum(vlist) <= 1, f"Group_{blk}_{slot}"
        
        model += pl.lpSum(X.values()), "Total"
        
        # Select solver with fallback
        solver = None
        if self.solver_name == "HiGHS_CMD":
            # Try HiGHS_CMD first (standalone executable)
            try:
                test_solver = pl.HiGHS_CMD(msg=0)
                if test_solver.available():
                    solver = pl.HiGHS_CMD(msg=0, timeLimit=time_limit)
                    if callback:
                        callback("  Using HiGHS (CMD)")
            except Exception:
                pass
            
            # Try HiGHS API (Python bindings) if CMD not available
            if solver is None:
                try:
                    test_solver = pl.HiGHS(msg=0)
                    if test_solver.available():
                        solver = pl.HiGHS(msg=0, timeLimit=time_limit)
                        if callback:
                            callback("  Using HiGHS (API)")
                except Exception:
                    pass
            
            # Fallback to CBC
            if solver is None:
                if callback:
                    callback("  ⚠ HiGHS not available, falling back to CBC")
                solver = pl.PULP_CBC_CMD(msg=0, timeLimit=time_limit)
        else:
            solver = pl.PULP_CBC_CMD(msg=0, timeLimit=time_limit)
        
        status = model.solve(solver)
        
        if status != pl.LpStatusOptimal:
            if pl.value(model.objective) is None or pl.value(model.objective) == 0:
                return False, [], {'error': f'Status: {pl.LpStatus[status]}'}
        
        # Extract solution
        schedule_rows = []
        new_occupied = set()
        
        for (session_id, room_id, slot_idx), var in X.items():
            if pl.value(var) == 1:
                session = next(s for s in sessions if s['id'] == session_id)
                slot = self.time_slots[slot_idx]
                duration = session['duration_slots']
                
                for s in range(slot_idx, slot_idx + duration):
                    new_occupied.add((room_id, s))
                
                end_slot = self.time_slots[slot_idx + duration - 1]
                end_hour, end_min = end_slot['hour'], end_slot['minute'] + 30
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
                    'Instructor': 'TBA'
                })
        
        return True, schedule_rows, {
            'components': len(sessions),
            'optimal': status == pl.LpStatusOptimal,
            'new_occupied': new_occupied
        }
    
    def _log_utilization(self, callback):
        """Log current slot utilization."""
        lab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') == 'lab']
        nonlab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') != 'lab']
        
        lab_occ = sum(1 for (r, s) in self.occupied_slots if r in lab_rooms)
        nonlab_occ = sum(1 for (r, s) in self.occupied_slots if r in nonlab_rooms)
        total_lab = len(lab_rooms) * len(self.time_slots)
        total_nonlab = len(nonlab_rooms) * len(self.time_slots)
        
        callback(f"  Utilization: Labs {lab_occ}/{total_lab} ({100*lab_occ/total_lab:.1f}%), Lectures {nonlab_occ}/{total_nonlab} ({100*nonlab_occ/total_nonlab:.1f}%)")
    
    def _calculate_utilization(self) -> Dict:
        """Calculate final utilization metrics."""
        lab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') == 'lab']
        nonlab_rooms = [r['room_id'] for r in self.rooms_df.to_dict('records') if r.get('room_category') != 'lab']
        
        lab_occ = sum(1 for (r, s) in self.occupied_slots if r in lab_rooms)
        nonlab_occ = sum(1 for (r, s) in self.occupied_slots if r in nonlab_rooms)
        total_lab = len(lab_rooms) * len(self.time_slots)
        total_nonlab = len(nonlab_rooms) * len(self.time_slots)
        
        return {
            'lab': 100 * lab_occ / total_lab if total_lab > 0 else 0,
            'lecture': 100 * nonlab_occ / total_nonlab if total_nonlab > 0 else 0,
            'lab_slots': f"{lab_occ}/{total_lab}",
            'lecture_slots': f"{nonlab_occ}/{total_nonlab}"
        }
    
    def export_schedules(self, output_dir: str) -> pd.DataFrame:
        """Export all schedules to CSV files."""
        if not self.all_schedules:
            return pd.DataFrame()
        
        combined = pd.concat(self.all_schedules, ignore_index=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Export per block
        if 'Program-Year-Block' in combined.columns:
            for block in combined['Program-Year-Block'].unique():
                block_df = combined[combined['Program-Year-Block'] == block]
                block_df.to_csv(os.path.join(output_dir, f"schedule_{block}.csv"), index=False)
        
        # Export combined
        combined.to_csv(os.path.join(output_dir, '_schedule_ALL.csv'), index=False)
        return combined


def solve_pbp(courses_file: str, enrollment_file: str, rooms_file: str,
              semester: int = 1, output_dir: str = "schedules",
              time_limit: int = 300, solver: str = "OR_TOOLS_CP_SAT",
              callback: Callable = None) -> Tuple[bool, Dict]:
    """
    Convenience function to solve scheduling program-by-program.
    
    Args:
        solver: "OR_TOOLS_CP_SAT", "PULP_CBC_CMD", or "HiGHS_CMD"
    """
    scheduler = PBPScheduler(courses_file, enrollment_file, rooms_file, semester, solver)
    
    success, stats = scheduler.solve_all_programs(time_limit=time_limit, callback=callback)
    
    if success:
        sem_folder = f"{'1st' if semester == 1 else '2nd'}_Sem_Schedule"
        full_output = os.path.join(output_dir, sem_folder)
        scheduler.export_schedules(full_output)
        if callback:
            callback(f"\n✓ Schedules exported to {full_output}")
    
    return success, stats


if __name__ == "__main__":
    def print_cb(msg):
        print(msg)
    
    # Test with different solvers
    for solver in ["OR_TOOLS_CP_SAT", "HiGHS_CMD", "PULP_CBC_CMD"]:
        print(f"\n{'='*60}")
        print(f"Testing solver: {solver}")
        print(f"{'='*60}")
        
        success, stats = solve_pbp(
            courses_file="courses_full.csv",
            enrollment_file="enrollment_full.csv",
            rooms_file="rooms_full.csv",
            semester=1,
            output_dir=f"test_pbp_{solver}",
            time_limit=120,
            solver=solver,
            callback=print_cb
        )
        print(f"\nSuccess: {success}")
        if success:
            print(f"Total time: {stats['total_time']:.1f}s")
            print(f"Utilization: Lab {stats['utilization']['lab']:.1f}%, Lecture {stats['utilization']['lecture']:.1f}%")
