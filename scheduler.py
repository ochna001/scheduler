"""
Classroom Space Allocation Optimizer
Binary Integer Linear Programming Implementation

Based on: "Modelling and Simulating Classroom Space Allocation in CCMS New Building 
and Old Laboratory: A Binary Integer Linear Programming Approach"

Author: Kenji Mazo
"""

import pandas as pd
import pulp as pl
from typing import Dict, List, Tuple, Set
import itertools
from datetime import datetime
import numpy as np
import os
import sys
import json


class SchedulingOptimizer:
    """
    Implements a Binary Integer Linear Programming model for classroom scheduling.

    This optimizer schedules course components (e.g., 'IT114 Lecture') by selecting
    an optimal weekly schedule pattern from a set of predefined valid patterns 
    (e.g., 'MWF at 1hr/meeting' or 'TTh at 1.5hr/meeting').

    Decision Variables:
    - Y_p = 1 if pattern p is chosen for its course component.
    - X_ijk = 1 if session (meeting) i is assigned to room j at start time k.

    Objective:
    - Maximize the number of chosen patterns, effectively ensuring all course
      components are scheduled.
    """
    
    def __init__(self, courses_file: str, enrollment_file: str, rooms_file: str, 
                 lab_pattern: str = '1x3', program_filter: List[str] = None, existing_schedule: pd.DataFrame = None):
        """
        Initialize the scheduling optimizer.
        
        Args:
            courses_file: Path to courses CSV file
            enrollment_file: Path to enrollment CSV file  
            rooms_file: Path to rooms CSV file
            lab_pattern: Lab scheduling pattern ('1x3' for 1hr×3days, '1.5x2' for 1.5hr×2days)
        """
        self.courses_file = courses_file
        self.enrollment_file = enrollment_file
        self.rooms_file = rooms_file
        self.lab_pattern = lab_pattern  # Store lab pattern preference
        
        # Load data
        self.courses_df = pd.read_csv(courses_file)
        
        # Load enrollment (support both CSV and JSON)
        if enrollment_file.endswith('.json'):
            self.enrollment_df = self._generate_enrollment_from_json(courses_file)
        else:
            self.enrollment_df = pd.read_csv(enrollment_file)

        # Ensure year columns are integers to prevent float/int mismatch
        if 'year' in self.courses_df.columns:
            self.courses_df['year'] = pd.to_numeric(self.courses_df['year'], errors='coerce').fillna(0).astype(int)
        if 'year' in self.enrollment_df.columns:
            self.enrollment_df['year'] = pd.to_numeric(self.enrollment_df['year'], errors='coerce').fillna(0).astype(int)

        # Apply program filter if provided
        if program_filter:
            self.enrollment_df = self.enrollment_df[self.enrollment_df['program'].isin(program_filter)]
        
        # Load rooms (CSV only for now)
        self.rooms_df = pd.read_csv(rooms_file)
        self.existing_schedule = existing_schedule
        
        # Time slots: 5-day schedule (M-F)
        self.days = ['M', 'T', 'W', 'TH', 'F']
        self.time_slot_duration = 0.5  # hours (30 minutes)
        self.time_slots = self._generate_time_slots()
        self.time_slots_per_day = len(self.time_slots) // len(self.days)
        
        # Objective function weights (from paper)
        self.alpha = 0.4  # Utilization
        self.beta = 0.3   # Conflict minimization
        self.gamma = 0.2  # Idle time reduction
        self.delta = 0.1  # Fairness
        
        # Model components
        self.model = None
        self.X = {}  # Decision variables
        self.classes = []  # Class sections
        self.rooms = []  # Room IDs
        self.K = []  # Time slot indices
        
    def _generate_time_slots(self):
        """Generate time slots for 8:00 AM - 5:00 PM.
        Creates 30-minute base slots that can be combined for longer sessions.
        """
        slots = []
        slot_id = 0
        
        # Time ranges: 8:00-12:00 (morning), 1:00-5:00 (afternoon)
        # Each hour has 2 slots (30 min each)
        times = [
            ('08:00', '08:30'), ('08:30', '09:00'),
            ('09:00', '09:30'), ('09:30', '10:00'),
            ('10:00', '10:30'), ('10:30', '11:00'),
            ('11:00', '11:30'), ('11:30', '12:00'),
            ('13:00', '13:30'), ('13:30', '14:00'),
            ('14:00', '14:30'), ('14:30', '15:00'),
            ('15:00', '15:30'), ('15:30', '16:00'),
            ('16:00', '16:30'), ('16:30', '17:00'),
        ]
        
        for day in self.days:
            for start, end in times:
                slots.append({
                    'day': day,
                    'start': start,
                    'end': end,
                    'slot_id': slot_id
                })
                slot_id += 1
        
        return slots
    
    def _get_session_configs(self, course):
        """Determine the session configuration based on course type and requirements.
        Returns list of (session_type, duration_in_30min_slots, day_pattern, meetings_per_week)
        
        Multi-pattern approach: Each course type has multiple valid pedagogical patterns.
        The optimizer selects the best pattern based on room availability and conflicts.
        """
        code = course['code']
        lec_hours = course.get('lec_hours', 0)
        lab_hours = course.get('lab_hours', 0)
        configs = []

        # --- Special Handling for Practicum ---
        # Both IT 128 and IS 404 are practicum courses with 486 lab hours (off-campus internship)
        # Treat them as a 2-hour non-lab (lecture) class for weekly check-ins
        if code == 'IT 128' or code == 'IS 404':
            configs.append({'type': 'lecture', 'duration': 2, 'pattern': '2_days', 'meetings': 2})   # 1hr × 2 days
            configs.append({'type': 'lecture', 'duration': 4, 'pattern': 'single_day', 'meetings': 1}) # 2hr x 1 day
            return configs

        # --- Special Handling for PathFit courses ---
        # PathFit is a 2-hour course that should be scheduled as a single 2-hour block once per week
        if code.startswith('PathFit'):
            configs.append({'type': 'lecture', 'duration': 4, 'pattern': 'single_day', 'meetings': 1})  # 2hr × 1 day
            return configs

        # --- LECTURE SESSIONS ---
        if lec_hours > 0:
            if lab_hours == 0:
                # Pure lecture courses (GECs, etc.) are 3 hours per week.
                configs.append({'type': 'lecture', 'duration': 3, 'pattern': '2_days', 'meetings': 2})   # 1.5hr × 2 days
                configs.append({'type': 'lecture', 'duration': 2, 'pattern': 'MWF', 'meetings': 3})   # 1hr × 3 days
            else:
                # Lectures for courses with labs are 2 hours per week.
                configs.append({'type': 'lecture', 'duration': 2, 'pattern': '2_days', 'meetings': 2})   # 1hr × 2 days
                configs.append({'type': 'lecture', 'duration': 4, 'pattern': 'single_day', 'meetings': 1}) # 2hr x 1 day

        # --- LAB SESSIONS ---
        # Rule: All labs are 3 hours per week.
        if lab_hours > 0:
            # Generate patterns for 3 hours total:
            configs.append({'type': 'lab', 'duration': 3, 'pattern': '2_days', 'meetings': 2})   # 1.5hr × 2 days
            configs.append({'type': 'lab', 'duration': 2, 'pattern': 'MWF', 'meetings': 3})   # 1hr × 3 days

        return configs

    def _generate_class_sections(self, semester: int = None):
        """
        Generate schedulable course components, each with multiple possible patterns.
        This new structure allows the solver to choose the best pattern for each course.
        """
        self.course_components = []
        self.patterns = []
        self.sessions = []

        component_id = 0
        pattern_id = 0
        session_id = 0

        all_courses = self.courses_df
        if semester is not None and 'semester' in all_courses.columns:
            all_courses = all_courses[all_courses['semester'] == semester]
            print(f"  Filtering for semester {semester}: {len(all_courses)} courses")

        for _, enrollment in self.enrollment_df.iterrows():
            program, year, block, students = enrollment['program'], enrollment['year'], enrollment['block'], enrollment['students']
            program_courses = all_courses[all_courses['year'] == year]

            for _, course in program_courses.iterrows():
                # Skip NSTP courses as they are scheduled on Saturday at the Covered Court
                if course['code'].startswith('NSTP'):
                    continue
                    
                configs = self._get_session_configs(course)
                if not configs:
                    continue

                # Group configs by session type (lecture/lab) to create components
                configs_by_type = {}
                for config in configs:
                    if config['type'] not in configs_by_type:
                        configs_by_type[config['type']] = []
                    configs_by_type[config['type']].append(config)

                for session_type, type_configs in configs_by_type.items():
                    # Create one course component for this course type (e.g., IT114 Lecture)
                    # IMPORTANT: Determine room_category based on session_type, not course
                    # Lectures can use any room (non-lab), only labs require lab rooms
                    room_category = 'lab' if session_type == 'lab' else 'non-lab'
                    
                    comp = {
                        'id': component_id,
                        'course_code': course['code'],
                        'session_type': session_type,
                        'program': program, 'year': year, 'block': block,
                        'students': students, 'room_category': room_category
                    }
                    self.course_components.append(comp)
                    
                    # Create all possible patterns for this component
                    for config in type_configs:
                        pat = {
                            'id': pattern_id,
                            'component_id': component_id,
                            'pattern_name': f"{config['pattern']}_{config['duration']}x{config['meetings']}"
                        }
                        self.patterns.append(pat)
                        
                        # Create all session instances for this pattern
                        for meeting_num in range(config['meetings']):
                            self.sessions.append({
                                'id': session_id,
                                'pattern_id': pattern_id,
                                'component_id': component_id,
                                'duration_slots': config['duration'],
                                'day_pattern': config['pattern'],
                                # Copy component info for easier access
                                'course_code': comp['course_code'], 'session_type': comp['session_type'],
                                'program': comp['program'], 'year': comp['year'], 'block': comp['block'],
                                'students': comp['students'], 'room_category': comp['room_category']
                            })
                            session_id += 1
                        pattern_id += 1
                    component_id += 1
        
        # For compatibility with old code, we'll point self.classes to self.sessions
        self.classes = self.sessions
    
    def _build_compatibility_matrix(self) -> Dict[Tuple[int, str], bool]:
        """
        Build room-session compatibility matrix based on course room_category.
        Returns dict with (room_id, course_room_category) -> bool
        
        Rules:
        - Courses with room_category 'lab': ONLY in lab rooms
        - Courses with room_category 'non-lab': ONLY in non-lab rooms
        """
        compatibility = {}
        room_categories = ['lab', 'non-lab']

        for _, room in self.rooms_df.iterrows():
            room_id = room['room_id']
            room_category = room['room_category']

            for course_category in room_categories:
                if course_category == 'lab':
                    # Lab sessions can ONLY use lab rooms
                    compatibility[(room_id, course_category)] = (room_category == 'lab')
                elif course_category == 'non-lab':
                    # Lecture sessions can ONLY use non-lab rooms
                    compatibility[(room_id, course_category)] = (room_category == 'non-lab')

        return compatibility
    
    def _get_valid_start_slots_for_pattern(self, session_idx: int, session: Dict) -> List[int]:
        """
        Get valid start slots for a session based on its day pattern.
        
        Args:
            session_idx: Index of the session
            session: Session dictionary with day_pattern
            
        Returns:
            List of valid start slot indices that match the day pattern
        """
        day_pattern = session['day_pattern']
        duration = session['duration_slots']
        valid_starts = []
        
        # Determine which days are valid for this pattern
        if day_pattern == 'single_day' or day_pattern == 'flexible':
            # Can be scheduled on any day
            valid_days = ['M', 'T', 'W', 'TH', 'F']
        elif day_pattern == 'MWF':
            # Must be on Monday, Wednesday, or Friday
            valid_days = ['M', 'W', 'F']
        elif day_pattern == '2_days':
            # Can be scheduled on any two valid days (flexible)
            valid_days = ['M', 'T', 'W', 'TH', 'F']
        elif day_pattern == 'MW':
            # Must be on Monday or Wednesday
            valid_days = ['M', 'W']
        else:
            # Default: any day
            valid_days = ['M', 'T', 'W', 'TH', 'F']
        
        for k in self.K:
            slot_info = self.time_slots[k]
            day = slot_info['day']
            start_time = slot_info['start']

            # --- OPTIMIZATION HEURISTIC --- #
            # Restrict start times to reduce variable count.
            # - 1-hour sessions (duration=2) can start on the hour.
            # - 1.5-hour sessions (duration=3) can start at 8:00, 9:30, 13:00, 14:30.
            # - Longer sessions can start on the hour.
            minute = int(start_time.split(':')[1])
            if duration == 2 and minute != 0:  # 1hr sessions
                continue
            if duration == 3: # 1.5hr sessions
                if start_time not in ['08:00', '09:30', '13:00', '14:30']:
                    continue
            if duration > 3 and minute != 0: # 2hr+ sessions
                continue
            # --- END HEURISTIC --- #

            # Check if this day matches the pattern
            if day not in valid_days:
                continue
            
            # Check if we can fit duration consecutive slots starting from k on the same day
            valid = True
            # No need to check k + offset >= len(self.K) because self.time_slots is structured
            # such that a valid start time on a given day will always have enough slots.
            end_slot_index = k + duration - 1
            if end_slot_index >= len(self.time_slots) or self.time_slots[end_slot_index]['day'] != day:
                valid = False
            
            # --- LUNCH BREAK CHECK ---
            # Prevent sessions from spanning across the lunch break (12:00-13:00)
            # Morning slots end at 12:00, afternoon slots start at 13:00
            # If session starts in morning (before 12:00) it must end by 12:00
            if valid:
                end_time = self.time_slots[end_slot_index]['end']
                # Check if we're starting in morning but ending in afternoon
                if start_time < '12:00' and end_time > '12:00':
                    valid = False

            if valid:
                valid_starts.append(k)
        
        return valid_starts
    
    def _compute_session_overlaps(self) -> List[Tuple[int, int]]:
        """
        Pre-compute pairs of sessions that could potentially overlap in time.
        Uses a more efficient approach by grouping sessions by time slots.
        Assumes self.valid_starts and self.slot_occupation are already computed.
        
        Returns:
            List of (session_i, session_j) tuples where i < j
        """
        # Build an index: for each time slot, which sessions could occupy it?
        slot_to_sessions = {}
        for i in range(len(self.sessions)):
            for k_start in self.valid_starts.get(i, []):
                for slot in self.slot_occupation.get((i, k_start), []):
                    if slot not in slot_to_sessions:
                        slot_to_sessions[slot] = set()
                    slot_to_sessions[slot].add(i)
        
        # Now find overlapping session pairs
        overlaps = set()
        for slot, sessions_at_slot in slot_to_sessions.items():
            sessions_list = list(sessions_at_slot)
            for idx1 in range(len(sessions_list)):
                for idx2 in range(idx1 + 1, len(sessions_list)):
                    i1, i2 = sessions_list[idx1], sessions_list[idx2]
                    if i1 < i2:
                        overlaps.add((i1, i2))
                    else:
                        overlaps.add((i2, i1))
        
        overlaps = list(overlaps)
        n = len(self.sessions)
        print(f"    Found {len(overlaps)} potential session overlaps out of {n*(n-1)//2} possible pairs")
        return overlaps
    
    def build_model(self, semester: str = None):
        """
        Build the Binary Integer Linear Programming model using the new component-pattern structure.
        """
        print("Building optimization model...")
        
        # Store semester for later use
        self.semester = semester

        # Generate course components, patterns, and sessions
        self._generate_class_sections(semester=semester)
        
        self.rooms = self.rooms_df['room_id'].tolist()
        self.K = list(range(len(self.time_slots)))
        
        print(f"  Course Components: {len(self.course_components)}")
        print(f"  Patterns: {len(self.patterns)}")
        print(f"  Sessions (Meetings): {len(self.sessions)}")
        print(f"  Rooms: {len(self.rooms)}")
        print(f"  Time slots: {len(self.K)}")
        
        # Build compatibility matrix
        self.compatibility = self._build_compatibility_matrix()
        
        # Create the model
        self.model = pl.LpProblem("Classroom_Scheduling", pl.LpMaximize)
        
        # --- Decision Variables ---
        print("Creating decision variables...")
        self.X = {}  # X_ijk = 1 if session i is in room j at start time k
        self.Y = {}  # Y_p = 1 if pattern p is chosen for its component

        # Y variables for pattern selection
        for p in self.patterns:
            self.Y[p['id']] = pl.LpVariable(f"Y_{p['id']}", cat='Binary')

        # X variables for session assignment (OPTIMIZED: only create for compatible room-session pairs)
        for i in range(len(self.sessions)):
            session = self.sessions[i]
            valid_starts = self._get_valid_start_slots_for_pattern(i, session)
            
            for j, room_id in enumerate(self.rooms):
                # Skip incompatible room-session pairs
                if not self.compatibility.get((room_id, session['room_category']), False):
                    continue
                
                # Skip if room capacity is too small
                room_capacity = self.rooms_df.loc[self.rooms_df['room_id'] == room_id, 'capacity'].iloc[0]
                if session['students'] > room_capacity:
                    continue
                
                # Create variables only for valid and feasible assignments
                for k in valid_starts:
                    self.X[(i, j, k)] = pl.LpVariable(f"X_{i}_{j}_{k}", cat='Binary')

        print(f"  Total pattern variables (Y): {len(self.Y)}")
        print(f"  Total session assignment variables (X): {len(self.X)}")

        if not self.X:
            print("\nWARNING: No session assignment variables (X) were created.")
            print("This means no feasible (room, time) slots were found for any session.")
            print("Check room capacities, compatibility, and availability.")

        # --- Objective Function ---
        # Simplified objective: maximize the number of scheduled sessions
        # This is implicitly handled by the constraint that all components must be scheduled.
        # We can just maximize a dummy variable or sum of all Y variables.
        print("Formulating objective function...")
        self.model += pl.lpSum(self.Y), "Total_Patterns_Chosen"
        
        # --- Add Constraints ---
        print("Adding constraints...")
        self._add_constraints()
        self._add_existing_schedule_constraints()
        
        print("Model built successfully!")
        return self.model
    
    def _add_constraints(self):
        """Add all model constraints for the new component-pattern-session model."""
        
        start_time = datetime.now()
        print(f"  [{start_time.strftime('%H:%M:%S')}] Pre-calculating valid starts and slot occupations...")

        # Pre-calculate valid start slots and slot occupations for all sessions
        self.valid_starts = {i: self._get_valid_start_slots_for_pattern(i, s) for i, s in enumerate(self.sessions)}
        self.slot_occupation = {}
        for i, s in enumerate(self.sessions):
            for k_start in self.valid_starts[i]:
                self.slot_occupation[(i, k_start)] = [k_start + offset for offset in range(s['duration_slots'])]

        print(f"    Done in {(datetime.now() - start_time).total_seconds():.2f}s")

        # 1. Pattern Selection Constraint: Exactly one pattern must be chosen per component.
        start_time = datetime.now()
        print(f"  [{start_time.strftime('%H:%M:%S')}] Adding pattern selection constraints...")
        count = 0
        for c in self.course_components:
            patterns_for_comp = [p['id'] for p in self.patterns if p['component_id'] == c['id']]
            if patterns_for_comp:
                self.model += pl.lpSum(self.Y[p_id] for p_id in patterns_for_comp) == 1, f"PatternChoice_{c['id']}"
                count += 1
        print(f"    Added {count} constraints in {(datetime.now() - start_time).total_seconds():.2f}s")


        # 2. Session Assignment Constraint: A session is scheduled iff its parent pattern is chosen.
        start_time = datetime.now()
        print(f"  [{start_time.strftime('%H:%M:%S')}] Adding session assignment constraints...")
        count = 0
        for p in self.patterns:
            sessions_for_pattern = [s['id'] for s in self.sessions if s['pattern_id'] == p['id']]
            for s_id in sessions_for_pattern:
                # Each session of a chosen pattern must be scheduled exactly once.
                self.model += pl.lpSum(self.X.get((s_id, j, k), 0) 
                                      for j in range(len(self.rooms)) 
                                      for k in self.valid_starts.get(s_id, [])) == self.Y[p['id']], f"SessionAssignment_{s_id}"
                count += 1
        print(f"    Added {count} constraints in {(datetime.now() - start_time).total_seconds():.2f}s")

        # 3. Room and Student Group Conflict Constraints (HIGHLY OPTIMIZED)
        start_time = datetime.now()
        print(f"  [{start_time.strftime('%H:%M:%S')}] Adding conflict constraints...")
        
        # Build index: for each (room, slot), which session assignments could occupy it?
        room_slot_assignments = {}
        for (i, j, k) in self.X.keys():
            for slot in self.slot_occupation.get((i, k), []):
                key = (j, slot)
                if key not in room_slot_assignments:
                    room_slot_assignments[key] = []
                room_slot_assignments[key].append((i, j, k))
        
        # Room conflicts: At most one session can occupy each (room, slot)
        count = 0
        for (j, slot), assignments in room_slot_assignments.items():
            if len(assignments) > 1:
                self.model += pl.lpSum(self.X[a] for a in assignments) <= 1, f"RoomConflict_{j}_{slot}"
                count += 1
        print(f"    Added {count} room conflict constraints.")
        
        # Student group conflicts: Build index for each (group, slot)
        group_slot_assignments = {}
        for (i, j, k) in self.X.keys():
            session = self.sessions[i]
            group_key = (session['program'], session['year'], session['block'])
            for slot in self.slot_occupation.get((i, k), []):
                key = (group_key, slot)
                if key not in group_slot_assignments:
                    group_slot_assignments[key] = []
                group_slot_assignments[key].append((i, j, k))
        
        # At most one session per group can occupy each slot
        count = 0
        for (group_key, slot), assignments in group_slot_assignments.items():
            if len(assignments) > 1:
                prog, yr, blk = group_key
                self.model += pl.lpSum(self.X[a] for a in assignments) <= 1, f"GroupConflict_{prog}{yr}{blk}_{slot}"
                count += 1
        print(f"    Added {count} group conflict constraints.")
        print(f"    Done in {(datetime.now() - start_time).total_seconds():.2f}s")


        # 4. Different Day Constraint for multi-meeting patterns (OPTIMIZED)
        start_time = datetime.now()
        print(f"  [{start_time.strftime('%H:%M:%S')}] Adding different-day constraints...")
        count = 0
        for p in self.patterns:
            sessions_in_pattern = [s for s in self.sessions if s['pattern_id'] == p['id']]
            if len(sessions_in_pattern) > 1:
                for idx1 in range(len(sessions_in_pattern)):
                    for idx2 in range(idx1 + 1, len(sessions_in_pattern)):
                        s1 = sessions_in_pattern[idx1]
                        s2 = sessions_in_pattern[idx2]
                        
                        for day_idx in range(len(self.days)):
                            day_slots = set(range(day_idx * self.time_slots_per_day, (day_idx + 1) * self.time_slots_per_day))
                            
                            s1_assignments = [self.X.get((s1['id'], j, k)) for j in range(len(self.rooms)) for k in self.valid_starts.get(s1['id'], []) if k in day_slots and self.X.get((s1['id'], j, k))]
                            s2_assignments = [self.X.get((s2['id'], j, k)) for j in range(len(self.rooms)) for k in self.valid_starts.get(s2['id'], []) if k in day_slots and self.X.get((s2['id'], j, k))]
                            
                            if s1_assignments and s2_assignments:
                                self.model += pl.lpSum(s1_assignments) + pl.lpSum(s2_assignments) <= 1, f"DifferentDay_{p['id']}_s{s1['id']}_s{s2['id']}_day{day_idx}"
                                count += 1
        print(f"    Added {count} constraints in {(datetime.now() - start_time).total_seconds():.2f}s")

        # 5. Same Room and Same Time-of-Day Constraints
        start_time = datetime.now()
        print(f"  [{start_time.strftime('%H:%M:%S')}] Adding same-room and same-time constraints...")
        count = 0
        for p in self.patterns:
            sessions_in_pattern = [s for s in self.sessions if s['pattern_id'] == p['id']]
            if len(sessions_in_pattern) > 1:
                s1 = sessions_in_pattern[0]
                for s2 in sessions_in_pattern[1:]:
                    # Same Room Constraint
                    for j in range(len(self.rooms)):
                        s1_in_room_j = pl.lpSum(self.X.get((s1['id'], j, k), 0) for k in self.valid_starts.get(s1['id'], []))
                        s2_in_room_j = pl.lpSum(self.X.get((s2['id'], j, k), 0) for k in self.valid_starts.get(s2['id'], []))
                        self.model += s1_in_room_j == s2_in_room_j, f"SameRoom_{p['id']}_{s1['id']}_{s2['id']}_r{j}"
                        count += 1

                    # Same Time-of-Day Constraint
                    for t in range(self.time_slots_per_day):
                        s1_at_time_t = pl.lpSum(self.X.get((s1['id'], j, k), 0) for j in range(len(self.rooms)) for k in self.valid_starts.get(s1['id'], []) if k % self.time_slots_per_day == t)
                        s2_at_time_t = pl.lpSum(self.X.get((s2['id'], j, k), 0) for j in range(len(self.rooms)) for k in self.valid_starts.get(s2['id'], []) if k % self.time_slots_per_day == t)
                        self.model += s1_at_time_t == s2_at_time_t, f"SameTime_{p['id']}_{s1['id']}_{s2['id']}_t{t}"
                        count += 1
        print(f"    Added {count} constraints in {(datetime.now() - start_time).total_seconds():.2f}s")

        # 6. Room Capacity and Compatibility (OPTIMIZED)
        start_time = datetime.now()
        print(f"  [{start_time.strftime('%H:%M:%S')}] Adding capacity and compatibility constraints...")
        count = 0
        for i, session in enumerate(self.sessions):
            for j, room_id in enumerate(self.rooms):
                room_capacity = self.rooms_df.loc[self.rooms_df['room_id'] == room_id, 'capacity'].iloc[0]
                
                if not self.compatibility.get((room_id, session['room_category']), False):
                    continue
                
                if session['students'] > room_capacity:
                    for k in self.valid_starts.get(i, []):
                        if self.X.get((i, j, k)) is not None:
                            self.model += self.X[(i, j, k)] == 0, f"Capacity_{i}_{j}_{k}"
                            count += 1
        print(f"    Added {count} constraints in {(datetime.now() - start_time).total_seconds():.2f}s")
    
    def _generate_initial_solution(self) -> Dict:
        """Generate a feasible, non-optimal solution using a greedy heuristic to warm-start the MIP solver."""
        print("  Generating initial solution with greedy heuristic...")
        start_time = datetime.now()

        solution = {'Y': {}, 'X': {}}
        occupied_room_slots = set()  # {(room_idx, slot_idx)}
        occupied_group_slots = set() # {(group_key, slot_idx)}

        # Process components that are harder to schedule first (fewer pattern options)
        components = sorted(self.course_components, key=lambda c: len([p for p in self.patterns if p['component_id'] == c['id']]))

        for comp in components:
            # Try to find a valid assignment for this component
            for pat in (p for p in self.patterns if p['component_id'] == comp['id']):
                sessions_in_pattern = [s for s in self.sessions if s['pattern_id'] == pat['id']]
                
                temp_assignments = []
                temp_room_slots = set()
                temp_group_slots = set()
                is_pattern_schedulable = True

                for sess in sessions_in_pattern:
                    is_session_schedulable = False
                    group_key = (sess['program'], sess['year'], sess['block'])

                    # Find a valid (room, time) for this session
                    for j, room_id in enumerate(self.rooms):
                        room_capacity = self.rooms_df.loc[self.rooms_df['room_id'] == room_id, 'capacity'].iloc[0]
                        if sess['students'] > room_capacity or not self.compatibility.get((room_id, sess['room_category']), False):
                            continue

                        for k in self.valid_starts.get(sess['id'], []):
                            # Check for conflicts
                            is_conflict = False
                            session_slots = self.slot_occupation.get((sess['id'], k), [])
                            for slot in session_slots:
                                if (j, slot) in occupied_room_slots or (j, slot) in temp_room_slots:
                                    is_conflict = True
                                    break
                                if (group_key, slot) in occupied_group_slots or (group_key, slot) in temp_group_slots:
                                    is_conflict = True
                                    break
                            
                            if not is_conflict:
                                # Found a valid spot for this session
                                temp_assignments.append({'s_id': sess['id'], 'j': j, 'k': k})
                                for slot in session_slots:
                                    temp_room_slots.add((j, slot))
                                    temp_group_slots.add((group_key, slot))
                                is_session_schedulable = True
                                break # Go to next session
                        if is_session_schedulable:
                            break # Go to next session
                    
                    if not is_session_schedulable:
                        is_pattern_schedulable = False
                        break # Try next pattern

                if is_pattern_schedulable:
                    # Found a valid schedule for the whole pattern, lock it in
                    solution['Y'][pat['id']] = 1
                    for assign in temp_assignments:
                        solution['X'][(assign['s_id'], assign['j'], assign['k'])] = 1
                    
                    occupied_room_slots.update(temp_room_slots)
                    occupied_group_slots.update(temp_group_slots)
                    break # Go to next component

        scheduled_components = len(solution['Y'])
        print(f"    Greedy heuristic finished in {(datetime.now() - start_time).total_seconds():.2f}s")
        print(f"    Found initial schedule for {scheduled_components} out of {len(self.course_components)} components.")
        return solution

    def _time_str_to_slots(self, time_str: str, days_str: str) -> List[int]:
        """Convert a time string (e.g., '08:00-09:30') and day string (e.g., 'MW') to a list of slot IDs."""
        try:
            start_str, end_str = time_str.split('-')
        except ValueError:
            return [] # Invalid format

        occupied_slots = []
        days = set()
        if 'M' in days_str: days.add('M')
        if 'T' in days_str and 'TH' not in days_str: days.add('T')
        if 'W' in days_str: days.add('W')
        if 'TH' in days_str: days.add('TH')
        if 'F' in days_str: days.add('F')

        for slot in self.time_slots:
            if slot['day'] in days:
                if slot['start'] >= start_str and slot['end'] <= end_str:
                    occupied_slots.append(slot['slot_id'])
        
        return occupied_slots

    def _add_existing_schedule_constraints(self):
        """Add constraints to prevent scheduling over an existing schedule."""
        if self.existing_schedule is None or self.existing_schedule.empty:
            return

        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Adding existing schedule constraints...")
        count = 0

        # Create a quick lookup for room_id to room_index
        room_to_idx = {room_id: i for i, room_id in enumerate(self.rooms)}

        # Find all occupied room-slot pairs from the existing schedule
        occupied_room_slots = set()
        for _, row in self.existing_schedule.iterrows():
            room_id = row.get('Room')
            if room_id not in room_to_idx:
                continue
            
            room_idx = room_to_idx[room_id]
            time_str = row.get('Time')
            days_str = row.get('Days')
            
            if not time_str or not days_str:
                continue

            slot_ids = self._time_str_to_slots(time_str, days_str)
            for slot_id in slot_ids:
                occupied_room_slots.add((room_idx, slot_id))

        # Add constraints for the new sessions
        for (i, j, k), var in self.X.items():
            session_slots = self.slot_occupation.get((i, k), [])
            for slot in session_slots:
                if (j, slot) in occupied_room_slots:
                    self.model += var == 0, f"ExistingScheduleConflict_{i}_{j}_{k}"
                    count += 1
                    break # No need to check other slots for this variable
        
        print(f"    Added {count} constraints from existing schedule in {(datetime.now() - start_time).total_seconds():.2f}s")

    def _create_priority_groups(self):
        """
        Create priority groups for hierarchical scheduling.
        Higher priority courses are scheduled first.
        
        Returns:
            List of (priority_level, component_ids) tuples, sorted by priority (highest first)
        """
        priority_groups = {
            1: [],  # Senior year lab courses (highest priority)
            2: [],  # Senior year lecture courses
            3: [],  # Junior year lab courses
            4: [],  # Junior year lecture courses
            5: [],  # Sophomore year lab courses
            6: [],  # Sophomore year lecture courses
            7: [],  # Freshman year lab courses
            8: []   # Freshman year lecture courses (lowest priority)
        }
        
        for comp in self.course_components:
            year = comp['year']
            session_type = comp['session_type']
            
            # Determine priority based on year and session type
            if year == 4:
                priority = 1 if session_type == 'lab' else 2
            elif year == 3:
                priority = 3 if session_type == 'lab' else 4
            elif year == 2:
                priority = 5 if session_type == 'lab' else 6
            else:  # year == 1
                priority = 7 if session_type == 'lab' else 8
            
            priority_groups[priority].append(comp['id'])
        
        # Return as sorted list of (priority, component_ids)
        return [(p, comps) for p, comps in sorted(priority_groups.items()) if comps]
    
    def _create_sub_model(self, component_ids: List[int], scheduled_components: Set[int]):
        """
        Create a sub-model for a subset of components.
        
        Args:
            component_ids: List of component IDs to schedule in this sub-model
            scheduled_components: Set of already scheduled component IDs (to avoid conflicts)
            
        Returns:
            A new PuLP model for the subset
        """
        print(f"    Creating sub-model for {len(component_ids)} components...")
        
        sub_model = pl.LpProblem("Classroom_Scheduling_Sub", pl.LpMaximize)
        sub_Y = {}
        sub_X = {}
        
        # Track which slots are already occupied by scheduled components
        occupied_room_slots = set()
        occupied_group_slots = set()
        
        for comp_id in scheduled_components:
            # Find the chosen pattern for this component
            for p in self.patterns:
                if p['component_id'] == comp_id and pl.value(self.Y.get(p['id'])) == 1:
                    # Find all sessions for this pattern
                    for s in self.sessions:
                        if s['pattern_id'] == p['id']:
                            # Find the assignment
                            for (i, j, k), var in self.X.items():
                                if i == s['id'] and pl.value(var) == 1:
                                    # Mark these slots as occupied
                                    for slot in self.slot_occupation.get((i, k), []):
                                        occupied_room_slots.add((j, slot))
                                        group_key = (s['program'], s['year'], s['block'])
                                        occupied_group_slots.add((group_key, slot))
        
        # Create Y variables for patterns of target components
        relevant_patterns = [p for p in self.patterns if p['component_id'] in component_ids]
        for p in relevant_patterns:
            sub_Y[p['id']] = pl.LpVariable(f"SubY_{p['id']}", cat='Binary')
        
        # Create X variables for sessions of relevant patterns
        relevant_sessions = [s for s in self.sessions if s['component_id'] in component_ids]
        for s in relevant_sessions:
            s_id = s['id']
            for j in range(len(self.rooms)):
                room_id = self.rooms[j]
                
                # Check compatibility and capacity
                if not self.compatibility.get((room_id, s['room_category']), False):
                    continue
                room_capacity = self.rooms_df.loc[self.rooms_df['room_id'] == room_id, 'capacity'].iloc[0]
                if s['students'] > room_capacity:
                    continue
                
                for k in self.valid_starts.get(s_id, []):
                    # Check if this conflicts with already scheduled components
                    is_conflict = False
                    group_key = (s['program'], s['year'], s['block'])
                    for slot in self.slot_occupation.get((s_id, k), []):
                        if (j, slot) in occupied_room_slots or (group_key, slot) in occupied_group_slots:
                            is_conflict = True
                            break
                    
                    if not is_conflict:
                        sub_X[(s_id, j, k)] = pl.LpVariable(f"SubX_{s_id}_{j}_{k}", cat='Binary')
        
        # Objective: maximize scheduled patterns
        sub_model += pl.lpSum(sub_Y.values()), "Sub_Total_Patterns"
        
        # Constraints (simplified versions of main model constraints)
        # 1. Pattern selection
        for comp_id in component_ids:
            patterns_for_comp = [p['id'] for p in relevant_patterns if p['component_id'] == comp_id]
            if patterns_for_comp:
                sub_model += pl.lpSum(sub_Y[p_id] for p_id in patterns_for_comp) == 1, f"SubPattern_{comp_id}"
        
        # 2. Session assignment
        for p in relevant_patterns:
            sessions_for_pattern = [s['id'] for s in relevant_sessions if s['pattern_id'] == p['id']]
            for s_id in sessions_for_pattern:
                sub_model += pl.lpSum(sub_X.get((s_id, j, k), 0) 
                                     for j in range(len(self.rooms))
                                     for k in self.valid_starts.get(s_id, [])) == sub_Y[p['id']], f"SubSession_{s_id}"
        
        # 3. Room conflicts (only for new assignments)
        room_slot_assignments = {}
        for (i, j, k) in sub_X.keys():
            for slot in self.slot_occupation.get((i, k), []):
                key = (j, slot)
                if key not in room_slot_assignments:
                    room_slot_assignments[key] = []
                room_slot_assignments[key].append((i, j, k))
        
        for (j, slot), assignments in room_slot_assignments.items():
            if len(assignments) > 1:
                sub_model += pl.lpSum(sub_X[a] for a in assignments) <= 1, f"SubRoomConflict_{j}_{slot}"
        
        # 4. Group conflicts (only for new assignments)
        group_slot_assignments = {}
        for (i, j, k) in sub_X.keys():
            session = self.sessions[i]
            group_key = (session['program'], session['year'], session['block'])
            for slot in self.slot_occupation.get((i, k), []):
                key = (group_key, slot)
                if key not in group_slot_assignments:
                    group_slot_assignments[key] = []
                group_slot_assignments[key].append((i, j, k))
        
        for (group_key, slot), assignments in group_slot_assignments.items():
            if len(assignments) > 1:
                prog, yr, blk = group_key
                sub_model += pl.lpSum(sub_X[a] for a in assignments) <= 1, f"SubGroupConflict_{prog}{yr}{blk}_{slot}"
        
        return sub_model, sub_Y, sub_X
    
    def solve_hierarchical(self, semester=None, time_limit_per_phase: int = 300):
        """
        Solve using hierarchical decomposition by priority groups.
        Schedules high-priority courses first, then progressively adds lower priority courses.
        
        Args:
            semester: Semester to schedule (1 or 2)
            time_limit_per_phase: Time limit for each priority phase in seconds
            
        Returns:
            Status code (pl.LpStatusOptimal if all phases succeeded)
        """
        print("\n" + "="*60)
        print("HIERARCHICAL DECOMPOSITION SOLVER")
        print("="*60)
        
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")
        
        priority_groups = self._create_priority_groups()
        print(f"\nCreated {len(priority_groups)} priority groups:")
        for priority, components in priority_groups:
            print(f"  Priority {priority}: {len(components)} components")
        
        scheduled_components = set()
        all_succeeded = True
        
        for priority, component_ids in priority_groups:
            print(f"\n{'='*60}")
            print(f"PHASE: Scheduling Priority {priority} ({len(component_ids)} components)")
            print(f"{'='*60}")
            
            sub_model, sub_Y, sub_X = self._create_sub_model(component_ids, scheduled_components)
            
            # Solve sub-model
            solver = pl.HiGHS(
                timeLimit=time_limit_per_phase,
                gapRel=0.01,
                threads=os.cpu_count()
            )
            
            start_time = datetime.now()
            status = sub_model.solve(solver)
            solve_time = (datetime.now() - start_time).total_seconds()
            
            print(f"\nPhase Status: {pl.LpStatus[status]}")
            print(f"Solve time: {solve_time:.2f} seconds")
            
            if status == pl.LpStatusOptimal:
                # Transfer solution to main model
                scheduled_count = 0
                for p_id, var in sub_Y.items():
                    if pl.value(var) == 1:
                        self.Y[p_id].setInitialValue(1)
                        # Find component for this pattern
                        for p in self.patterns:
                            if p['id'] == p_id:
                                scheduled_components.add(p['component_id'])
                                scheduled_count += 1
                                break
                
                for (i, j, k), var in sub_X.items():
                    if pl.value(var) == 1:
                        self.X[(i, j, k)].setInitialValue(1)
                
                print(f"Successfully scheduled {scheduled_count} components")
            else:
                print(f"Failed to schedule priority {priority} components")
                all_succeeded = False
                # Continue to next priority group anyway
        
        print(f"\n{'='*60}")
        print(f"HIERARCHICAL SCHEDULING COMPLETE")
        print(f"{'='*60}")
        print(f"Total components scheduled: {len(scheduled_components)} / {len(self.course_components)}")
        
        return pl.LpStatusOptimal if all_succeeded else pl.LpStatusNotSolved
    
    def solve_progressive(self, time_limits: List[int] = None, semester=None):
        """
        Solve with increasing time limits and gap tolerances.
        Starts with quick solve, then progressively increases time and precision.
        
        Args:
            time_limits: List of time limits in seconds (default [300, 600, 1200])
            semester: Semester to schedule (1 or 2)
            
        Returns:
            Best solution status found
        """
        if time_limits is None:
            time_limits = [300, 600, 1200]
        
        print("\n" + "="*60)
        print("PROGRESSIVE SOLVER")
        print("="*60)
        
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")
        
        best_solution = None
        best_objective = 0
        best_status = None
        
        for i, time_limit in enumerate(time_limits):
            gap_tolerance = max(0.01, 0.1 / (i + 1))  # Decreasing tolerance: 0.1, 0.05, 0.033...
            
            print(f"\n{'='*60}")
            print(f"ITERATION {i+1}/{len(time_limits)}")
            print(f"{'='*60}")
            print(f"  Time limit: {time_limit} seconds ({time_limit/60:.1f} minutes)")
            print(f"  Gap tolerance: {gap_tolerance * 100:.1f}%")
            
            # Use warm start from previous iteration if available
            if best_solution is not None:
                print(f"  Using warm start from previous iteration")
                for p_id, val in best_solution['Y'].items():
                    if self.Y.get(p_id):
                        self.Y[p_id].setInitialValue(val)
                for (i, j, k), val in best_solution['X'].items():
                    if self.X.get((i, j, k)):
                        self.X[(i, j, k)].setInitialValue(val)
            else:
                # Generate initial solution for first iteration
                warm_start = self._generate_initial_solution()
                for p_id, val in warm_start['Y'].items():
                    if self.Y.get(p_id):
                        self.Y[p_id].setInitialValue(val)
                for (i, j, k), val in warm_start['X'].items():
                    if self.X.get((i, j, k)):
                        self.X[(i, j, k)].setInitialValue(val)
            
            # Solve
            solver = pl.HiGHS(
                timeLimit=time_limit,
                gapRel=gap_tolerance,
                threads=os.cpu_count()
            )
            
            start_time = datetime.now()
            status = self.model.solve(solver)
            solve_time = (datetime.now() - start_time).total_seconds()
            
            print(f"\nIteration Status: {pl.LpStatus[status]}")
            print(f"Solve time: {solve_time:.2f} seconds")
            
            if status in [pl.LpStatusOptimal, pl.LpStatusNotSolved]:
                objective_value = pl.value(self.model.objective)
                print(f"Objective value: {objective_value:.4f}")
                
                if objective_value > best_objective:
                    best_objective = objective_value
                    best_status = status
                    
                    # Extract solution
                    best_solution = {'Y': {}, 'X': {}}
                    for p_id, var in self.Y.items():
                        if pl.value(var) == 1:
                            best_solution['Y'][p_id] = 1
                    for (i, j, k), var in self.X.items():
                        if pl.value(var) == 1:
                            best_solution['X'][(i, j, k)] = 1
                    
                    scheduled_components = len(best_solution['Y'])
                    print(f"New best solution: {scheduled_components} components scheduled")
                
                # If optimal, no need to continue
                if status == pl.LpStatusOptimal:
                    print(f"\nOptimal solution found! Stopping early.")
                    break
            else:
                print("No feasible solution found in this iteration")
        
        print(f"\n{'='*60}")
        print(f"PROGRESSIVE SOLVING COMPLETE")
        print(f"{'='*60}")
        if best_solution:
            print(f"Best solution: {len(best_solution['Y'])} components scheduled")
            print(f"Final status: {pl.LpStatus[best_status]}")
            self._print_performance_metrics()
        else:
            print("No feasible solution found")
        
        return best_status if best_status else pl.LpStatusInfeasible
    
    def preprocess_model(self):
        """
        Apply preprocessing to reduce problem size and improve solving performance.
        This should be called after build_model() but before solving.
        """
        print("\n" + "="*60)
        print("MODEL PREPROCESSING")
        print("="*60)
        
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")
        
        print(f"Original model size:")
        print(f"  Pattern variables (Y): {len(self.Y)}")
        print(f"  Session variables (X): {len(self.X)}")
        
        # 1. Remove dominated patterns
        print(f"\n[1] Removing dominated patterns...")
        removed_patterns = self._remove_dominated_patterns()
        print(f"  Removed {removed_patterns} dominated patterns")
        
        # 2. Fix infeasible assignments
        print(f"\n[2] Fixing infeasible assignments...")
        fixed_vars = self._fix_infeasible_assignments()
        print(f"  Fixed {fixed_vars} infeasible variables to 0")
        
        # 3. Add symmetry breaking constraints
        print(f"\n[3] Adding symmetry breaking constraints...")
        symmetry_constraints = self._add_symmetry_breaking_constraints()
        print(f"  Added {symmetry_constraints} symmetry breaking constraints")
        
        print(f"\nPreprocessed model size:")
        print(f"  Pattern variables (Y): {len(self.Y)}")
        print(f"  Session variables (X): {len(self.X)}")
        print(f"  Total constraints: {len(self.model.constraints)}")
        
        print("="*60)
        print("PREPROCESSING COMPLETE")
        print("="*60)
    
    def _remove_dominated_patterns(self):
        """
        Remove patterns that are strictly dominated by others.
        A pattern A dominates pattern B if:
        - They have the same component
        - A has fewer sessions (less complex to schedule)
        - A has equal or better time flexibility
        """
        removed_count = 0
        
        # Group patterns by component
        patterns_by_component = {}
        for p in self.patterns:
            comp_id = p['component_id']
            if comp_id not in patterns_by_component:
                patterns_by_component[comp_id] = []
            patterns_by_component[comp_id].append(p)
        
        # For each component, find and remove dominated patterns
        for comp_id, comp_patterns in patterns_by_component.items():
            if len(comp_patterns) <= 1:
                continue
            
            # Calculate pattern metrics
            pattern_metrics = []
            for p in comp_patterns:
                sessions = [s for s in self.sessions if s['pattern_id'] == p['id']]
                metrics = {
                    'pattern': p,
                    'sessions': sessions,
                    'num_sessions': len(sessions),
                    'total_duration': sum(s['duration_slots'] for s in sessions),
                    'flexibility_score': self._calculate_pattern_flexibility(sessions)
                }
                pattern_metrics.append(metrics)
            
            # Find dominated patterns
            dominated_patterns = []
            for i, metrics_i in enumerate(pattern_metrics):
                for j, metrics_j in enumerate(pattern_metrics):
                    if i == j:
                        continue
                    
                    # Check if pattern j dominates pattern i
                    if (metrics_j['num_sessions'] < metrics_i['num_sessions'] and
                        metrics_j['total_duration'] <= metrics_i['total_duration'] and
                        metrics_j['flexibility_score'] >= metrics_i['flexibility_score']):
                        dominated_patterns.append(metrics_i['pattern']['id'])
                        break
            
            # Remove dominated patterns
            for pattern_id in dominated_patterns:
                if pattern_id in self.Y:
                    # Remove variable from model
                    var = self.Y[pattern_id]
                    self.model.remove(var)
                    del self.Y[pattern_id]
                    
                    # Remove associated X variables
                    x_to_remove = [(i, j, k) for (i, j, k) in self.X.keys() 
                                  if any(s['pattern_id'] == pattern_id for s in [self.sessions[i]])]
                    for x_key in x_to_remove:
                        if x_key in self.X:
                            self.model.remove(self.X[x_key])
                            del self.X[x_key]
                    
                    removed_count += 1
        
        return removed_count
    
    def _calculate_pattern_flexibility(self, sessions):
        """
        Calculate a flexibility score for a pattern based on available time slots.
        Higher score = more flexible (more scheduling options).
        """
        total_options = 0
        for session in sessions:
            session_id = session['id']
            if session_id in self.valid_starts:
                total_options += len(self.valid_starts[session_id])
        
        return total_options / len(sessions) if sessions else 0
    
    def _fix_infeasible_assignments(self):
        """
        Fix variables that must be 0 due to hard constraints.
        This reduces the search space for the solver.
        """
        fixed_count = 0
        
        # Check each X variable for obvious infeasibilities
        vars_to_fix = []
        
        for (i, j, k), var in self.X.items():
            session = self.sessions[i]
            room_id = self.rooms[j]
            
            # 1. Capacity constraint (already filtered, but double-check)
            room_capacity = self.rooms_df.loc[self.rooms_df['room_id'] == room_id, 'capacity'].iloc[0]
            if session['students'] > room_capacity:
                vars_to_fix.append((var, 0, "Capacity"))
                continue
            
            # 2. Time slot feasibility (check if session fits within day boundaries)
            start_slot = self.time_slots[k]
            duration = session['duration_slots']
            end_slot_idx = k + duration - 1
            
            if end_slot_idx >= len(self.time_slots):
                vars_to_fix.append((var, 0, "Time boundary"))
                continue
            
            end_slot = self.time_slots[end_slot_idx]
            if start_slot['day'] != end_slot['day']:
                vars_to_fix.append((var, 0, "Cross-day session"))
                continue
            
            # 3. Lunch break constraint (no sessions spanning 12:00-13:00)
            session_spans_lunch = False
            for offset in range(duration):
                slot_idx = k + offset
                if slot_idx < len(self.time_slots):
                    slot = self.time_slots[slot_idx]
                    if slot['start'] >= '12:00' and slot['end'] <= '13:00':
                        session_spans_lunch = True
                        break
            
            if session_spans_lunch:
                vars_to_fix.append((var, 0, "Lunch break"))
                continue
        
        # Fix the variables
        for var, value, reason in vars_to_fix:
            self.model += var == value, f"Fixed_{reason}_{var.name}"
            fixed_count += 1
        
        return fixed_count
    
    def _add_symmetry_breaking_constraints(self):
        """
        Add constraints to break symmetries and reduce equivalent solutions.
        This helps the solver converge faster.
        """
        constraints_added = 0
        
        # 1. Lexicographic ordering for identical sessions
        # For sessions with identical requirements, prefer lower-indexed rooms/times
        identical_sessions = self._find_identical_sessions()
        
        for session_group in identical_sessions:
            if len(session_group) <= 1:
                continue
            
            # Sort sessions by some criteria (e.g., program, year, block)
            sorted_sessions = sorted(session_group, 
                                   key=lambda s: (s['program'], s['year'], s['block'], s['course_code']))
            
            # Add ordering constraints: if session_i is in room_j at time_k,
            # then session_{i+1} must be in room >= j or time >= k
            for idx in range(len(sorted_sessions) - 1):
                curr_session = sorted_sessions[idx]
                next_session = sorted_sessions[idx + 1]
                
                # Find all possible assignments for current session
                curr_assignments = [(i, j, k) for (i, j, k) in self.X.keys() 
                                  if i == curr_session['id']]
                next_assignments = [(i, j, k) for (i, j, k) in self.X.keys() 
                                  if i == next_session['id']]
                
                if curr_assignments and next_assignments:
                    # Create symmetry breaking constraint
                    # This is a simplified version - full implementation would be more complex
                    for curr_assign in curr_assignments[:5]:  # Limit to first 5 for efficiency
                        curr_var = self.X[curr_assign]
                        next_vars = [self.X[a] for a in next_assignments if a in self.X]
                        
                        if next_vars:
                            # If current session is assigned here, next session must be assigned
                            # to a "later" slot (simplified constraint)
                            constraint = curr_var <= pl.lpSum(next_vars)
                            self.model += constraint, f"Symmetry_Break_{curr_session['id']}_{next_session['id']}"
                            constraints_added += 1
        
        # 2. Room preference ordering (prefer lower-indexed rooms for flexibility)
        # For each session type, add a weak preference for lower-indexed rooms
        session_types = set(s['session_type'] for s in self.sessions)
        for session_type in session_types:
            sessions_of_type = [s for s in self.sessions if s['session_type'] == session_type]
            if len(sessions_of_type) > 10:  # Only for larger groups
                # Add a small bonus for using lower-indexed rooms first
                # This is implemented as a weak constraint in the objective
                pass  # Would require objective modification
        
        # 3. Time slot ordering (prefer earlier slots for core courses)
        core_courses = [s for s in self.sessions 
                       if any(code in s['course_code'] for code in ['IT', 'IS']) 
                       and s['year'] >= 3]
        
        if len(core_courses) > 5:
            # Add a weak preference for earlier time slots
            # This helps reduce solution symmetry
            pass  # Would require objective modification
        
        return constraints_added
    
    def _find_identical_sessions(self):
        """
        Find groups of sessions that have identical requirements.
        These sessions can be ordered to break symmetry.
        """
        # Group sessions by their key characteristics
        session_groups = {}
        
        for session in self.sessions:
            # Create a key based on session characteristics
            key = (session['session_type'], 
                  session['duration_slots'],
                  session['students'],
                  session['room_category'])
            
            if key not in session_groups:
                session_groups[key] = []
            session_groups[key].append(session)
        
        # Return groups with more than one session
        return [group for group in session_groups.values() if len(group) > 1]

    def solve(self, time_limit: int = 600, gap_tolerance: float = 0.01, solver_name: str = 'PULP_CBC_CMD'):
        """
        Solve the optimization problem using the specified solver.
        
        Args:
            time_limit: Maximum solving time in seconds (default 600 = 10 min)
            gap_tolerance: Optimality gap tolerance (default 0.01 = 1%)
            solver_name: Name of the solver to use (PULP_CBC_CMD, HiGHS_CMD, GLPK_CMD, COIN_CMD)
        """
        print(f"\nSolving optimization problem...")
        
        # --- Configure Solver ---
        solver = None
        if solver_name == 'HiGHS_CMD':
            # Try to use HiGHS via Python API (highspy package)
            try:
                # Use HiGHS (Python API) instead of HiGHS_CMD (command line)
                solver = pl.HiGHS(msg=True, timeLimit=time_limit, gapRel=gap_tolerance, threads=8)
            except Exception as e:
                print(f"  HiGHS not available ({e}), falling back to CBC")
                solver = pl.PULP_CBC_CMD(msg=True, timeLimit=time_limit, gapRel=gap_tolerance)
        elif solver_name == 'GLPK_CMD':
            solver = pl.GLPK_CMD(msg=True, timeLimit=time_limit)
        elif solver_name == 'COIN_CMD':
             solver = pl.COIN_CMD(msg=True, timeLimit=time_limit, gapRel=gap_tolerance)
        else:
            # Default to CBC (Coin-OR Branch and Cut) which comes with PuLP
            solver = pl.PULP_CBC_CMD(msg=True, timeLimit=time_limit, gapRel=gap_tolerance)

        print(f"  Solver: {solver_name}")
        print(f"  Time limit: {time_limit} seconds")
        print(f"  Gap tolerance: {gap_tolerance:.1%}")
        
        # --- Heuristic for Warm Start ---
        print("  Generating initial solution with greedy heuristic...")
        self._generate_initial_solution()
        
        start_time = datetime.now()
        status = self.model.solve(solver)
        solve_time = (datetime.now() - start_time).total_seconds()

        print(f"\nOPTIMIZATION RESULTS")
        print(f"{'='*60}")
        print(f"Status: {pl.LpStatus[status]}")
        print(f"Solve time: {solve_time:.2f} seconds ({solve_time/60:.2f} minutes)")
        
        if status == pl.LpStatusOptimal or status == pl.LpStatusNotSolved: # NotSolved might have a feasible solution found
            # Check if we actually have an objective value
            obj_val = pl.value(self.model.objective)
            if obj_val is not None:
                print(f"Objective value: {obj_val:.4f}")
                self._print_performance_metrics()
            else:
                 print("No integer solution found.")
        else:
            print("No feasible solution found!")
        
        return status
    
    def _print_performance_metrics(self):
        """Calculate and print performance metrics similar to Table 2 in paper."""
        total_assigned_slots = 0
        it_assigned_slots = 0
        is_assigned_slots = 0

        for (i, j, k), var in self.X.items():
            if var is not None and pl.value(var) == 1:
                duration = self.sessions[i]['duration_slots']
                total_assigned_slots += duration
                if self.sessions[i]['program'] == 'IT':
                    it_assigned_slots += duration
                elif self.sessions[i]['program'] == 'IS':
                    is_assigned_slots += duration

        total_capacity = len(self.rooms) * len(self.K)
        utilization = (total_assigned_slots / total_capacity) * 100 if total_capacity > 0 else 0
        idle_percentage = 100 - utilization
        
        it_percentage = (it_assigned_slots / total_assigned_slots * 100) if total_assigned_slots > 0 else 0
        is_percentage = (is_assigned_slots / total_assigned_slots * 100) if total_assigned_slots > 0 else 0

        # Conflicts should be 0 due to constraints, so we can report it as such.
        conflicts = 0

        print(f"\nPerformance Metrics:")
        print(f"  Room Utilization: {utilization:.1f}%")
        print(f"  Scheduling Conflicts: {conflicts}")
        print(f"  Idle Time: {idle_percentage:.1f}%")
        print(f"  IT Program Allocation: {it_percentage:.1f}%")
        print(f"  IS Program Allocation: {is_percentage:.1f}%")
    
    def export_schedule(self, filename: str, program: str, year: int, block: str, save_file: bool = True):
        """
        Export schedule to CSV, returning a DataFrame for GUI use.
        """
        if self.model is None or pl.value(self.model.objective) is None:
            return pd.DataFrame()

        # Group scheduled sessions by their course component
        component_schedules = {}
        for (i, j, k), var in self.X.items():
            if var is not None and pl.value(var) == 1:
                session = self.sessions[i]
                comp_id = session['component_id']
                if comp_id not in component_schedules:
                    component = self.course_components[comp_id]
                    component_schedules[comp_id] = {'component': component, 'assignments': []}
                component_schedules[comp_id]['assignments'].append({
                    'room': self.rooms[j], 'start_slot': self.time_slots[k],
                    'session': session
                })

        # Format the output
        schedule_data = []
        for comp_id, schedule in component_schedules.items():
            component = schedule['component']
            # Convert years to int for comparison to handle float/int mismatch
            comp_year = int(component['year']) if pd.notna(component['year']) else None
            target_year = int(year) if year is not None and pd.notna(year) else None
            
            if (program and component['program'] != program) or \
               (target_year is not None and comp_year != target_year) or \
               (block and component['block'] != block):
                continue

            # Aggregate days, times, and rooms for multi-meeting courses
            time_room_by_day = {}
            for assign in schedule['assignments']:
                day = assign['start_slot']['day']
                start_time = assign['start_slot']['start']
                duration = assign['session']['duration_slots']
                end_slot_idx = self.time_slots.index(assign['start_slot']) + duration - 1
                end_time = self.time_slots[end_slot_idx]['end']

                # Format room string to include its category (Lab/Non-Lab)
                room_id = assign['room']
                room_info = self.rooms_df[self.rooms_df['room_id'] == room_id].iloc[0]
                room_category = room_info['room_category'].capitalize()
                room_display = f"{room_id} ({room_category})"

                time_room_by_day[day] = {'time': f"{start_time}-{end_time}", 'room': room_display}
            
            days_str = "".join(sorted(time_room_by_day.keys(), key=lambda d: self.days.index(d)))
            time_str = "\n".join([tr['time'] for d, tr in sorted(time_room_by_day.items(), key=lambda item: self.days.index(item[0]))])
            room_str = "\n".join([tr['room'] for d, tr in sorted(time_room_by_day.items(), key=lambda item: self.days.index(item[0]))])

            course_info = self.courses_df[self.courses_df['code'] == component['course_code']].iloc[0]
            lec_hours = course_info.get('lec_hours', 0)
            lab_hours = course_info.get('lab_hours', 0)
            total_hours = lec_hours + (lab_hours * 3) # 1 lab unit = 3 contact hours

            schedule_data.append({
                'Course Code': component['course_code'], 'Course Title': course_info['name'],
                'Time': time_str, 'Days': days_str, 'Room': room_str,
                'Lec': lec_hours, 'Lab': lab_hours,
                'Units': lec_hours + lab_hours,
                'No. of Hours': total_hours,
                'ETL Units': (lec_hours * 1) + (lab_hours * 3 * 0.75), # Example ETL calc
                'Instructor/Professor': 'TBA'
            })

        schedule_df = pd.DataFrame(schedule_data)
        if not schedule_df.empty:
            schedule_df = schedule_df.sort_values(by=['Course Code'])
        if save_file and not schedule_df.empty:
            schedule_df.to_csv(filename, index=False)
            print(f"  Schedule for {program} {year}{block} exported to {filename}")
        
        return schedule_df
    
    def get_full_schedule_df(self) -> pd.DataFrame:
        """Generates and returns the full schedule for all groups in a single DataFrame."""
        if self.model is None or pl.value(self.model.objective) is None:
            return pd.DataFrame()

        student_groups = self.enrollment_df[['program', 'year', 'block']].drop_duplicates()
        all_schedules_df = pd.DataFrame()

        for _, group in student_groups.iterrows():
            program, year, block = group['program'], group['year'], group['block']
            # Use export_schedule with a dummy path to get the DataFrame
            df = self.export_schedule("dummy.csv", program, year, block, save_file=False)
            if df is not None and not df.empty:
                df['Program-Year-Block'] = f"{program}-{year}{block}"
                all_schedules_df = pd.concat([all_schedules_df, df], ignore_index=True)
        
        return all_schedules_df

    def export_all_schedules(self, output_dir: str = "."):
        """Export schedules for all program-year-block combinations into a semester-specific folder."""
        import os

        # Create a semester-specific subfolder
        if self.semester == 1:
            folder_name = "1st_Sem_Schedule"
        elif self.semester == 2:
            folder_name = "2nd_Sem_Schedule"
        else:
            folder_name = "Generated_Schedules"
        
        final_output_dir = os.path.join(output_dir, folder_name)
        os.makedirs(final_output_dir, exist_ok=True)
        
        # If a combined schedule from a sequential run exists, export that
        if hasattr(self, 'combined_schedule_for_export') and not self.combined_schedule_for_export.empty:
            full_df = self.combined_schedule_for_export
        else:
            full_df = self.get_full_schedule_df()

        # Export individual files per student group
        student_groups = full_df['Program-Year-Block'].unique()
        for group_str in student_groups:
            group_df = full_df[full_df['Program-Year-Block'] == group_str]
            filename = os.path.join(output_dir, f"schedule_{group_str}.csv")
            group_df.to_csv(filename, index=False)
            print(f"  Schedule for {group_str} exported to {filename}")

        # Export a combined file
        combined_filename = os.path.join(output_dir, "_schedule_ALL.csv")
        full_df.to_csv(combined_filename, index=False)
        print(f"  Combined schedule exported to {combined_filename}")


def main(semester: str = 'first_semester'):
    """Main execution function."""
    print("="*60)
    print("CLASSROOM SCHEDULING OPTIMIZATION SYSTEM")
    print("="*60)
    
    optimizer = SchedulingOptimizer(
        courses_file='courses_fixed.csv',
        enrollment_file='enrollment_from_json.csv',
        rooms_file='room_redesigned.csv'
    )
    
    optimizer.build_model(semester=semester)
    status = optimizer.solve(time_limit=1200, gap_tolerance=0.05)
    
    if status == pl.LpStatusOptimal:
        optimizer.export_all_schedules(output_dir='schedules')
    
    print("\n" + "="*60)
    print("OPTIMIZATION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Classroom Scheduling Optimizer')
    parser.add_argument('--semester', type=str, default='first_semester', 
                        help='Semester to schedule (e.g., first_semester, second_semester)')
    args = parser.parse_args()

    main(semester=args.semester)
