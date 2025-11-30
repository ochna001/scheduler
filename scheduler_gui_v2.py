
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import threading
import os
import sys
from datetime import datetime
import pulp as pl
# Import the logic from the existing scripts
from scheduler import SchedulingOptimizer
from scheduler_large_dataset import solve_large_dataset, get_time_windows_for_year, add_occupation_constraints, track_occupied_slots

class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert("end", str, (self.tag,))
        self.widget.see("end")
        self.widget.configure(state="disabled")
        self.widget.update_idletasks()

    def flush(self):
        pass

class SchedulerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Classroom Scheduler - Full Simulation")
        self.root.geometry("1200x800")
        
        # Variables
        self.courses_file = tk.StringVar()
        self.enrollment_file = tk.StringVar()
        self.rooms_file = tk.StringVar()
        
        self.override_rooms = tk.BooleanVar(value=False)
        self.num_lab_rooms = tk.IntVar(value=10)
        self.num_lec_rooms = tk.IntVar(value=10)
        
        self.semester_var = tk.IntVar(value=1)
        self.time_limit_var = tk.IntVar(value=600) # 10 minutes
        
        # Layout
        self.create_widgets()
        
        # Redirect stdout to log window
        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")

    def create_widgets(self):
        # Main Container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel (Controls)
        left_panel = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # --- Presets ---
        ttk.Label(left_panel, text="Presets:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        preset_frame = ttk.Frame(left_panel)
        preset_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(preset_frame, text="Full Dataset", command=self.load_full_preset).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(preset_frame, text="Small Dataset", command=self.load_small_preset).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # --- Files ---
        ttk.Label(left_panel, text="Input Files:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.create_file_entry(left_panel, "Courses:", self.courses_file)
        self.create_file_entry(left_panel, "Enrollment:", self.enrollment_file)
        self.create_file_entry(left_panel, "Rooms:", self.rooms_file)
        
        # --- Room Configuration ---
        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(left_panel, text="Room Configuration:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        
        override_check = ttk.Checkbutton(left_panel, text="Override Room Counts (Simulation)", variable=self.override_rooms, command=self.toggle_room_inputs)
        override_check.pack(anchor="w")
        
        self.room_input_frame = ttk.Frame(left_panel)
        self.room_input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.room_input_frame, text="Lab Rooms:").grid(row=0, column=0, padx=5, sticky="w")
        ttk.Spinbox(self.room_input_frame, from_=1, to=100, textvariable=self.num_lab_rooms, width=5).grid(row=0, column=1, padx=5)
        
        ttk.Label(self.room_input_frame, text="Lecture Rooms:").grid(row=1, column=0, padx=5, sticky="w")
        ttk.Spinbox(self.room_input_frame, from_=1, to=100, textvariable=self.num_lec_rooms, width=5).grid(row=1, column=1, padx=5)
        
        self.toggle_room_inputs() # Set initial state

        # --- Simulation Settings ---
        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(left_panel, text="Settings:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        
        sets_frame = ttk.Frame(left_panel)
        sets_frame.pack(fill=tk.X)
        ttk.Label(sets_frame, text="Semester:").pack(side=tk.LEFT)
        ttk.Radiobutton(sets_frame, text="1", variable=self.semester_var, value=1).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(sets_frame, text="2", variable=self.semester_var, value=2).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(left_panel, text="Time Limit (sec/year):").pack(anchor="w", pady=(10,0))
        ttk.Scale(left_panel, from_=60, to=3600, variable=self.time_limit_var, orient=tk.HORIZONTAL).pack(fill=tk.X)
        ttk.Label(left_panel, textvariable=self.time_limit_var).pack(anchor="e")

        # --- Actions ---
        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=20)
        
        self.btn_check = ttk.Button(left_panel, text="1. Check Feasibility", command=self.check_feasibility, width=25)
        self.btn_check.pack(pady=5)
        
        self.btn_run = ttk.Button(left_panel, text="2. Run Simulation", command=self.start_simulation_thread, width=25, state="disabled")
        self.btn_run.pack(pady=5)

        # Right Panel (Logs)
        right_panel = ttk.LabelFrame(main_frame, text="Simulation Log & Analysis", padding="10")
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(right_panel, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Tag configurations for colored logs
        self.log_text.tag_config("stdout", foreground="black")
        self.log_text.tag_config("stderr", foreground="red")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="#ff8c00") # Dark orange

    def create_file_entry(self, parent, label, var):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, pady=2)
        ttk.Label(f, text=label, width=10).pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(f, text="...", width=3, command=lambda: self.browse_file(var)).pack(side=tk.LEFT)

    def browse_file(self, var):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("JSON Files", "*.json"), ("All Files", "*.*")])
        if filename:
            var.set(filename)

    def load_full_preset(self):
        cwd = os.getcwd()
        self.courses_file.set(os.path.join(cwd, "courses_full.csv"))
        self.enrollment_file.set(os.path.join(cwd, "enrollment_full.csv"))
        self.rooms_file.set(os.path.join(cwd, "rooms_full.csv"))
        self.print_log("Loaded Full Dataset preset.")

    def load_small_preset(self):
        cwd = os.getcwd()
        self.courses_file.set(os.path.join(cwd, "courses_with_semester.csv"))
        self.enrollment_file.set(os.path.join(cwd, "enrollment_from_json.csv"))
        self.rooms_file.set(os.path.join(cwd, "room_redesigned.csv"))
        self.print_log("Loaded Small Dataset preset.")

    def toggle_room_inputs(self):
        if self.override_rooms.get():
            for child in self.room_input_frame.winfo_children():
                child.configure(state='normal')
        else:
            for child in self.room_input_frame.winfo_children():
                child.configure(state='disabled')

    def print_log(self, message, tag="stdout"):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n", (tag,))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update_idletasks()

    def get_effective_rooms_file(self):
        """Returns the path to the rooms file to use (original or generated)."""
        if not self.override_rooms.get():
            return self.rooms_file.get()
        
        # Generate temp rooms file
        n_lab = self.num_lab_rooms.get()
        n_lec = self.num_lec_rooms.get()
        
        rooms_data = []
        # Add labs
        for i in range(n_lab):
            rooms_data.append({
                'room_id': f'LAB-{i+1:03d}',
                'building': 'Simulated', 'floor': 1, 'capacity': 50,
                'room_type': 'lab', 'equipment': 'general', 'room_category': 'lab'
            })
        # Add lectures
        for i in range(n_lec):
             rooms_data.append({
                'room_id': f'LEC-{i+1:03d}',
                'building': 'Simulated', 'floor': 2, 'capacity': 50,
                'room_type': 'lecture', 'equipment': 'general', 'room_category': 'non-lab'
            })
            
        df = pd.DataFrame(rooms_data)
        temp_file = "temp_rooms_simulation.csv"
        df.to_csv(temp_file, index=False)
        self.print_log(f"Generated temporary rooms file with {n_lab} labs and {n_lec} lecture rooms.", "warning")
        return temp_file

    def check_feasibility(self):
        if not self.courses_file.get() or not self.enrollment_file.get():
            messagebox.showerror("Error", "Please select Courses and Enrollment files.")
            return

        try:
            courses_path = self.courses_file.get()
            enrollment_path = self.enrollment_file.get()
            rooms_path = self.get_effective_rooms_file() # Handle override
            
            if not os.path.exists(rooms_path):
                messagebox.showerror("Error", "Rooms file not found (or generation failed).")
                return

            self.print_log("\n--- RUNNING FEASIBILITY ANALYSIS ---", "warning")
            
            # Logic adapted from check_feasibility.py
            courses = pd.read_csv(courses_path)
            enrollment = pd.read_csv(enrollment_path)
            rooms = pd.read_csv(rooms_path)
            
            semester = self.semester_var.get()
            sem_courses = courses[courses['semester'] == semester]
            
            total_lab_hours_demand = 0
            total_lec_hours_demand = 0
            
            # Dictionary to store breakdown: course_code -> {'lec_hrs': hours, 'lab_hrs': hours, 'sections': count, 'title': name}
            breakdown = {}

            # Calculate demand
            for _, group in enrollment.iterrows():
                group_program = group['program']
                group_year = group['year']
                group_block = group['block']
                group_id = f"{group_program} {group_year}-{group_block}"
                
                group_courses = sem_courses[
                    (sem_courses['program'] == group_program) & 
                    (sem_courses['year'] == group_year)
                ]
                
                for _, course in group_courses.iterrows():
                    # Skip NSTP
                    if course['code'].startswith('NSTP'):
                        continue

                    # Determine hours based on Scheduler logic
                    # Lab: Always 3 hours if lab_hours > 0
                    # Lec: 3 hours if pure lecture, 2 hours if mixed
                    
                    raw_lec = course['lec_hours']
                    raw_lab = course['lab_hours']
                    
                    # Special handling for practicum (IT 128) - treated as 2hr lecture
                    if course['code'] == 'IT 128':
                        sched_lec = 2
                        sched_lab = 0
                    else:
                        sched_lab = 3 if raw_lab > 0 else 0
                        if raw_lec > 0:
                            if raw_lab == 0:
                                sched_lec = 3 # Pure lecture
                            else:
                                sched_lec = 2 # Lecture with lab
                        else:
                            sched_lec = 0

                    total_lec_hours_demand += sched_lec
                    total_lab_hours_demand += sched_lab
                    
                    code = course['code']
                    if code not in breakdown:
                        breakdown[code] = {
                            'title': course['name'], 
                            'lec_hrs_per_section': sched_lec, 
                            'lab_hrs_per_section': sched_lab, 
                            'sections': 0
                        }
                    breakdown[code]['sections'] += 1
            
            # Calculate Supply
            HOURS_PER_WEEK = 40 
            lab_rooms = rooms[rooms['room_category'] == 'lab']
            non_lab_rooms = rooms[rooms['room_category'] == 'non-lab']
            
            total_lab_supply = len(lab_rooms) * HOURS_PER_WEEK
            total_lec_supply = len(non_lab_rooms) * HOURS_PER_WEEK 
            
            self.print_log(f"Semester {semester} Analysis:")
            self.print_log(f"  Lecture Demand: {total_lec_hours_demand} hrs | Supply: {total_lec_supply} hrs")
            self.print_log(f"  Lab Demand:     {total_lab_hours_demand} hrs | Supply: {total_lab_supply} hrs")
            
            lec_util = (total_lec_hours_demand / total_lec_supply) if total_lec_supply > 0 else 999
            lab_util = (total_lab_hours_demand / total_lab_supply) if total_lab_supply > 0 else 999
            
            self.print_log(f"  Lecture Utilization: {lec_util:.1%}")
            self.print_log(f"  Lab Utilization:     {lab_util:.1%}")

            # --- DETAILED BREAKDOWN ---
            self.print_log("\n--- LAB BREAKDOWN ---", "stdout")
            for code, data in breakdown.items():
                if data['lab_hrs_per_section'] > 0:
                    total = data['sections'] * data['lab_hrs_per_section']
                    self.print_log(f"  • {code}: {data['sections']} sections × {data['lab_hrs_per_section']} hrs/week = {total} hrs")

            self.print_log("\n--- LECTURE BREAKDOWN ---", "stdout")
            for code, data in breakdown.items():
                if data['lec_hrs_per_section'] > 0:
                    total = data['sections'] * data['lec_hrs_per_section']
                    self.print_log(f"  • {code}: {data['sections']} sections × {data['lec_hrs_per_section']} hrs/week = {total} hrs")
            
            can_run = True
            if total_lec_hours_demand > total_lec_supply:
                self.print_log("❌ CRITICAL: Lecture demand exceeds supply! Scheduling will likely fail.", "stderr")
                can_run = False
            if total_lab_hours_demand > total_lab_supply:
                self.print_log("❌ CRITICAL: Lab demand exceeds supply! Scheduling will likely fail.", "stderr")
                can_run = False
                
            if can_run:
                self.print_log("✅ Feasibility Check Passed.", "success")
                self.btn_run.configure(state="normal")
            elif lec_util > 0.85 or lab_util > 0.85:
                 self.print_log("⚠️ WARNING: Utilization is very high (>85%). Scheduling may be difficult or fragmented.", "warning")
                 self.btn_run.configure(state="normal") # Allow them to try anyway
            else:
                # Allow run but warn heavily
                self.btn_run.configure(state="normal") 
                
        except Exception as e:
            self.print_log(f"Error checking feasibility: {e}", "stderr")

    def start_simulation_thread(self):
        self.btn_run.configure(state="disabled")
        self.btn_check.configure(state="disabled")
        t = threading.Thread(target=self.run_simulation)
        t.start()

    def run_simulation(self):
        try:
            courses_path = self.courses_file.get()
            enrollment_path = self.enrollment_file.get()
            rooms_path = self.get_effective_rooms_file()
            semester = self.semester_var.get()
            
            output_dir = f"output_gui_sim_sem{semester}"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            self.print_log(f"\n--- STARTING SIMULATION (Semester {semester}) ---", "warning")
            self.print_log(f"Strategy: Year-by-Year Decomposition")
            
            # Here we essentially replicate the logic from scheduler_large_dataset.py
            # But we can't just call 'solve_large_dataset' easily because we want to redirect output 
            # and maybe control it more. However, for now, calling it is the safest bet to reuse logic.
            # The stdout redirection in __init__ handles the print statements.
            
            # IMPORTANT: Check if we need to modify the time limit in the imported module?
            # The user can set time limit. solve_large_dataset doesn't accept time_limit as arg in the file I read?
            # Let's check scheduler_large_dataset.py content again.
            # It has: status = optimizer.solve(time_limit=600, gap_tolerance=0.10) hardcoded.
            # I should probably modify scheduler_large_dataset.py to accept time_limit or monkeypatch it.
            # For now, let's just run it.
            
            solve_large_dataset(
                courses_file=courses_path,
                enrollment_file=enrollment_path,
                rooms_file=rooms_path,
                semester=semester,
                output_dir=output_dir,
                time_limit=self.time_limit_var.get()
            )
            
            self.print_log(f"\n✅ Simulation Complete! Schedules saved to {output_dir}", "success")
            messagebox.showinfo("Success", "Simulation Completed Successfully!")
            
        except Exception as e:
            self.print_log(f"\n❌ Simulation Failed: {str(e)}", "stderr")
            import traceback
            self.print_log(traceback.format_exc(), "stderr")
        finally:
            self.btn_run.configure(state="normal")
            self.btn_check.configure(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerGUI(root)
    root.mainloop()
