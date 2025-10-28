"""
Classroom Scheduling Optimizer - GUI Application
Binary Integer Linear Programming with Interactive Interface

Features:
- File selection for input CSVs
- Live optimization progress
- Interactive schedule table display
- Export functionality
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import threading
import os
from datetime import datetime
from scheduler import SchedulingOptimizer
import pulp as pl
from typing import List


class CollapsibleFrame(ttk.Frame):
    """A collapsible frame widget for tkinter."""
    def __init__(self, parent, text="", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.text = text
        self.is_expanded = tk.BooleanVar(value=True)

        self.title_frame = ttk.Frame(self, style='TFrame')
        self.title_frame.pack(fill=tk.X, expand=True)

        self.toggle_button = ttk.Label(self.title_frame, text=f'▼ {self.text}', style='Header.TLabel', cursor="hand2")
        self.toggle_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.toggle_button.bind("<Button-1>", self.toggle)

    def toggle(self, event=None):
        if self.is_expanded.get():
            self.content_frame.pack_forget()
            self.toggle_button.config(text=f'► {self.text}')
        else:
            self.content_frame.pack(fill=tk.BOTH, expand=True)
            self.toggle_button.config(text=f'▼ {self.text}')
        self.is_expanded.set(not self.is_expanded.get())

class SchedulerGUI:
    """Main GUI Application for Classroom Scheduling Optimizer."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Classroom Scheduling Optimizer - CCMS")
        self.root.geometry("1400x800")
        self.root.minsize(1000, 700)
        
        # File paths
        self.courses_file = tk.StringVar()
        self.enrollment_file = tk.StringVar()
        self.rooms_file = tk.StringVar()
        
        # Optimization state
        self.optimizer = None
        self.is_running = False
        self.schedules_data = []
        self.theme = tk.StringVar(value="light")
        self.semester_var = tk.StringVar(value="1")
        self.scheduling_mode_var = tk.StringVar(value="All at Once")
        
        # Setup UI
        self.apply_theme()
        self.create_widgets()
        
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        if self.theme.get() == "light":
            self.theme.set("dark")
        else:
            self.theme.set("light")
        self.apply_theme()

    def apply_theme(self):
        """Configure ttk styles for modern appearance."""
        style = ttk.Style(self.root)
        style.theme_use('clam')

        if self.theme.get() == "dark":
            # Dark Theme Colors
            bg_color = '#2e2e2e'
            fg_color = '#d4d4d4'
            accent_color = '#3a7adf'
            widget_bg = '#3c3c3c'
            tree_heading_bg = '#4a4a4a'
            log_bg = '#1e1e1e'
        else:
            # Light Theme Colors
            bg_color = '#f0f0f0'
            fg_color = '#000000'
            accent_color = '#2563eb'
            widget_bg = '#ffffff'
            tree_heading_bg = '#e1e1e1'
            log_bg = '#fdfdfd'

        # Apply root background
        self.root.config(bg=bg_color)

        # General widget styling
        style.configure('.', background=bg_color, foreground=fg_color, bordercolor=bg_color)
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TButton', background=accent_color, foreground='white', font=('Segoe UI', 10, 'bold'))
        style.map('TButton', background=[('active', '#4a8eff')])
        style.configure('Header.TLabel', font=('Segoe UI', 10, 'bold'), background=bg_color, foreground=fg_color)
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), background=bg_color, foreground=fg_color)
        style.configure('Subtitle.TLabel', font=('Segoe UI', 11), background=bg_color, foreground=fg_color)
        style.configure('Primary.TButton', background=accent_color, foreground='white', font=('Segoe UI', 10, 'bold'))

        # Treeview styling
        style.configure("Treeview", background=widget_bg, foreground=fg_color, fieldbackground=widget_bg,rowheight=40)
        style.configure("Treeview.Heading", background=tree_heading_bg, foreground=fg_color, font=('Segoe UI', 9, 'bold'))
        style.map("Treeview.Heading", background=[('active', accent_color)])

        # Combobox styling
        style.configure('TCombobox', fieldbackground=widget_bg, background=widget_bg, foreground=fg_color)

        # Paned window
        style.configure('TPanedWindow', background=bg_color)

        # Update log text widget and other specific widgets if they exist
        if hasattr(self, 'status_text'):
            self.status_text.config(bg=log_bg, fg=fg_color, insertbackground=fg_color)
        if hasattr(self, 'root'):
            self.root.config(bg=bg_color)
        if hasattr(self, 'timer_label'):
            self.timer_label.config(background=bg_color, foreground=fg_color)
        if hasattr(self, 'summary_label'):
            self.summary_label.config(background=bg_color, foreground=fg_color)
        if hasattr(self, 'status_bar_label'):
            self.status_bar_label.config(background=bg_color, foreground=fg_color)
        if hasattr(self, 'time_label'):
            self.time_label.config(background=bg_color, foreground=fg_color)
        
    def create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="🎓 Classroom Scheduling Optimizer",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="Binary Integer Linear Programming - CCMS Optimization System",
            style='Subtitle.TLabel'
        )
        subtitle_label.grid(row=1, column=0, columnspan=1, pady=(0, 20), sticky=tk.W)

        # Theme toggle button
        theme_button = ttk.Button(
            main_frame, 
            text="🌓 Toggle Theme", 
            command=self.toggle_theme
        )
        theme_button.grid(row=0, column=1, rowspan=2, sticky=tk.E)
        
        # Main horizontal paned window (left-right split)
        main_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        main_paned.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # LEFT PANEL - Input and Logs
        left_panel = ttk.Frame(main_paned, padding="5")
        main_paned.add(left_panel, weight=1)
        left_panel.columnconfigure(0, weight=1)
        # Configure row 0 to expand, as it will hold the new vertical pane
        left_panel.rowconfigure(0, weight=1)

        # Create a new VERTICAL paned window for the left side
        left_v_paned = ttk.PanedWindow(left_panel, orient=tk.VERTICAL)
        left_v_paned.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create a top frame for inputs and controls
        top_left_frame = ttk.Frame(left_v_paned, padding="5")
        top_left_frame.columnconfigure(0, weight=1)
        left_v_paned.add(top_left_frame, weight=0)  # weight=0 so it doesn't expand

        # Create a bottom frame for the progress log
        bottom_left_frame = ttk.Frame(left_v_paned, padding="5")
        bottom_left_frame.columnconfigure(0, weight=1)
        # This row will hold the progress section and expand
        bottom_left_frame.rowconfigure(0, weight=1)
        left_v_paned.add(bottom_left_frame, weight=1)  # weight=1 so it expands

        # Add the sections to their new frames
        self.create_input_section(top_left_frame)
        self.create_control_section(top_left_frame)
        self.create_progress_section(bottom_left_frame)
        
        # RIGHT PANEL - Results Table
        right_panel = ttk.Frame(main_paned, padding="5")
        main_paned.add(right_panel, weight=2)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # Results Section (in right panel)
        self.create_results_section(right_panel)
        
        # Status Bar (bottom of main frame)
        self.create_status_bar(main_frame)
        
    def create_input_section(self, parent):
        """Create file selection section."""
        collapsible_frame = CollapsibleFrame(parent, text="📁 Input Files")
        collapsible_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame = collapsible_frame.content_frame
        input_frame.columnconfigure(1, weight=1)
        
        # Courses file
        ttk.Label(input_frame, text="Courses (CSV/JSON):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(input_frame, textvariable=self.courses_file, width=40).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Button(input_frame, text="Browse...", command=lambda: self.browse_file(self.courses_file)).grid(
            row=0, column=2, padx=5
        )
        
        # Enrollment file
        ttk.Label(input_frame, text="Enrollment CSV:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(input_frame, textvariable=self.enrollment_file, width=40).grid(
            row=1, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Button(input_frame, text="Browse...", command=lambda: self.browse_file(self.enrollment_file)).grid(
            row=1, column=2, padx=5
        )
        
        # Rooms file
        ttk.Label(input_frame, text="Rooms CSV:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(input_frame, textvariable=self.rooms_file, width=40).grid(
            row=2, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Button(input_frame, text="Browse...", command=lambda: self.browse_file(self.rooms_file)).grid(
            row=2, column=2, padx=5
        )
        
        # Quick load buttons
        load_frame = ttk.Frame(input_frame)
        load_frame.grid(row=3, column=0, columnspan=3, pady=10)

        ttk.Button(
            load_frame, 
            text="📂 Load Default", 
            command=self.load_default_files
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            load_frame, 
            text="🧪 Load Reduced", 
            command=self.load_reduced_files
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            load_frame, 
            text="🗂️ Load Full Dataset", 
            command=self.load_full_files
        ).pack(side=tk.LEFT, padx=5)
        
    def create_control_section(self, parent):
        """Create control buttons section."""
        control_frame = ttk.Frame(parent, padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(1, weight=1)

        # Semester selection
        ttk.Label(control_frame, text="Semester:").pack(side=tk.LEFT, padx=(0, 5))
        semester_combo = ttk.Combobox(
            control_frame,
            textvariable=self.semester_var,
            values=["1", "2"],
            width=5,
            state='readonly'
        )
        semester_combo.pack(side=tk.LEFT, padx=5, pady=2)
        semester_combo.set("1")

        # Scheduling mode selection
        ttk.Label(control_frame, text="Mode:").pack(side=tk.LEFT, padx=(10, 5))
        mode_combo = ttk.Combobox(
            control_frame,
            textvariable=self.scheduling_mode_var,
            values=["All at Once", "IT then IS"],
            width=12,
            state='readonly'
        )
        mode_combo.pack(side=tk.LEFT, padx=5, pady=2)
        mode_combo.set("All at Once")
        
        # Stack buttons vertically for left panel
        self.run_button = ttk.Button(
            control_frame,
            text="▶ Run Optimization",
            command=self.run_optimization,
            style='Primary.TButton'
        )
        self.run_button.pack(fill=tk.X, pady=2)
        
        self.stop_button = ttk.Button(
            control_frame,
            text="⏹ Stop",
            command=self.stop_optimization,
            state=tk.DISABLED
        )
        self.stop_button.pack(fill=tk.X, pady=2)
        
        self.export_button = ttk.Button(
            control_frame,
            text="💾 Export All Schedules",
            command=self.export_schedules,
            state=tk.DISABLED
        )
        self.export_button.pack(fill=tk.X, pady=2)
        
        self.clear_button = ttk.Button(
            control_frame,
            text="🗑️ Clear Results",
            command=self.clear_results
        )
        self.clear_button.pack(fill=tk.X, pady=2)
        
    def create_progress_section(self, parent):
        """Create progress tracking section."""
        collapsible_frame = CollapsibleFrame(parent, text="⚙️ Optimization Progress")
        collapsible_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        parent.rowconfigure(0, weight=1)
        progress_frame = collapsible_frame.content_frame
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(2, weight=1)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='indeterminate',
            length=400
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Timer label
        self.timer_label = ttk.Label(progress_frame, text="Elapsed Time: 00:00:00", font=('Consolas', 9))
        self.timer_label.grid(row=1, column=0, pady=(5, 5))

        # Status text
        self.status_text = tk.Text(
            progress_frame,
            height=20,
            wrap=tk.WORD,
            font=('Consolas', 9),
            insertbackground='white' # This will be styled by apply_theme
        )
        self.status_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
    def create_results_section(self, parent):
        """Create results table section."""
        collapsible_frame = CollapsibleFrame(parent, text="📊 Generated Schedules")
        collapsible_frame.pack(fill=tk.BOTH, expand=True)
        results_frame = collapsible_frame.content_frame
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
        
        # Filter controls
        filter_frame = ttk.Frame(results_frame)
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # View mode selector
        ttk.Label(filter_frame, text="View Mode:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.view_mode_var = tk.StringVar(value="List View")
        self.view_mode_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.view_mode_var,
            state='readonly',
            width=20
        )
        self.view_mode_combo['values'] = ['List View', 'Timetable Grid']
        self.view_mode_combo.pack(side=tk.LEFT, padx=5)
        self.view_mode_combo.bind('<<ComboboxSelected>>', self.change_view_mode)
        
        # Separator
        ttk.Separator(filter_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Filter by program
        ttk.Label(filter_frame, text="Filter by:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.filter_var = tk.StringVar(value="All Schedules")
        self.filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            state='readonly',
            width=30
        )
        self.filter_combo['values'] = ['All Schedules']
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        self.filter_combo.bind('<<ComboboxSelected>>', self.apply_filter)
        
        # Create container for different views
        self.view_container = ttk.Frame(results_frame)
        self.view_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.view_container.columnconfigure(0, weight=1)
        self.view_container.rowconfigure(0, weight=1)
        
        # Create List View (Treeview)
        self.list_view_frame = ttk.Frame(self.view_container)
        self.list_view_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.list_view_frame.columnconfigure(0, weight=1)
        self.list_view_frame.rowconfigure(0, weight=1)
        
        # Treeview with scrollbars
        self.tree = ttk.Treeview(
            self.list_view_frame,
            columns=('Course Code', 'Course Title', 'Time', 'Days', 'Room', 'Lec', 'Lab', 
                     'Units', 'No. of Hours', 'ETL Units', 'Instructor/Professor', 'Program-Year-Block'),
            show='headings',
            height=15
        )
        
        # Configure columns
        columns_config = {
            'Course Code': 80,
            'Course Title': 250,
            'Time': 120,
            'Days': 60,
            'Room': 90,
            'Lec': 40,
            'Lab': 40,
            'Units': 50,
            'No. of Hours': 80,
            'ETL Units': 70,
            'Instructor/Professor': 120,
            'Program-Year-Block': 120
        }
        
        for col, width in columns_config.items():
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=width, anchor=tk.W if col == 'Course Title' else tk.CENTER)
        
        # Scrollbars
        vsb = ttk.Scrollbar(self.list_view_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.list_view_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Create Timetable Grid View (initially hidden)
        self.grid_view_frame = ttk.Frame(self.view_container)
        self.grid_view_canvas = tk.Canvas(self.grid_view_frame, bg='white')
        grid_vsb = ttk.Scrollbar(self.grid_view_frame, orient="vertical", command=self.grid_view_canvas.yview)
        grid_hsb = ttk.Scrollbar(self.grid_view_frame, orient="horizontal", command=self.grid_view_canvas.xview)
        self.grid_view_canvas.configure(yscrollcommand=grid_vsb.set, xscrollcommand=grid_hsb.set)
        
        self.grid_view_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        grid_vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        grid_hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.grid_view_frame.columnconfigure(0, weight=1)
        self.grid_view_frame.rowconfigure(0, weight=1)
        
        # Inner frame for grid content
        self.grid_inner_frame = ttk.Frame(self.grid_view_canvas)
        self.grid_view_canvas.create_window((0, 0), window=self.grid_inner_frame, anchor='nw')
        self.grid_inner_frame.bind('<Configure>', lambda e: self.grid_view_canvas.configure(scrollregion=self.grid_view_canvas.bbox('all')))
        
        # Summary label
        self.summary_label = ttk.Label(results_frame, text="No schedules generated yet")
        self.summary_label.grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        
    def create_status_bar(self, parent):
        """Create status bar at bottom."""
        status_frame = ttk.Frame(parent, relief=tk.SUNKEN, padding="2")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.status_bar_label = ttk.Label(
            status_frame,
            text="Ready to optimize schedules",
            anchor=tk.W
        )
        self.status_bar_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.time_label = ttk.Label(status_frame, text="", anchor=tk.E)
        self.time_label.pack(side=tk.RIGHT)
        
    def browse_file(self, var):
        """Open file browser dialog."""
        # Determine file types based on which variable
        if var == self.courses_file:
            filetypes = [
                ("CSV & JSON files", "*.csv *.json"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
            title = "Select Courses File (CSV or JSON)"
        else:
            filetypes = [("CSV files", "*.csv"), ("All files", "*.*")]
            title = "Select CSV File"
        
        filename = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        if filename:
            var.set(filename)
            # If JSON curriculum selected for courses, update label
            if filename.endswith('.json'):
                self.log_status(f"✓ JSON curriculum file selected: {os.path.basename(filename)}")
            
    def load_default_files(self):
        """Load default files from current directory."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        courses = os.path.join(current_dir, "courses.csv")
        enrollment = os.path.join(current_dir, "enrollment_from_json.csv")
        rooms = os.path.join(current_dir, "room.csv")
        
        if os.path.exists(courses):
            self.courses_file.set(courses)
        if os.path.exists(enrollment):
            self.enrollment_file.set(enrollment)
        if os.path.exists(rooms):
            self.rooms_file.set(rooms)
            
        if all(os.path.exists(f) for f in [courses, enrollment, rooms]):
            self.log_status("✓ Default files loaded successfully")
            self.update_status_bar("Default files loaded")
        else:
            messagebox.showwarning("Warning", "Some default files not found in current directory")
            
    def load_reduced_files(self):
        """Load default files with the reduced enrollment dataset."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        courses = os.path.join(current_dir, "courses_fixed.csv")
        enrollment = os.path.join(current_dir, "enrollment_reduced.csv")
        rooms = os.path.join(current_dir, "room_redesigned.csv")
        
        if os.path.exists(courses):
            self.courses_file.set(courses)
        if os.path.exists(enrollment):
            self.enrollment_file.set(enrollment)
        if os.path.exists(rooms):
            self.rooms_file.set(rooms)
            
        if all(os.path.exists(f) for f in [courses, enrollment, rooms]):
            self.log_status("✓ Reduced dataset loaded successfully")
            self.update_status_bar("Reduced dataset loaded")
        else:
            messagebox.showwarning("Warning", "Some reduced dataset files not found.")

    def load_full_files(self):
        """Load full dataset files for large-scale optimization."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        courses = os.path.join(current_dir, "courses_full.csv")
        enrollment = os.path.join(current_dir, "enrollment_full.csv")
        rooms = os.path.join(current_dir, "rooms_full.csv")
        
        if os.path.exists(courses):
            self.courses_file.set(courses)
        if os.path.exists(enrollment):
            self.enrollment_file.set(enrollment)
        if os.path.exists(rooms):
            self.rooms_file.set(rooms)
            
        if all(os.path.exists(f) for f in [courses, enrollment, rooms]):
            self.log_status("✓ Full dataset loaded successfully")
            self.log_status("⚠️ WARNING: Full dataset requires decomposed solving!")
            self.log_status("   Use command line: python scheduler_large_dataset.py")
            self.log_status("   Or see OPTIMIZATION_GUIDE.md for details")
            self.update_status_bar("Full dataset loaded (use decomposed solver)")
            
            # Show info dialog
            messagebox.showinfo(
                "Large Dataset Detected",
                "Full dataset loaded!\n\n"
                "⚠️ This dataset is too large for direct optimization.\n\n"
                "Recommended approach:\n"
                "1. Close this GUI\n"
                "2. Run: python scheduler_large_dataset.py\n\n"
                "This will solve year-by-year in 15-25 minutes.\n\n"
                "See OPTIMIZATION_GUIDE.md for details."
            )
        else:
            messagebox.showwarning("Warning", "Some full dataset files not found.")

    def validate_inputs(self):
        """Validate that all required files are selected."""
        if not self.courses_file.get():
            messagebox.showerror("Error", "Please select Courses CSV/JSON file")
            return False
        
        if not self.enrollment_file.get():
            messagebox.showerror("Error", "Please select Enrollment CSV file")
            return False
        
        if not self.rooms_file.get():
            messagebox.showerror("Error", "Please select Rooms CSV file")
            return False
            
        # Check if files exist
        if not os.path.exists(self.courses_file.get()):
            messagebox.showerror("Error", f"Courses file not found: {self.courses_file.get()}")
            return False
        
        if not self.courses_file.get().endswith('.json'):
            # Check enrollment only if not JSON mode
            if not os.path.exists(self.enrollment_file.get()):
                messagebox.showerror("Error", f"Enrollment file not found: {self.enrollment_file.get()}")
                return False
        
        if not os.path.exists(self.rooms_file.get()):
            messagebox.showerror("Error", f"Rooms file not found: {self.rooms_file.get()}")
            return False
                
        return True
        
    def run_optimization(self):
        """Run the optimization in a separate thread."""
        if not self.validate_inputs():
            return
            
        self.is_running = True
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.export_button.config(state=tk.DISABLED)
        self.progress_bar.start()
        
        self.clear_log()
        self.log_status("="*60)
        self.log_status("CLASSROOM SCHEDULING OPTIMIZATION")
        self.log_status("="*60)
        self.log_status("")

        # Start timer
        self.start_time = datetime.now()
        self.update_timer()
        
        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(target=self.optimization_worker, daemon=True)
        thread.start()
        
    def optimization_worker(self):
        """Worker thread for optimization."""
        mode = self.scheduling_mode_var.get()
        semester = int(self.semester_var.get())

        try:
            if mode == "All at Once":
                optimizer, status = self._run_single_optimization(semester)
                if status == pl.LpStatusOptimal:
                    self.optimizer = optimizer
                    self.load_schedules()
                    self.export_button.config(state=tk.NORMAL)
                    self.update_status_bar(f"✓ Optimization complete!")
                else:
                    self.update_status_bar("Optimization did not find a solution.")

            elif mode == "IT then IS":
                self._run_sequential_optimization(semester)
        finally:
            self.is_running = False
            self.progress_bar.stop()
            self.run_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def _run_single_optimization(self, semester: int, program_filter: List[str] = None, existing_schedule: pd.DataFrame = None):
        """Runs a single optimization pass and returns the resulting optimizer instance and status."""
        try:
            start_time = datetime.now()
            
            self.log_status(f"\n>> Running optimization for programs: {program_filter or 'All'}...")

            optimizer = SchedulingOptimizer(
                courses_file=self.courses_file.get(),
                enrollment_file=self.enrollment_file.get(),
                rooms_file=self.rooms_file.get(),
                program_filter=program_filter,
                existing_schedule=existing_schedule
            )
            
            self.log_status("\n🔧 Building optimization model...")
            optimizer.build_model(semester=semester)
            self.log_status(f"   Course Components: {len(optimizer.course_components)}")
            self.log_status(f"   Total Y (pattern) variables: {len(optimizer.Y)}")
            self.log_status(f"   Total X (assignment) variables: {len(optimizer.X)}")

            if not optimizer.X:
                self.log_status("   No variables created. Skipping solve.")
                return optimizer, pl.LpStatusNotSolved

            self.log_status("\n⚙️ Solving optimization problem...")
            status = optimizer.solve(time_limit=1200, gap_tolerance=0.05)
            
            solve_time = (datetime.now() - start_time).total_seconds()
            self.log_status(f"Status: {pl.LpStatus[status]} in {solve_time:.2f}s")
            
            if status == pl.LpStatusOptimal:
                self.log_status(f"Objective value: {pl.value(optimizer.model.objective):.4f}")
            
            return optimizer, status

        except Exception as e:
            self.log_status(f"\n❌ ERROR in single run: {str(e)}")
            messagebox.showerror("Error", f"Optimization failed:\n{str(e)}")
            return None, pl.LpStatusUndefined

    def _run_sequential_optimization(self, semester: int):
        """Runs the two-phase 'IT then IS' optimization."""
        try:
            # --- Phase 1: Schedule IT --- #
            self.log_status("\n" + "="*25 + " PHASE 1: IT PROGRAM " + "="*25)
            it_optimizer, it_status = self._run_single_optimization(semester, program_filter=['IT'])

            if it_status != pl.LpStatusOptimal:
                self.log_status("\n❌ Phase 1 (IT) failed. Halting sequential optimization.")
                self.update_status_bar("IT scheduling failed")
                return

            it_schedule_df = it_optimizer.get_full_schedule_df()
            self.log_status(f"   ✓ IT schedule generated with {len(it_schedule_df)} entries.")

            # --- Phase 2: Schedule IS --- #
            self.log_status("\n" + "="*25 + " PHASE 2: IS PROGRAM " + "="*25)
            is_optimizer, is_status = self._run_single_optimization(semester, program_filter=['IS'], existing_schedule=it_schedule_df)

            if is_status != pl.LpStatusOptimal:
                self.log_status("\n⚠️ Phase 2 (IS) did not find an optimal solution. Results may be incomplete.")
            
            is_schedule_df = is_optimizer.get_full_schedule_df()
            self.log_status(f"   ✓ IS schedule generated with {len(is_schedule_df)} entries.")

            # --- Combine and Load --- #
            self.log_status("\n" + "="*25 + " COMBINING RESULTS " + "="*25)
            combined_schedule_df = pd.concat([it_schedule_df, is_schedule_df], ignore_index=True)
            self.optimizer = is_optimizer # Store the final optimizer for export
            self.optimizer.combined_schedule_for_export = combined_schedule_df
            
            self.load_schedules(combined_schedule_df)
            self.export_button.config(state=tk.NORMAL)
            self.update_status_bar("✓ Sequential optimization complete!")

        except Exception as e:
            self.log_status(f"\n❌ ERROR in sequential run: {str(e)}")
            messagebox.showerror("Error", f"Sequential optimization failed:\n{str(e)}")
            self.update_status_bar("Error occurred")
        
    def load_schedules(self, schedule_df: pd.DataFrame = None):
        """Load all generated schedules into the table directly from the optimizer."""
        self.log_status("\n📋 Loading schedules into table...")
        
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get all unique student groups from the optimizer
        if self.optimizer is None or self.optimizer.enrollment_df is None:
            self.log_status("   Optimizer not ready. Cannot load schedules.")
            return

        if schedule_df is not None:
            all_schedules_df = schedule_df
        elif self.optimizer:
            all_schedules_df = self.optimizer.get_full_schedule_df()
        else:
            self.log_status("   Optimizer not ready. Cannot load schedules.")
            return

        self.schedules_data = all_schedules_df.to_dict('records')

        # Populate tree
        for entry in self.schedules_data:
            self.tree.insert('', tk.END, values=(
                entry.get('Course Code', ''),
                entry.get('Course Title', ''),
                entry.get('Time', ''),
                entry.get('Days', ''),
                entry.get('Room', ''),
                entry.get('Lec', ''),
                entry.get('Lab', ''),
                f"{entry.get('Units', 0):.2f}",
                entry.get('No. of Hours', ''),
                f"{entry.get('ETL Units', 0):.2f}",
                entry.get('Instructor/Professor', 'TBA'),
                entry.get('Program-Year-Block', '')
            ))
        
        # Update filter options
        unique_programs = sorted(all_schedules_df['Program-Year-Block'].unique())
        self.filter_combo['values'] = ['All Schedules'] + unique_programs
        
        # Update summary
        self.summary_label.config(text=f"Total: {len(self.schedules_data)} course schedules loaded")
        self.log_status(f"   ✓ {len(self.schedules_data)} course schedules loaded")
        
    def apply_filter(self, event=None):
        """Apply filter to displayed schedules."""
        filter_value = self.filter_var.get()
        
        # Update based on current view mode
        if self.view_mode_var.get() == "List View":
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Re-populate based on filter
            count = 0
            for entry in self.schedules_data:
                if filter_value == 'All Schedules' or entry['Program-Year-Block'] == filter_value:
                    self.tree.insert('', tk.END, values=(
                        entry['Course Code'],
                        entry['Course Title'],
                        entry['Time'],
                        entry['Days'],
                        entry['Room'],
                        entry['Lec'],
                        entry['Lab'],
                        f"{entry['Units']:.2f}",
                        entry['No. of Hours'],
                        f"{entry['ETL Units']:.2f}",
                        entry['Instructor/Professor'],
                        entry['Program-Year-Block']
                    ))
                    count += 1
            
            self.summary_label.config(text=f"Showing: {count} course schedules")
        else:
            # Refresh timetable grid
            self.populate_timetable_grid()
            
            # Update summary
            filtered_count = len([e for e in self.schedules_data 
                                 if filter_value == 'All Schedules' or e['Program-Year-Block'] == filter_value])
            self.summary_label.config(text=f"Showing: {filtered_count} course schedules")
        
    def sort_treeview(self, col):
        """Sort treeview by column."""
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        items.sort()
        
        for index, (val, k) in enumerate(items):
            self.tree.move(k, '', index)
    
    def change_view_mode(self, event=None):
        """Switch between List View and Timetable Grid View."""
        mode = self.view_mode_var.get()
        
        if mode == "List View":
            self.grid_view_frame.grid_forget()
            self.list_view_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        elif mode == "Timetable Grid":
            self.list_view_frame.grid_forget()
            self.grid_view_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self.populate_timetable_grid()
    
    def get_course_color(self, course_code):
        """Generate a consistent color for a course based on its code."""
        # Hash the course code to get a consistent color
        hash_val = hash(course_code)
        
        # Generate pastel colors for better readability
        colors = [
            '#FFE5E5',  # Light red
            '#E5F5FF',  # Light blue
            '#E5FFE5',  # Light green
            '#FFF5E5',  # Light orange
            '#F5E5FF',  # Light purple
            '#FFE5F5',  # Light pink
            '#E5FFFF',  # Light cyan
            '#FFFFE5',  # Light yellow
            '#F0E5FF',  # Light lavender
            '#E5FFF0',  # Light mint
        ]
        return colors[abs(hash_val) % len(colors)]
    
    def populate_timetable_grid(self):
        """Create a timetable grid view (M-F on x-axis, 8AM-5PM on y-axis)."""
        # Clear existing grid
        for widget in self.grid_inner_frame.winfo_children():
            widget.destroy()

        if not self.schedules_data:
            self.log_status("⚠️ No schedules_data available for timetable grid")
            ttk.Label(self.grid_inner_frame, text="No schedule data available").grid(row=0, column=0, padx=20, pady=20)
            return

        # Get filtered data
        filter_value = self.filter_var.get()
        filtered_data = [
            entry for entry in self.schedules_data
            if filter_value == 'All Schedules' or entry['Program-Year-Block'] == filter_value
        ]

        self.log_status("\n🔍 Timetable Grid Debug:")
        self.log_status(f"   Total schedules: {len(self.schedules_data)}")
        self.log_status(f"   Filter: {filter_value}")
        self.log_status(f"   Filtered data: {len(filtered_data)} entries")

        if not filtered_data:
            self.log_status("   ⚠️ No data matches the filter")
            ttk.Label(self.grid_inner_frame, text="No data for selected filter").grid(row=0, column=0, padx=20, pady=20)
            return

        # Debug: Show first entry
        sample = filtered_data[0]
        self.log_status(f"   Sample entry keys: {list(sample.keys())}")
        self.log_status(f"   Time: '{sample.get('Time', 'N/A')}'")
        self.log_status(f"   Days: '{sample.get('Days', 'N/A')}'")
        self.log_status(f"   Course Code: '{sample.get('Course Code', 'N/A')}'")

        # Define time slots (8 AM to 5 PM, 30-minute intervals)
        time_slots = []
        for hour in range(8, 17):
            time_slots.append(f"{hour:02d}:00")
            time_slots.append(f"{hour:02d}:30")

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        day_abbrev = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'TH': 'Thursday', 'F': 'Friday'}

        # Create header row
        ttk.Label(self.grid_inner_frame, text="Time", font=('Segoe UI', 9, 'bold'),
                  relief=tk.RIDGE, padding=5).grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        for col_idx, day in enumerate(days, start=1):
            ttk.Label(self.grid_inner_frame, text=day, font=('Segoe UI', 9, 'bold'),
                      relief=tk.RIDGE, padding=5).grid(row=0, column=col_idx, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create a structure to track course blocks: [day][time_slot_index] = course_info
        course_blocks = {day: {} for day in days}
        skip_cells = {day: set() for day in days}  # Track cells that should be skipped (covered by rowspan)

        # Parse schedule data and identify course blocks
        parsed_count = 0
        error_count = 0

        for entry in filtered_data:
            course_code = entry.get('Course Code', '')
            course_title = entry.get('Course Title', '')

            # --- FIX: Get the RAW multiline time string ---
            time_str_raw = entry.get('Time', '')
            days_str = entry.get('Days', '')
            room_str = entry.get('Room', '')

            if not time_str_raw or not days_str:  # --- FIX: Check the raw string
                self.log_status(
                    f"   ⚠️ Skipping {course_code}: missing time or days (time='{time_str_raw}', days='{days_str}')"
                )
                error_count += 1
                continue

            # Parse days once per entry (this was correct)
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
                    self.log_status(
                        f"   ⚠️ Skipping unknown day char '{days_str[idx]}' in '{days_str}' for {course_code}'"
                    )
                    idx += 1

            if not course_days:
                self.log_status(f"   ⚠️ No valid days found for {course_code} from '{days_str}'")
                error_count += 1
                continue

            # --- FIX: Loop through each *individual* time slot from the multiline string ---
            for time_str in time_str_raw.split('\n'):
                time_str = time_str.strip()  # Clean up whitespace
                if not time_str:
                    continue  # Skip empty lines

                try:
                    parts = time_str.split('-')
                    if len(parts) != 2:
                        self.log_status(f"   ⚠️ Invalid time format for {course_code}: '{time_str}'")
                        error_count += 1
                        continue
                    start_time = parts[0].strip()
                    end_time = parts[1].strip()
                except Exception as exc:
                    self.log_status(f"   ⚠️ Error parsing time '{time_str}' for {course_code}: {exc}")
                    error_count += 1
                    continue

                try:
                    start_idx = time_slots.index(start_time)
                    end_idx = start_idx + 1
                    for slot_idx in range(start_idx + 1, len(time_slots)):
                        if time_slots[slot_idx] >= end_time:
                            end_idx = slot_idx
                            break
                    else:
                        end_idx = len(time_slots)

                    rowspan = end_idx - start_idx
                    if rowspan < 1:
                        rowspan = 1

                    for day in course_days:
                        if day not in course_blocks:
                            continue

                        conflict = False
                        for slot_idx in range(start_idx, start_idx + rowspan):
                            if slot_idx in course_blocks[day] or slot_idx in skip_cells[day]:
                                existing = course_blocks[day].get(slot_idx, {}).get('code', 'another course (rowspan)')
                                self.log_status(
                                    f"   ⚠️ Conflict for {course_code} on {day} at {time_str}. "
                                    f"Slot already taken by {existing}."
                                )
                                error_count += 1
                                conflict = True
                                break

                        if conflict:
                            continue

                        course_blocks[day][start_idx] = {
                            'code': course_code,
                            'title': course_title,
                            'room': room_str,
                            'rowspan': rowspan,
                            'time': time_str
                        }

                        for slot_idx in range(start_idx + 1, start_idx + rowspan):
                            skip_cells[day].add(slot_idx)

                        parsed_count += 1

                except (ValueError, IndexError) as exc:
                    self.log_status(
                        f"   ⚠️ Could not parse time '{time_str}' (is it in the 8-5 range?) for {course_code}: {exc}"
                    )
                    error_count += 1
                    continue
            # --- END OF FIX LOOP ---

        self.log_status(f"   ✓ Parsed {parsed_count} course blocks, {error_count} errors")
        self.log_status(f"   Course blocks created: {sum(len(blocks) for blocks in course_blocks.values())}")

        # Populate grid cells (This part was correct)
        for row_idx, time_slot in enumerate(time_slots, start=1):
            slot_idx = row_idx - 1  # Convert to 0-based index

            ttk.Label(
                self.grid_inner_frame,
                text=time_slot,
                relief=tk.RIDGE,
                padding=5,
                font=('Segoe UI', 8),
            ).grid(row=row_idx, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

            for col_idx, day in enumerate(days, start=1):
                if slot_idx in skip_cells[day]:
                    continue

                if slot_idx in course_blocks[day]:
                    course = course_blocks[day][slot_idx]
                    cell_text = f"{course['code']}\n{course['title']}\n{course['room']}\n{course['time']}"

                    cell_frame = tk.Frame(
                        self.grid_inner_frame,
                        relief=tk.RIDGE,
                        borderwidth=1,
                        bg=self.get_course_color(course['code'])
                    )
                    cell_frame.grid(
                        row=row_idx,
                        column=col_idx,
                        rowspan=course['rowspan'],
                        sticky=(tk.W, tk.E, tk.N, tk.S)
                    )

                    cell_label = tk.Label(
                        cell_frame,
                        text=cell_text,
                        font=('Segoe UI', 8),
                        bg=self.get_course_color(course['code']),
                        justify=tk.LEFT,
                        anchor='nw',
                        padx=3,
                        pady=3
                    )
                    cell_label.pack(fill=tk.BOTH, expand=True)

                else:
                    ttk.Label(self.grid_inner_frame, text="", relief=tk.RIDGE, padding=5).grid(
                        row=row_idx, column=col_idx, sticky=(tk.W, tk.E, tk.N, tk.S)
                    )

        for col in range(6):
            self.grid_inner_frame.columnconfigure(col, weight=1, minsize=120)
            
    def export_schedules(self):
        """Export all schedules to CSV files."""
        if not self.optimizer:
            return
            
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return
            
        try:
            self.log_status(f"\n💾 Exporting schedules to: {output_dir}")
            self.optimizer.export_all_schedules(output_dir)
            self.log_status("   ✓ All schedules exported successfully!")
            messagebox.showinfo("Success", f"Schedules exported to:\n{output_dir}")
            self.update_status_bar(f"Schedules exported to {output_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
            
    def clear_results(self):
        """Clear all results and reset UI."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.schedules_data = []
        self.optimizer = None
        self.summary_label.config(text="No schedules generated yet")
        self.filter_combo['values'] = ['All Schedules']
        self.filter_var.set('All Schedules')
        self.export_button.config(state=tk.DISABLED)
        self.clear_log()
        self.update_status_bar("Results cleared")
        
    def stop_optimization(self):
        """Stop the optimization (placeholder for future implementation)."""
        self.is_running = False
        self.log_status("\n⏹ Optimization stopped by user")
        self.update_status_bar("Optimization stopped")
        
    def log_status(self, message):
        """Add message to status text."""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self):
        """Clear status text."""
        self.status_text.delete(1.0, tk.END)
        
    def update_status_bar(self, message):
        """Update status bar message."""
        self.status_bar_label.config(text=message)
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))

    def update_timer(self):
        """Update the elapsed time label every second."""
        if self.is_running:
            elapsed = datetime.now() - self.start_time
            total_seconds = int(elapsed.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.timer_label.config(text=f"Elapsed Time: {time_str}")
            self.root.after(1000, self.update_timer)


def main():
    """Main entry point for GUI application."""
    root = tk.Tk()
    app = SchedulerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()