"""
Experimental OR-Tools CP-SAT based classroom scheduler.

This module is designed to coexist with the existing PuLP/HiGHS-based
`scheduler.py` implementation. It reuses the same CSV inputs:

- courses_full.csv
- enrollment_full.csv
- rooms_full.csv

and the same 8:00–12:00 / 13:00–17:00 time window with 30-minute base slots.

NOTE:
- This is an initial version focusing on core hard constraints:
  * no room conflicts
  * no student group conflicts
  * room capacity and room_category matching
  * 8–12 / 13–17 schedule with lunch break respected via valid start slots
- It reuses the same multi-pattern session structure (lecture + lab patterns)
  as in the PuLP model, but does not yet implement all fairness/soft
  objectives.
- Requires: `pip install ortools`.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from ortools.sat.python import cp_model


@dataclass
class Session:
    id: int
    pattern_id: int
    component_id: int
    duration_slots: int
    day_pattern: str
    course_code: str
    session_type: str
    program: str
    year: int
    block: str
    students: int
    room_category: str


class OrToolsScheduler:
    def __init__(
        self,
        courses_file: str,
        enrollment_file: str,
        rooms_file: str,
        semester: int = 1,
        program_filter: List[str] | None = None,
    ) -> None:
        self.courses_file = courses_file
        self.enrollment_file = enrollment_file
        self.rooms_file = rooms_file
        self.semester = semester

        # Load data
        self.courses_df = pd.read_csv(courses_file)
        self.enrollment_df = pd.read_csv(enrollment_file)
        self.rooms_df = pd.read_csv(rooms_file)

        # Normalize year columns
        if "year" in self.courses_df.columns:
            self.courses_df["year"] = (
                pd.to_numeric(self.courses_df["year"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
        if "year" in self.enrollment_df.columns:
            self.enrollment_df["year"] = (
                pd.to_numeric(self.enrollment_df["year"], errors="coerce")
                .fillna(0)
                .astype(int)
            )

        if program_filter:
            self.enrollment_df = self.enrollment_df[
                self.enrollment_df["program"].isin(program_filter)
            ]

        # Time slots: 8–12, 13–17, 30-minute slots, Monday–Friday
        self.days = ["M", "T", "W", "TH", "F"]
        self.time_slots = self._generate_time_slots()
        self.time_slots_per_day = len(self.time_slots) // len(self.days)

        # Will be populated by _generate_class_sections
        self.course_components: List[Dict] = []
        self.patterns: List[Dict] = []
        self.sessions: List[Session] = []

        # OR-Tools model related
        self.model: cp_model.CpModel | None = None
        self.X: Dict[Tuple[int, int, int], cp_model.IntVar] = {}
        self.Y: Dict[int, cp_model.IntVar] = {}
        self.valid_starts: Dict[int, List[int]] = {}
        self.slot_occupation: Dict[Tuple[int, int], List[int]] = {}

    # ------------------------------------------------------------------
    # Time slots and session configs (mirrors scheduler.py)
    # ------------------------------------------------------------------
    def _generate_time_slots(self) -> List[Dict]:
        slots: List[Dict] = []
        slot_id = 0
        times = [
            ("08:00", "08:30"), ("08:30", "09:00"),
            ("09:00", "09:30"), ("09:30", "10:00"),
            ("10:00", "10:30"), ("10:30", "11:00"),
            ("11:00", "11:30"), ("11:30", "12:00"),
            ("13:00", "13:30"), ("13:30", "14:00"),
            ("14:00", "14:30"), ("14:30", "15:00"),
            ("15:00", "15:30"), ("15:30", "16:00"),
            ("16:00", "16:30"), ("16:30", "17:00"),
        ]
        for day in self.days:
            for start, end in times:
                slots.append({
                    "day": day,
                    "start": start,
                    "end": end,
                    "slot_id": slot_id,
                })
                slot_id += 1
        return slots

    def _get_session_configs(self, course: Dict) -> List[Dict]:
        code = course["code"]
        lec_hours = course.get("lec_hours", 0)
        lab_hours = course.get("lab_hours", 0)
        configs: List[Dict] = []

        # Practicum special case
        if code == "IT 128" or code == "IS 404":
            configs.append({"type": "lecture", "duration": 2, "pattern": "2_days", "meetings": 2})
            configs.append({"type": "lecture", "duration": 4, "pattern": "single_day", "meetings": 1})
            return configs

        # PathFit: 2-hour single block once per week
        if str(code).startswith("PathFit"):
            configs.append({"type": "lecture", "duration": 4, "pattern": "single_day", "meetings": 1})
            return configs

        # Lecture sessions
        if lec_hours > 0:
            if lab_hours == 0:
                # Pure lecture (3hrs/week)
                configs.append({"type": "lecture", "duration": 3, "pattern": "2_days", "meetings": 2})
                configs.append({"type": "lecture", "duration": 2, "pattern": "MWF", "meetings": 3})
            else:
                # Lecture for courses with lab (2hrs/week)
                configs.append({"type": "lecture", "duration": 2, "pattern": "2_days", "meetings": 2})
                configs.append({"type": "lecture", "duration": 4, "pattern": "single_day", "meetings": 1})

        # Lab sessions: always 3hrs/week
        if lab_hours > 0:
            configs.append({"type": "lab", "duration": 3, "pattern": "2_days", "meetings": 2})
            configs.append({"type": "lab", "duration": 2, "pattern": "MWF", "meetings": 3})

        return configs

    def _generate_class_sections(self, semester: int | None = None) -> None:
        self.course_components = []
        self.patterns = []
        self.sessions = []

        component_id = 0
        pattern_id = 0
        session_id = 0

        all_courses = self.courses_df
        if semester is not None and "semester" in all_courses.columns:
            all_courses = all_courses[all_courses["semester"] == semester]

        for _, enroll in self.enrollment_df.iterrows():
            program = enroll["program"]
            year = int(enroll["year"])
            block = enroll["block"]
            students = int(enroll["students"])

            program_courses = all_courses[
                (all_courses["program"] == program)
                & (all_courses["year"] == year)
            ]

            for _, course in program_courses.iterrows():
                code = course["code"]

                # Skip NSTP courses (scheduled separately)
                if str(code).startswith("NSTP"):
                    continue

                room_category = course.get("room_category", "non-lab")
                type_configs = self._get_session_configs(course)

                # Create component entry
                comp = {
                    "id": component_id,
                    "course_code": code,
                    "session_type": "mixed",
                    "program": program,
                    "year": year,
                    "block": block,
                    "students": students,
                    "room_category": room_category,
                }
                self.course_components.append(comp)

                for cfg in type_configs:
                    pat = {
                        "id": pattern_id,
                        "component_id": component_id,
                        "pattern_name": f"{cfg['pattern']}_{cfg['duration']}x{cfg['meetings']}",
                    }
                    self.patterns.append(pat)

                    for _ in range(cfg["meetings"]):
                        self.sessions.append(
                            Session(
                                id=session_id,
                                pattern_id=pattern_id,
                                component_id=component_id,
                                duration_slots=cfg["duration"],
                                day_pattern=cfg["pattern"],
                                course_code=code,
                                session_type=cfg["type"],
                                program=program,
                                year=year,
                                block=block,
                                students=students,
                                room_category=room_category,
                            )
                        )
                        session_id += 1

                    pattern_id += 1

                component_id += 1

    # ------------------------------------------------------------------
    # Valid starts and occupation (mirrors scheduler.py logic)
    # ------------------------------------------------------------------
    def _get_valid_start_slots_for_pattern(self, session: Session) -> List[int]:
        day_pattern = session.day_pattern
        duration = session.duration_slots
        valid_starts: List[int] = []

        if day_pattern in ("single_day", "flexible"):
            valid_days = ["M", "T", "W", "TH", "F"]
        elif day_pattern == "MWF":
            valid_days = ["M", "W", "F"]
        elif day_pattern == "2_days" or day_pattern == "MW":
            valid_days = ["M", "T", "W", "TH", "F"]
        else:
            valid_days = ["M", "T", "W", "TH", "F"]

        for k, slot_info in enumerate(self.time_slots):
            day = slot_info["day"]
            start_time = slot_info["start"]

            # Heuristic: restrict start times
            minute = int(start_time.split(":")[1])
            if duration == 2 and minute != 0:
                continue
            if duration == 3:
                if start_time not in ["08:00", "09:30", "13:00", "14:30"]:
                    continue
            if duration > 3 and minute != 0:
                continue

            if day not in valid_days:
                continue

            end_slot_index = k + duration - 1
            if (
                end_slot_index >= len(self.time_slots)
                or self.time_slots[end_slot_index]["day"] != day
            ):
                continue

            # Lunch break guard: prevent spanning 12:00–13:00
            end_time = self.time_slots[end_slot_index]["end"]
            if start_time < "12:00" and end_time > "12:00":
                continue

            valid_starts.append(k)

        return valid_starts

    # ------------------------------------------------------------------
    # Model building and solving
    # ------------------------------------------------------------------
    def build_model(self) -> None:
        self._generate_class_sections(self.semester)
        self.model = cp_model.CpModel()

        # Rooms list
        self.rooms = list(self.rooms_df["room_id"].tolist())

        # Precompute valid starts and slot occupation
        self.valid_starts = {}
        self.slot_occupation = {}
        for sess in self.sessions:
            starts = self._get_valid_start_slots_for_pattern(sess)
            self.valid_starts[sess.id] = starts
            for k_start in starts:
                self.slot_occupation[(sess.id, k_start)] = [
                    k_start + offset for offset in range(sess.duration_slots)
                ]

        # Decision variables
        self.Y = {}
        for pat in self.patterns:
            self.Y[pat["id"]] = self.model.NewBoolVar(f"Y_{pat['id']}")

        self.X = {}
        for sess in self.sessions:
            for j, room_id in enumerate(self.rooms):
                room_row = self.rooms_df[self.rooms_df["room_id"] == room_id]
                if room_row.empty:
                    continue
                capacity = int(room_row["capacity"].iloc[0])
                if sess.students > capacity:
                    continue
                # room_category matching
                room_cat = str(room_row["room_category"].iloc[0])
                if sess.room_category == "lab" and room_cat != "lab":
                    continue
                if sess.room_category == "non-lab" and room_cat != "non-lab":
                    continue

                for k in self.valid_starts.get(sess.id, []):
                    var = self.model.NewBoolVar(f"X_{sess.id}_{j}_{k}")
                    self.X[(sess.id, j, k)] = var

        # 1. Pattern selection: exactly one pattern per component
        for comp in self.course_components:
            pids = [p["id"] for p in self.patterns if p["component_id"] == comp["id"]]
            if pids:
                self.model.Add(sum(self.Y[p] for p in pids) == 1)

        # 2. Session assignment: each session scheduled iff its pattern is chosen
        for pat in self.patterns:
            pid = pat["id"]
            sess_ids = [s.id for s in self.sessions if s.pattern_id == pid]
            for s_id in sess_ids:
                vars_for_sess: List[cp_model.IntVar] = []
                for j, _room in enumerate(self.rooms):
                    for k in self.valid_starts.get(s_id, []):
                        v = self.X.get((s_id, j, k))
                        if v is not None:
                            vars_for_sess.append(v)
                if vars_for_sess:
                    self.model.Add(sum(vars_for_sess) == self.Y[pid])
                else:
                    # If no feasible assignment, force pattern off
                    self.model.Add(self.Y[pid] == 0)

        # 3. Room conflict constraints
        room_slot_assignments: Dict[Tuple[int, int], List[cp_model.IntVar]] = {}
        for (s_id, j, k), var in self.X.items():
            for slot in self.slot_occupation.get((s_id, k), []):
                key = (j, slot)
                room_slot_assignments.setdefault(key, []).append(var)

        for key, vars_at_slot in room_slot_assignments.items():
            if len(vars_at_slot) > 1:
                self.model.Add(sum(vars_at_slot) <= 1)

        # 4. Student group conflict constraints
        group_slot_assignments: Dict[Tuple[Tuple[str, int, str], int], List[cp_model.IntVar]] = {}
        for (s_id, j, k), var in self.X.items():
            sess = next(s for s in self.sessions if s.id == s_id)
            group_key = (sess.program, sess.year, sess.block)
            for slot in self.slot_occupation.get((s_id, k), []):
                key = (group_key, slot)
                group_slot_assignments.setdefault(key, []).append(var)

        for key, vars_at_slot in group_slot_assignments.items():
            if len(vars_at_slot) > 1:
                self.model.Add(sum(vars_at_slot) <= 1)

        # Objective: maximize number of chosen patterns (scheduled components)
        self.model.Maximize(sum(self.Y.values()))

    def solve(self, time_limit: int = 600) -> Tuple[cp_model.CpSolver, cp_model.CpSolverStatus]:
        if self.model is None:
            self.build_model()

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(time_limit)
        solver.parameters.num_search_workers = 0  # use all cores

        print("Solving CP-SAT model (OR-Tools)...")
        start = datetime.now()
        status = solver.Solve(self.model)
        elapsed = (datetime.now() - start).total_seconds()
        print(f"Status: {solver.StatusName(status)}")
        print(f"Solve time: {elapsed:.2f} seconds")
        print(f"Objective value (scheduled components): {solver.ObjectiveValue():.1f}")

        return solver, status

    def extract_schedule(self, solver: cp_model.CpSolver) -> pd.DataFrame:
        """Extract schedule as a DataFrame similar to CSV output in PuLP version."""
        rows = []
        for (s_id, j, k), var in self.X.items():
            if solver.BooleanValue(var):
                sess = next(s for s in self.sessions if s.id == s_id)
                slot_ids = self.slot_occupation.get((s_id, k), [])
                if not slot_ids:
                    continue
                first_slot = self.time_slots[slot_ids[0]]
                last_slot = self.time_slots[slot_ids[-1]]
                day = first_slot["day"]
                time_str = f"{first_slot['start']}-{last_slot['end']}"
                room_id = self.rooms[j]

                # Look up course title
                course_row = self.courses_df[self.courses_df["code"] == sess.course_code]
                if not course_row.empty:
                    title = course_row["name"].iloc[0]
                    lec_hours = int(course_row.get("lec_hours", pd.Series([0])).iloc[0])
                    lab_hours = int(course_row.get("lab_hours", pd.Series([0])).iloc[0])
                else:
                    title = ""
                    lec_hours = 0
                    lab_hours = 0

                # Match scheduler.py semantics
                units = lec_hours + lab_hours
                total_hours = lec_hours + lab_hours * 3  # 1 lab unit = 3 contact hours
                etl_units = (lec_hours * 1) + (lab_hours * 3 * 0.75)

                prog_year_block = f"{sess.program}-{sess.year}{sess.block}"

                rows.append({
                    "Course Code": sess.course_code,
                    "Course Title": title,
                    "Time": time_str,
                    "Days": day,
                    "Room": room_id,
                    "Lec": lec_hours,
                    "Lab": lab_hours,
                    "Units": units,
                    "No. of Hours": total_hours,
                    "ETL Units": etl_units,
                    "Instructor/Professor": "TBA",
                    "Program-Year-Block": prog_year_block,
                })

        return pd.DataFrame(rows)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="OR-Tools CP-SAT scheduler (experimental)")
    parser.add_argument("--courses", default="courses_full.csv")
    parser.add_argument("--enrollment", default="enrollment_full.csv")
    parser.add_argument("--rooms", default="rooms_full.csv")
    parser.add_argument("--semester", type=int, default=1)
    parser.add_argument("--time_limit", type=int, default=600)
    parser.add_argument("--output", default="schedule_ortools.csv")
    args = parser.parse_args()

    sched = OrToolsScheduler(
        courses_file=args.courses,
        enrollment_file=args.enrollment,
        rooms_file=args.rooms,
        semester=args.semester,
    )
    sched.build_model()
    solver, status = sched.solve(time_limit=args.time_limit)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        df = sched.extract_schedule(solver)

        # Always write the raw combined output requested by --output
        out_path = args.output
        df.to_csv(out_path, index=False)
        print(f"Schedule exported to {out_path}")

        # Mirror scheduler.py: write per-group and combined files into a
        # semester-specific folder so GUI v3 can load them easily.
        import os

        base_dir = os.path.dirname(out_path) or "."
        if sched.semester == 1:
            folder_name = "1st_Sem_Schedule"
        elif sched.semester == 2:
            folder_name = "2nd_Sem_Schedule"
        else:
            folder_name = "Generated_Schedules"

        final_output_dir = os.path.join(base_dir, folder_name)
        os.makedirs(final_output_dir, exist_ok=True)

        # Per Program-Year-Block files
        if "Program-Year-Block" in df.columns:
            for group in sorted(df["Program-Year-Block"].dropna().unique()):
                group_df = df[df["Program-Year-Block"] == group]
                filename = os.path.join(final_output_dir, f"schedule_{group}.csv")
                group_df.to_csv(filename, index=False)
                print(f"  Schedule for {group} exported to {filename}")

        # Combined file in the same folder
        combined_filename = os.path.join(final_output_dir, "_schedule_ALL.csv")
        df.to_csv(combined_filename, index=False)
        print(f"  Combined schedule exported to {combined_filename}")
    else:
        print("No feasible schedule found by OR-Tools model.")


if __name__ == "__main__":
    main()
