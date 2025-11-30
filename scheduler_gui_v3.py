
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import threading
import os
import sys
import time
import pulp as pl
from datetime import datetime
# Import the logic from the existing scripts
from scheduler import SchedulingOptimizer
from scheduler_large_dataset import solve_large_dataset

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
        self.root.geometry("1400x900")
        
        # Variables
        self.courses_file = tk.StringVar()
        self.enrollment_file = tk.StringVar()
        self.rooms_file = tk.StringVar()
        
        self.override_rooms = tk.BooleanVar(value=False)
        self.num_lab_rooms = tk.IntVar(value=10)
        self.num_lec_rooms = tk.IntVar(value=10)
        
        self.semester_var = tk.IntVar(value=1)
        self.time_limit_var = tk.IntVar(value=600) # 10 minutes
        self.gap_tolerance_var = tk.DoubleVar(value=5.0)  # 5% gap tolerance
        self.solver_var = tk.StringVar(value="PULP_CBC_CMD")
        
        self.schedules_data = []
        self.optimizer = None # Store optimizer reference
        
        # Timer variables
        self.timer_running = False
        self.timer_start = None
        self.simulation_stopped = False  # Flag to stop simulation between years

        # Layout
        self.create_widgets()
        
        # Redirect stdout to log window
        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")

    def create_widgets(self):
        # Main Container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Main Split: Left (Config) vs Right (Logs & Results)
        main_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # --- LEFT PANEL ---
        left_panel = ttk.LabelFrame(main_paned, text="Configuration", padding="10")
        main_paned.add(left_panel, weight=1) # Config panel takes less space
        
        # Presets
        ttk.Label(left_panel, text="Presets:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        preset_frame = ttk.Frame(left_panel)
        preset_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(preset_frame, text="Full Dataset", command=self.load_full_preset).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(preset_frame, text="Small Dataset", command=self.load_small_preset).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Files
        ttk.Label(left_panel, text="Input Files:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.create_file_entry(left_panel, "Courses:", self.courses_file)
        self.create_file_entry(left_panel, "Enrollment:", self.enrollment_file)
        self.create_file_entry(left_panel, "Rooms:", self.rooms_file)
        
        # Room Config
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
        
        self.toggle_room_inputs()

        # Settings
        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(left_panel, text="Settings:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        
        sets_frame = ttk.Frame(left_panel)
        sets_frame.pack(fill=tk.X)
        ttk.Label(sets_frame, text="Semester:").pack(side=tk.LEFT)
        ttk.Radiobutton(sets_frame, text="1", variable=self.semester_var, value=1).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(sets_frame, text="2", variable=self.semester_var, value=2).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(left_panel, text="Time Limit (seconds/year):").pack(anchor="w", pady=(10,0))
        
        # Helper to snap slider to 60s increments
        def snap_slider(val):
            val = float(val)
            snapped = round(val / 60) * 60
            self.time_limit_var.set(int(snapped))

        scale = ttk.Scale(left_panel, from_=60, to=3600, variable=self.time_limit_var, orient=tk.HORIZONTAL, command=snap_slider)
        scale.pack(fill=tk.X)
        ttk.Label(left_panel, textvariable=self.time_limit_var).pack(anchor="e")
        
        # Gap Tolerance Slider
        ttk.Label(left_panel, text="Gap Tolerance (%):").pack(anchor="w", pady=(10,0))
        
        def update_gap_label(val):
            self.gap_tolerance_var.set(round(float(val), 1))
        
        gap_scale = ttk.Scale(left_panel, from_=0.1, to=20.0, variable=self.gap_tolerance_var, orient=tk.HORIZONTAL, command=update_gap_label)
        gap_scale.pack(fill=tk.X)
        gap_label_frame = ttk.Frame(left_panel)
        gap_label_frame.pack(fill=tk.X)
        ttk.Label(gap_label_frame, textvariable=self.gap_tolerance_var).pack(side=tk.LEFT)
        ttk.Label(gap_label_frame, text="% (lower = more optimal, higher = faster/more random)").pack(side=tk.LEFT, padx=5)
        
        # Solver Selection
        ttk.Label(left_panel, text="Solver:").pack(anchor="w", pady=(5,0))
        solver_combo = ttk.Combobox(left_panel, textvariable=self.solver_var, state="readonly")
        solver_combo['values'] = ("PULP_CBC_CMD", "HiGHS_CMD", "GLPK_CMD", "COIN_CMD")
        solver_combo.pack(fill=tk.X)

        # Strategy Selection
        ttk.Label(left_panel, text="Strategy:").pack(anchor="w", pady=(5,0))
        self.strategy_var = tk.StringVar(value="Sequential (Year-by-Year)")
        strategy_combo = ttk.Combobox(left_panel, textvariable=self.strategy_var, state="readonly")
        strategy_combo['values'] = ("Sequential (Year-by-Year)", "Global (All-at-Once)")
        strategy_combo.pack(fill=tk.X)
        
        # Actions
        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=20)
        
        self.btn_check = ttk.Button(left_panel, text="1. Check Feasibility", command=self.check_feasibility, width=25)
        self.btn_check.pack(pady=5)
        
        self.btn_run = ttk.Button(left_panel, text="2. Run Simulation", command=self.start_simulation_thread, width=25, state="disabled")
        self.btn_run.pack(pady=5)
        
        self.btn_stop = ttk.Button(left_panel, text="⏹ Stop Simulation", command=self.stop_simulation, width=25, state="disabled")
        self.btn_stop.pack(pady=5)
        
        # Timer display
        timer_frame = ttk.Frame(left_panel)
        timer_frame.pack(fill=tk.X, pady=10)
        ttk.Label(timer_frame, text="⏱ Elapsed:").pack(side=tk.LEFT)
        self.timer_label = ttk.Label(timer_frame, text="00:00:00", font=("Consolas", 12, "bold"))
        self.timer_label.pack(side=tk.LEFT, padx=5)
        
        # Status indicator
        self.status_label = ttk.Label(timer_frame, text="", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.RIGHT)
        
        # Load Results button
        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(left_panel, text="Load Results from Folder", command=self.load_results_from_folder, width=25).pack(pady=5)

        # --- RIGHT PANEL ---
        right_panel = ttk.Frame(main_paned)
        main_paned.add(right_panel, weight=4) # Right panel takes more space
        
        # Right split: Logs (top) vs Visualizer (bottom)
        right_paned = ttk.PanedWindow(right_panel, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)
        
        # Logs Frame
        logs_frame = ttk.LabelFrame(right_paned, text="Simulation Log", padding="5")
        right_paned.add(logs_frame, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(logs_frame, state="disabled", font=("Consolas", 9), height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_config("stdout", foreground="black")
        self.log_text.tag_config("stderr", foreground="red")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="#ff8c00")

        # Visualizer Frame
        visualizer_frame = ttk.LabelFrame(right_paned, text="Schedule Visualizer", padding="5")
        right_paned.add(visualizer_frame, weight=3)
        
        self.create_results_section(visualizer_frame)

    def create_results_section(self, parent):
        """Create results table section."""
        # Filter controls
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="View Mode:").pack(side=tk.LEFT, padx=(0, 5))
        self.view_mode_var = tk.StringVar(value="Timetable Grid")
        self.view_mode_combo = ttk.Combobox(filter_frame, textvariable=self.view_mode_var, state='readonly', width=15)
        self.view_mode_combo['values'] = ['List View', 'Timetable Grid']
        self.view_mode_combo.pack(side=tk.LEFT, padx=5)
        self.view_mode_combo.bind('<<ComboboxSelected>>', self.change_view_mode)
        
        ttk.Separator(filter_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(filter_frame, text="Filter by:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_var = tk.StringVar(value="All Schedules")
        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, state='readonly', width=25)
        self.filter_combo['values'] = ['All Schedules']
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        self.filter_combo.bind('<<ComboboxSelected>>', self.apply_filter)
        
        ttk.Button(filter_frame, text="Load Results from Folder", command=self.load_results_from_folder).pack(side=tk.RIGHT)

        # Container for views
        self.view_container = ttk.Frame(parent)
        self.view_container.pack(fill=tk.BOTH, expand=True)
        
        # --- List View ---
        self.list_view_frame = ttk.Frame(self.view_container)
        # (Initially hidden)
        
        # Treeview with all columns matching the schedule CSV
        columns = ('Course Code', 'Course Title', 'Time', 'Days', 'Room', 'Lec', 'Lab', 
                   'Units', 'No. of Hours', 'ETL Units', 'Instructor/Professor', 'Program-Year-Block')
        self.tree = ttk.Treeview(self.list_view_frame, columns=columns, show='headings', height=15)
        
        # Configure columns with appropriate widths
        columns_config = {
            'Course Code': 80,
            'Course Title': 200,
            'Time': 100,
            'Days': 50,
            'Room': 100,
            'Lec': 35,
            'Lab': 35,
            'Units': 45,
            'No. of Hours': 70,
            'ETL Units': 60,
            'Instructor/Professor': 100,
            'Program-Year-Block': 100
        }
        
        for col, width in columns_config.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.W if col == 'Course Title' else tk.CENTER)
        
        # Scrollbars
        vsb = ttk.Scrollbar(self.list_view_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.list_view_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        self.list_view_frame.columnconfigure(0, weight=1)
        self.list_view_frame.rowconfigure(0, weight=1)

        # --- Grid View ---
        self.grid_view_frame = ttk.Frame(self.view_container)
        self.grid_view_canvas = tk.Canvas(self.grid_view_frame, bg='white')
        grid_vsb = ttk.Scrollbar(self.grid_view_frame, orient="vertical", command=self.grid_view_canvas.yview)
        grid_hsb = ttk.Scrollbar(self.grid_view_frame, orient="horizontal", command=self.grid_view_canvas.xview)
        self.grid_view_canvas.configure(yscrollcommand=grid_vsb.set, xscrollcommand=grid_hsb.set)
        
        self.grid_view_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        grid_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        grid_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.grid_inner_frame = ttk.Frame(self.grid_view_canvas)
        self.grid_view_canvas.create_window((0, 0), window=self.grid_inner_frame, anchor='nw')
        self.grid_inner_frame.bind('<Configure>', lambda e: self.grid_view_canvas.configure(scrollregion=self.grid_view_canvas.bbox('all')))
        
        # Default View
        self.change_view_mode()

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
        if not self.override_rooms.get():
            return self.rooms_file.get()
        
        n_lab = self.num_lab_rooms.get()
        n_lec = self.num_lec_rooms.get()
        
        rooms_data = []
        for i in range(n_lab):
            rooms_data.append({
                'room_id': f'LAB-{i+1:03d}', 'building': 'Simulated', 'floor': 1, 'capacity': 50,
                'room_type': 'lab', 'equipment': 'general', 'room_category': 'lab'
            })
        for i in range(n_lec):
             rooms_data.append({
                'room_id': f'LEC-{i+1:03d}', 'building': 'Simulated', 'floor': 2, 'capacity': 50,
                'room_type': 'lecture', 'equipment': 'general', 'room_category': 'non-lab'
            })
            
        df = pd.DataFrame(rooms_data)
        temp_file = "temp_rooms_simulation.csv"
        df.to_csv(temp_file, index=False)
        self.print_log(f"Generated temp rooms: {n_lab} labs, {n_lec} lectures.", "warning")
        return temp_file

    def check_feasibility(self):
        if not self.courses_file.get() or not self.enrollment_file.get():
            messagebox.showerror("Error", "Please select Courses and Enrollment files.")
            return

        try:
            courses_path = self.courses_file.get()
            enrollment_path = self.enrollment_file.get()
            rooms_path = self.get_effective_rooms_file()
            
            if not os.path.exists(rooms_path):
                messagebox.showerror("Error", "Rooms file not found.")
                return

            self.print_log("\n--- RUNNING FEASIBILITY ANALYSIS ---", "warning")
            
            courses = pd.read_csv(courses_path)
            enrollment = pd.read_csv(enrollment_path)
            rooms = pd.read_csv(rooms_path)
            
            semester = self.semester_var.get()
            sem_courses = courses[courses['semester'] == semester]
            
            total_lab_hours_demand = 0
            total_lec_hours_demand = 0
            breakdown = {}

            for _, group in enrollment.iterrows():
                group_program = group['program']
                group_year = group['year']
                
                group_courses = sem_courses[
                    (sem_courses['program'] == group_program) & 
                    (sem_courses['year'] == group_year)
                ]
                
                for _, course in group_courses.iterrows():
                    if course['code'].startswith('NSTP'): continue

                    raw_lec = course['lec_hours']
                    raw_lab = course['lab_hours']
                    
                    if course['code'] == 'IT 128':
                        sched_lec = 2; sched_lab = 0
                    else:
                        sched_lab = 3 if raw_lab > 0 else 0
                        if raw_lec > 0:
                            sched_lec = 3 if raw_lab == 0 else 2
                        else:
                            sched_lec = 0

                    total_lec_hours_demand += sched_lec
                    total_lab_hours_demand += sched_lab
                    
                    code = course['code']
                    if code not in breakdown:
                        breakdown[code] = {'title': course['name'], 'lec_hrs': sched_lec, 'lab_hrs': sched_lab, 'sections': 0}
                    breakdown[code]['sections'] += 1
            
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

            self.print_log("\n--- LAB BREAKDOWN ---", "stdout")
            for code, data in breakdown.items():
                if data['lab_hrs'] > 0:
                    total = data['sections'] * data['lab_hrs']
                    self.print_log(f"  • {code}: {data['sections']} sections × {data['lab_hrs']} hrs = {total} hrs")

            self.print_log("\n--- LECTURE BREAKDOWN ---", "stdout")
            for code, data in breakdown.items():
                if data['lec_hrs'] > 0:
                    total = data['sections'] * data['lec_hrs']
                    self.print_log(f"  • {code}: {data['sections']} sections × {data['lec_hrs']} hrs = {total} hrs")
            
            can_run = True
            if total_lec_hours_demand > total_lec_supply:
                self.print_log("❌ CRITICAL: Lecture demand exceeds supply!", "stderr")
                can_run = False
            if total_lab_hours_demand > total_lab_supply:
                self.print_log("❌ CRITICAL: Lab demand exceeds supply!", "stderr")
                can_run = False
                
            if can_run:
                self.print_log("✅ Feasibility Check Passed.", "success")
                self.btn_run.configure(state="normal")
            elif lec_util > 0.85 or lab_util > 0.85:
                 self.print_log("⚠️ WARNING: Utilization >85%.", "warning")
                 self.btn_run.configure(state="normal")
            else:
                self.btn_run.configure(state="normal") 
                
        except Exception as e:
            self.print_log(f"Error checking feasibility: {e}", "stderr")

    def start_simulation_thread(self):
        self.btn_run.configure(state="disabled")
        self.btn_check.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.simulation_stopped = False
        self.status_label.config(text="Running...", foreground="green")
        # Start timer
        self.timer_running = True
        self.timer_start = time.time()
        self.update_timer()
        t = threading.Thread(target=self.run_simulation)
        t.start()

    def stop_simulation(self):
        """Stop the simulation after the current year completes."""
        self.simulation_stopped = True
        self.status_label.config(text="Stopping...", foreground="orange")
        self.print_log("\n⚠️ Stop requested. Will stop after current year completes...", "warning")
        self.btn_stop.configure(state="disabled")

    def update_timer(self):
        """Update the timer label every second."""
        if self.timer_running:
            elapsed = time.time() - self.timer_start
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            self.timer_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.root.after(1000, self.update_timer)

    def stop_timer(self):
        """Stop the timer and return elapsed time."""
        self.timer_running = False
        if self.timer_start:
            elapsed = time.time() - self.timer_start
            return elapsed
        return 0

    def run_simulation(self):
        try:
            courses_path = self.courses_file.get()
            enrollment_path = self.enrollment_file.get()
            rooms_path = self.get_effective_rooms_file()
            semester = self.semester_var.get()
            time_limit = self.time_limit_var.get()
            gap_tolerance = self.gap_tolerance_var.get() / 100.0  # Convert % to decimal
            solver_name = self.solver_var.get()
            strategy = self.strategy_var.get()
            
            output_dir = f"output_gui_sim_sem{semester}"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            self.print_log(f"\n--- STARTING SIMULATION ---", "warning")
            self.print_log(f"Strategy: {strategy}")
            self.print_log(f"Solver: {solver_name} | Time Limit: {time_limit}s | Gap Tolerance: {gap_tolerance:.1%}")
            
            if strategy == "Global (All-at-Once)":
                self.print_log("Running global optimization (this may take a while)...")
                optimizer = SchedulingOptimizer(
                    courses_file=courses_path,
                    enrollment_file=enrollment_path,
                    rooms_file=rooms_path
                )
                self.print_log("Building full model...")
                optimizer.build_model(semester=semester)
                
                self.print_log(f"Solving full model (max {time_limit}s)...")
                status = optimizer.solve(time_limit=time_limit, gap_tolerance=gap_tolerance, solver_name=solver_name)
                
                if status == pl.LpStatusOptimal or pl.value(optimizer.model.objective) > 0:
                     self.print_log("✓ Optimal/Feasible solution found!")
                     optimizer.export_all_schedules(output_dir=output_dir)
                else:
                     self.print_log("❌ No feasible solution found in time limit.", "stderr")

            else:
                # Sequential Strategy - pass stop check callback
                all_solutions = solve_large_dataset(
                    courses_file=courses_path,
                    enrollment_file=enrollment_path,
                    rooms_file=rooms_path,
                    semester=semester,
                    output_dir=output_dir,
                    time_limit=time_limit,
                    gap_tolerance=gap_tolerance,
                    solver=solver_name,
                    stop_check=lambda: self.simulation_stopped
                )
                
                if self.simulation_stopped:
                    self.print_log(f"\n⚠️ Simulation stopped by user.", "warning")
                    return
            
            self.print_log(f"\n✅ Simulation Complete!", "success")
            self.load_results_from_folder(output_dir)
            # Attempt to load from specific subfolder if it exists
            sem_folder = "1st_Sem_Schedule" if semester == 1 else "2nd_Sem_Schedule"
            sub_path = os.path.join(output_dir, sem_folder)
            if os.path.exists(sub_path):
                 self.load_results_from_folder(sub_path)
            
            messagebox.showinfo("Success", "Simulation Completed Successfully!")
            
        except Exception as e:
            self.print_log(f"\n❌ Simulation Failed: {str(e)}", "stderr")
            import traceback
            self.print_log(traceback.format_exc(), "stderr")
        finally:
            elapsed = self.stop_timer()
            self.print_log(f"\n⏱ Total time: {elapsed/60:.2f} minutes ({elapsed:.1f} seconds)")
            self.btn_run.configure(state="normal")
            self.btn_check.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            if self.simulation_stopped:
                self.status_label.config(text="Stopped", foreground="red")
            else:
                self.status_label.config(text="Complete", foreground="green")

    def load_results_from_folder(self, folder_path=None):
        """Load all CSV schedules from a folder and visualize them."""
        if not folder_path:
            folder_path = filedialog.askdirectory()
            
        if not folder_path or not os.path.exists(folder_path):
            return

        self.print_log(f"\n📂 Loading results from: {folder_path}")
        
        self.schedules_data = []
        for f in os.listdir(folder_path):
            if f.endswith(".csv") and f.startswith("schedule_"):
                try:
                    path = os.path.join(folder_path, f)
                    df = pd.read_csv(path)
                    
                    # Extract Program-Year-Block from filename (e.g., schedule_IT1A.csv -> IT-1A)
                    # Filename format: schedule_<Program><Year><Block>.csv
                    base_name = f.replace("schedule_", "").replace(".csv", "")
                    # Parse: IT1A -> IT-1A, IT2B -> IT-2B
                    if len(base_name) >= 3:
                        program = base_name[:-2]  # e.g., IT
                        year = base_name[-2]      # e.g., 1
                        block = base_name[-1]     # e.g., A
                        program_year_block = f"{program}-{year}{block}"
                    else:
                        program_year_block = base_name
                    
                    # Add to internal list using the correct column names from the CSV
                    for _, row in df.iterrows():
                        self.schedules_data.append({
                            'Course Code': row.get('Course Code', ''),
                            'Course Title': row.get('Course Title', ''),
                            'Time': row.get('Time', ''),
                            'Days': row.get('Days', ''),
                            'Room': row.get('Room', ''),
                            'Lec': row.get('Lec', 0),
                            'Lab': row.get('Lab', 0),
                            'Units': row.get('Units', 0),
                            'No. of Hours': row.get('No. of Hours', 0),
                            'ETL Units': row.get('ETL Units', 0),
                            'Instructor/Professor': row.get('Instructor/Professor', 'TBA'),
                            'Program-Year-Block': program_year_block
                        })
                except Exception as e:
                    self.print_log(f"Error loading {f}: {e}", "stderr")

        if self.schedules_data:
            self.print_log(f"   Loaded {len(self.schedules_data)} schedule entries.")
            self.update_filters()
            self.refresh_view()
        else:
            self.print_log("   No schedule files found.", "warning")

    def update_filters(self):
        blocks = sorted(list(set(item['Program-Year-Block'] for item in self.schedules_data)))
        self.filter_combo['values'] = ['All Schedules'] + blocks
        self.filter_combo.set('All Schedules')

    def change_view_mode(self, event=None):
        mode = self.view_mode_var.get()
        if mode == 'List View':
            self.list_view_frame.pack(fill=tk.BOTH, expand=True)
            self.grid_view_frame.pack_forget()
        else:
            self.list_view_frame.pack_forget()
            self.grid_view_frame.pack(fill=tk.BOTH, expand=True)
        self.refresh_view()

    def apply_filter(self, event=None):
        self.refresh_view()

    def refresh_view(self):
        mode = self.view_mode_var.get()
        filter_val = self.filter_var.get()
        
        filtered = [x for x in self.schedules_data if filter_val == 'All Schedules' or x['Program-Year-Block'] == filter_val]
        
        if mode == 'List View':
            self.tree.delete(*self.tree.get_children())
            for item in filtered:
                # Format time/room to single line for display
                time_display = item.get('Time', '').replace('\n', ', ')
                room_display = item.get('Room', '').replace('\n', ', ')
                
                self.tree.insert('', 'end', values=(
                    item.get('Course Code', ''),
                    item.get('Course Title', ''),
                    time_display,
                    item.get('Days', ''),
                    room_display,
                    item.get('Lec', 0),
                    item.get('Lab', 0),
                    item.get('Units', 0),
                    item.get('No. of Hours', 0),
                    item.get('ETL Units', 0),
                    item.get('Instructor/Professor', 'TBA'),
                    item.get('Program-Year-Block', '')
                ))
        else:
            # Grid View Logic - Proper Timetable
            self.populate_timetable_grid(filtered)

    def get_course_color(self, course_code):
        """Generate a consistent color for a course based on its code."""
        colors = [
            '#FFE5E5', '#E5F5FF', '#E5FFE5', '#FFF5E5', '#F5E5FF',
            '#FFE5F5', '#E5FFFF', '#FFFFE5', '#F0E5FF', '#E5FFF0',
        ]
        return colors[abs(hash(course_code)) % len(colors)]

    def populate_timetable_grid(self, filtered_data):
        """Create a timetable grid view (M-F on x-axis, 8AM-5PM on y-axis)."""
        # Clear existing grid
        for widget in self.grid_inner_frame.winfo_children():
            widget.destroy()

        if not filtered_data:
            ttk.Label(self.grid_inner_frame, text="No schedule data available").grid(row=0, column=0, padx=20, pady=20)
            return

        # Define time slots (8 AM to 5 PM, 30-minute intervals) - EXCLUDING LUNCH (12:00-13:00)
        time_slots = []
        for hour in range(8, 12):  # Morning: 8:00-12:00
            time_slots.append(f"{hour:02d}:00")
            time_slots.append(f"{hour:02d}:30")
        # Add lunch break marker
        time_slots.append("12:00 (Lunch)")
        for hour in range(13, 18):  # Afternoon: 13:00-17:00
            time_slots.append(f"{hour:02d}:00")
            time_slots.append(f"{hour:02d}:30")

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        day_abbrev = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'TH': 'Thursday', 'F': 'Friday'}

        # Create header row
        ttk.Label(self.grid_inner_frame, text="Time", font=('Segoe UI', 9, 'bold'),
                  relief=tk.RIDGE, padding=5).grid(row=0, column=0, sticky="nsew")

        for col_idx, day in enumerate(days, start=1):
            ttk.Label(self.grid_inner_frame, text=day, font=('Segoe UI', 9, 'bold'),
                      relief=tk.RIDGE, padding=5).grid(row=0, column=col_idx, sticky="nsew")

        # Create a structure to track course blocks: [day][time_slot_index] = course_info
        # Use actual schedulable time slots (without lunch marker) for parsing
        schedulable_slots = []
        for hour in range(8, 12):
            schedulable_slots.append(f"{hour:02d}:00")
            schedulable_slots.append(f"{hour:02d}:30")
        for hour in range(13, 18):
            schedulable_slots.append(f"{hour:02d}:00")
            schedulable_slots.append(f"{hour:02d}:30")

        course_blocks = {day: {} for day in days}
        skip_cells = {day: set() for day in days}

        # Parse schedule data and identify course blocks
        for entry in filtered_data:
            course_code = entry.get('Course Code', '')
            course_title = entry.get('Course Title', '')
            time_str_raw = entry.get('Time', '')
            days_str = entry.get('Days', '')
            room_str = entry.get('Room', '')

            if not time_str_raw or not days_str:
                continue

            # Parse days
            course_days = []
            idx = 0
            while idx < len(days_str):
                if idx < len(days_str) - 1 and days_str[idx:idx + 2] == 'TH':
                    course_days.append('Thursday')
                    idx += 2
                elif days_str[idx] in day_abbrev:
                    course_days.append(day_abbrev[days_str[idx]])
                    idx += 1
                else:
                    idx += 1

            if not course_days:
                continue

            # Loop through each individual time slot from the multiline string
            for time_str in time_str_raw.split('\n'):
                time_str = time_str.strip()
                if not time_str:
                    continue

                try:
                    parts = time_str.split('-')
                    if len(parts) != 2:
                        continue
                    start_time = parts[0].strip()
                    end_time = parts[1].strip()

                    if start_time not in schedulable_slots:
                        continue

                    start_idx = schedulable_slots.index(start_time)
                    end_idx = start_idx + 1
                    for slot_idx in range(start_idx + 1, len(schedulable_slots)):
                        if schedulable_slots[slot_idx] >= end_time:
                            end_idx = slot_idx
                            break
                    else:
                        end_idx = len(schedulable_slots)

                    rowspan = max(1, end_idx - start_idx)

                    for day in course_days:
                        if day not in course_blocks:
                            continue

                        # Check for conflicts
                        conflict = False
                        for slot_idx in range(start_idx, start_idx + rowspan):
                            if slot_idx in course_blocks[day] or slot_idx in skip_cells[day]:
                                conflict = True
                                break

                        if conflict:
                            continue

                        course_blocks[day][start_idx] = {
                            'code': course_code,
                            'title': course_title,
                            'room': room_str.split('\n')[0] if room_str else '',
                            'rowspan': rowspan,
                            'time': time_str
                        }

                        for slot_idx in range(start_idx + 1, start_idx + rowspan):
                            skip_cells[day].add(slot_idx)

                except (ValueError, IndexError):
                    continue

        # Populate grid cells - map schedulable slots to display rows
        display_row = 1
        schedulable_idx = 0
        
        for time_slot in time_slots:
            if "Lunch" in time_slot:
                # Lunch break row - span all columns with a special color
                ttk.Label(self.grid_inner_frame, text="12:00", relief=tk.RIDGE, padding=5,
                          font=('Segoe UI', 8)).grid(row=display_row, column=0, sticky="nsew")
                for col_idx in range(1, 6):
                    lunch_label = tk.Label(self.grid_inner_frame, text="LUNCH BREAK", 
                                           bg="#DDDDDD", relief=tk.RIDGE, font=('Segoe UI', 8))
                    lunch_label.grid(row=display_row, column=col_idx, sticky="nsew")
                display_row += 1
                continue
            
            slot_idx = schedulable_idx
            schedulable_idx += 1

            ttk.Label(self.grid_inner_frame, text=time_slot, relief=tk.RIDGE, padding=5,
                      font=('Segoe UI', 8)).grid(row=display_row, column=0, sticky="nsew")

            for col_idx, day in enumerate(days, start=1):
                if slot_idx in skip_cells[day]:
                    display_row_for_skip = display_row
                    # Don't render anything, it's covered by rowspan
                    pass
                elif slot_idx in course_blocks[day]:
                    course = course_blocks[day][slot_idx]
                    cell_text = f"{course['code']}\n{course['room']}\n{course['time']}"

                    cell_frame = tk.Frame(self.grid_inner_frame, relief=tk.RIDGE, borderwidth=1,
                                          bg=self.get_course_color(course['code']))
                    cell_frame.grid(row=display_row, column=col_idx, rowspan=course['rowspan'], sticky="nsew")

                    cell_label = tk.Label(cell_frame, text=cell_text, font=('Segoe UI', 7),
                                          bg=self.get_course_color(course['code']),
                                          justify=tk.LEFT, anchor='nw', padx=3, pady=3)
                    cell_label.pack(fill=tk.BOTH, expand=True)
                else:
                    ttk.Label(self.grid_inner_frame, text="", relief=tk.RIDGE, padding=5).grid(
                        row=display_row, column=col_idx, sticky="nsew")
            
            display_row += 1

        # Configure column weights
        for col in range(6):
            self.grid_inner_frame.columnconfigure(col, weight=1, minsize=100)

if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerGUI(root)
    root.mainloop()
