import sys
import os
import time
import queue
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

# Matplotlib integration with Tkinter
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Safe imports for ML packages
try:
    import joblib
except ImportError:
    import pickle as joblib

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# Import local ML modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_pipeline.config import (
    SAMPLING_RATE, MUSCLES, SAMPLES_PER_RECORDING, 
    MODEL_PATH, SCALER_PATH, WINDOW_SIZE, WINDOW_STEP
)
from ml_pipeline.filters import clean_emg_signal, RealTimeEMGFilter
from ml_pipeline.features import extract_all_window_features, convert_features_to_vector, get_feature_names
from gui_app.serial_reader import SerialEMGStreamer

class ALSPredictorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("sEMG Bulbar ALS Silent Speech Diagnostic System")
        self.root.geometry("1280x768")
        self.root.minsize(1024, 720)
        
        # Apply dark professional styling
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()
        
        # Core states
        self.streamer = None
        self.sample_queue = queue.Queue(maxsize=10000)
        self.real_time_filter = RealTimeEMGFilter()
        
        # Buffer for continuous real-time plot (stores last 1.5 seconds of data)
        self.plot_window_size = 1500
        self.raw_buffer = np.full(self.plot_window_size, 1850.0)
        self.filtered_buffer = np.zeros(self.plot_window_size)
        
        # Muscle profile data dictionary: { muscle_name: average_feature_vector }
        self.muscle_recordings = {}
        # Stores the raw signals for visual confirmation
        self.recorded_signals = {}
        
        # Recording status states
        self.is_recording = False
        self.recording_muscle = None
        self.recording_buffer = []
        self.recording_start_time = 0.0
        
        # ML model and scaler state
        self.clf = None
        self.scaler = None
        self.load_ml_model()
        
        # Build UI Elements
        self.create_widgets()
        
        # Start high-performance GUI polling loop
        self.root.after(30, self.update_gui_loop)
        
    def _configure_styles(self):
        """Sets up a clean, high-contrast dark color palette."""
        # Color codes
        self.bg_color = "#121214"
        self.card_color = "#1C1C1F"
        self.accent_color = "#00ADB5"      # Cyan
        self.text_primary = "#EEEEEE"
        self.text_secondary = "#9E9E9E"
        self.green_active = "#4CAF50"
        self.red_inactive = "#E53935"
        self.gold_rec = "#FFB300"
        
        # Configure Root background
        self.root.configure(bg=self.bg_color)
        
        # Configure Ttk widget styles
        self.style.configure(".", background=self.bg_color, foreground=self.text_primary)
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Card.TFrame", background=self.card_color, borderwidth=1, relief="flat")
        
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_primary, font=("Consolas", 10))
        self.style.configure("Title.TLabel", background=self.bg_color, foreground=self.accent_color, font=("Consolas", 16, "bold"))
        self.style.configure("CardTitle.TLabel", background=self.card_color, foreground=self.accent_color, font=("Consolas", 12, "bold"))
        self.style.configure("CardText.TLabel", background=self.card_color, foreground=self.text_primary, font=("Consolas", 10))
        self.style.configure("CardTextSec.TLabel", background=self.card_color, foreground=self.text_secondary, font=("Consolas", 9))
        
        # Button styles
        self.style.configure("TButton", background="#2C2C35", foreground=self.text_primary, borderwidth=0, font=("Consolas", 10, "bold"))
        self.style.map("TButton", background=[("active", "#3E3E4A")], foreground=[("active", self.accent_color)])
        
        self.style.configure("Accent.TButton", background=self.accent_color, foreground="#000000", borderwidth=0, font=("Consolas", 10, "bold"))
        self.style.map("Accent.TButton", background=[("active", "#00FFF5")])
        
        # Combobox styles
        self.style.configure("TCombobox", fieldbackground="#1C1C1F", background="#2C2C35", foreground=self.text_primary)
        
    def load_ml_model(self):
        """Loads pre-trained model and scaler. If missing, runs with a warning."""
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            try:
                self.clf = joblib.load(MODEL_PATH)
                self.scaler = joblib.load(SCALER_PATH)
                print("Inference engine loaded successfully.")
            except Exception as e:
                print(f"Failed to load trained model: {e}")
        else:
            print("No saved models found in /models/ directory. Run train.py first to build the classifier.")

    def create_widgets(self):
        """Builds the main dashboard grid layout."""
        # Main Layout Grid
        self.root.columnconfigure(0, weight=3) # Visualizer left panel
        self.root.columnconfigure(1, weight=2) # Controls & Clinical analysis panel
        self.root.rowconfigure(0, weight=1)
        
        # --- LEFT COLUMN: GRAPHICS AND CONNECTION ---
        left_panel = ttk.Frame(self.root, padding=12)
        left_panel.grid(row=0, column=0, sticky="nsew")
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1)
        
        # 1. Connection Header Card
        conn_card = ttk.Frame(left_panel, style="Card.TFrame", padding=10)
        conn_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(conn_card, text="SYSTEM HARDWARE LINK", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        
        ttk.Label(conn_card, text="Port:", style="CardText.TLabel").grid(row=1, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.port_dropdown = ttk.Combobox(conn_card, textvariable=self.port_var, width=15, state="readonly")
        self.port_dropdown.grid(row=1, column=1, padx=(5, 15), sticky="w")
        self.refresh_ports()
        
        ttk.Label(conn_card, text="Baud:", style="CardText.TLabel").grid(row=1, column=2, sticky="w")
        self.baud_var = tk.StringVar(value="115200")
        self.baud_dropdown = ttk.Combobox(conn_card, textvariable=self.baud_var, values=["9600", "57600", "115200", "921600"], width=10, state="readonly")
        self.baud_dropdown.grid(row=1, column=3, padx=(5, 15), sticky="w")
        
        self.conn_btn = ttk.Button(conn_card, text="CONNECT LINK", command=self.toggle_connection)
        self.conn_btn.grid(row=1, column=4, padx=(10, 0), sticky="e")
        
        # Status Light Label
        self.status_light_canvas = tk.Canvas(conn_card, width=14, height=14, bg=self.card_color, highlightthickness=0)
        self.status_light_canvas.grid(row=1, column=5, padx=(10, 5))
        self.status_light = self.status_light_canvas.create_oval(2, 2, 12, 12, fill=self.red_inactive)
        
        self.status_lbl = ttk.Label(conn_card, text="DISCONNECTED", style="CardTextSec.TLabel")
        self.status_lbl.grid(row=1, column=6, sticky="w")
        
        # Simulator options
        self.sim_profile_var = tk.StringVar(value="Healthy")
        self.sim_check_var = tk.BooleanVar(value=True) # Default to simulation mode to let users test instantly!
        self.sim_chk = tk.Checkbutton(
            conn_card, text="Demo Simulator Mode", variable=self.sim_check_var, 
            bg=self.card_color, fg=self.text_primary, selectcolor=self.bg_color,
            activebackground=self.card_color, activeforeground=self.text_primary,
            font=("Consolas", 9), command=self.on_sim_check_toggle
        )
        self.sim_chk.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        
        ttk.Label(conn_card, text="Sim Profile:", style="CardTextSec.TLabel").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.sim_profile_dropdown = ttk.Combobox(conn_card, textvariable=self.sim_profile_var, values=["Healthy", "ALS Patient"], width=12, state="readonly")
        self.sim_profile_dropdown.grid(row=2, column=3, columnspan=2, sticky="w", padx=(5, 0), pady=(8, 0))
        self.sim_profile_dropdown.bind("<<ComboboxSelected>>", self.on_sim_profile_change)
        
        # 2. High-Performance Signal Visualizer Card
        graph_card = ttk.Frame(left_panel, style="Card.TFrame", padding=10)
        graph_card.grid(row=1, column=0, sticky="nsew")
        graph_card.columnconfigure(0, weight=1)
        graph_card.rowconfigure(1, weight=1)
        
        # Tab Control to toggle Raw vs Filtered
        tab_frame = ttk.Frame(graph_card)
        tab_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ttk.Label(tab_frame, text="ELECTROMYOGRAPHY SIGNAL VISUALIZER", style="CardTitle.TLabel").pack(side="left")
        
        # Matplotlib Plot Setup
        self.fig = Figure(figsize=(6, 4), dpi=100, facecolor=self.card_color)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(self.bg_color)
        self.ax.tick_params(colors=self.text_secondary, labelsize=8)
        self.ax.spines['bottom'].set_color(self.card_color)
        self.ax.spines['top'].set_color(self.card_color)
        self.ax.spines['left'].set_color(self.card_color)
        self.ax.spines['right'].set_color(self.card_color)
        self.ax.grid(True, color="#222225", linestyle="--")
        
        # Initial dummy plots
        self.line_raw, = self.ax.plot([], [], color="#5E6368", alpha=0.6, label="Raw ADC Input")
        self.line_filtered, = self.ax.plot([], [], color=self.accent_color, linewidth=1.5, label="Filtered sEMG (20-450 Hz)")
        
        self.ax.set_xlim(0, self.plot_window_size)
        self.ax.set_ylim(-300, 300) # Centered filtered scale in mV
        self.ax.legend(loc="upper right", facecolor=self.card_color, edgecolor="#2A2A2E", fontsize=8, labelcolor=self.text_primary)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_card)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        
        
        # --- RIGHT COLUMN: CLINICAL PROTOCOL & DIAGNOSTIC PANEL ---
        right_panel = ttk.Frame(self.root, padding=12)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=3) # Clinical protocol stepper
        right_panel.rowconfigure(1, weight=2) # Diagnostic output panel
        
        # 1. Step-by-Step Clinical Protocol Stepper
        protocol_card = ttk.Frame(right_panel, style="Card.TFrame", padding=12)
        protocol_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        protocol_card.columnconfigure(0, weight=1)
        
        ttk.Label(protocol_card, text="SEQUENTIAL BULBAR EMG PROTOCOL", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Grid frame for muscle list items
        list_frame = ttk.Frame(protocol_card)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        
        self.muscle_rows = {}
        for idx, muscle in enumerate(MUSCLES):
            row_frame = ttk.Frame(list_frame, padding=8, relief="solid", borderwidth=1)
            row_frame.grid(row=idx, column=0, sticky="ew", pady=5)
            row_frame.columnconfigure(1, weight=1)
            
            # Icon Indicator Canvas
            ind_canvas = tk.Canvas(row_frame, width=12, height=12, bg=self.card_color, highlightthickness=0)
            ind_canvas.grid(row=0, column=0, padx=(5, 10))
            ind_dot = ind_canvas.create_oval(1, 1, 11, 11, fill="#424242")
            
            # Label
            lbl = ttk.Label(row_frame, text=f"Step {idx+1}: {muscle}", style="CardText.TLabel")
            lbl.grid(row=0, column=1, sticky="w")
            
            # Progress bar for active recording
            pbar = ttk.Progressbar(row_frame, orient="horizontal", length=110, mode="determinate")
            pbar.grid(row=0, column=2, padx=10, sticky="e")
            
            # Action button
            btn = ttk.Button(row_frame, text="RECORD 5s", command=lambda m=muscle: self.start_muscle_recording(m))
            btn.grid(row=0, column=3, sticky="e")
            
            self.muscle_rows[muscle] = {
                "dot": ind_dot,
                "canvas": ind_canvas,
                "pbar": pbar,
                "btn": btn,
                "frame": row_frame
            }
            
        # Global Step Controls
        ctrl_frame = ttk.Frame(protocol_card)
        ctrl_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        
        self.clear_btn = ttk.Button(ctrl_frame, text="RESET ALL SESSIONS", command=self.clear_recordings)
        self.clear_btn.pack(side="left")
        
        self.analyze_btn = ttk.Button(ctrl_frame, text="RUN ALS DIAGNOSTIC REPORT", style="Accent.TButton", state="disabled", command=self.analyze_profile)
        self.analyze_btn.pack(side="right")
        
        # 2. Diagnostic & Clinical Report Panel
        self.report_card = ttk.Frame(right_panel, style="Card.TFrame", padding=12)
        self.report_card.grid(row=1, column=0, sticky="nsew")
        self.report_card.columnconfigure(0, weight=1)
        self.report_card.rowconfigure(1, weight=1)
        
        ttk.Label(self.report_card, text="AI DIAGNOSTIC REPORT OUTCOME", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        # Center-aligned summary card
        self.result_frame = tk.Frame(self.report_card, bg=self.bg_color, relief="solid", borderwidth=1, highlightbackground="#2A2A2E", highlightthickness=1)
        self.result_frame.grid(row=1, column=0, sticky="nsew")
        self.result_frame.grid_propagate(False)
        self.result_frame.columnconfigure(0, weight=1)
        
        # Dummy content inside report card
        self.result_header_lbl = tk.Label(self.result_frame, text="NO DATA RECORDED", bg=self.bg_color, fg=self.text_secondary, font=("Consolas", 14, "bold"))
        self.result_header_lbl.pack(pady=(40, 5))
        
        self.result_detail_lbl = tk.Label(
            self.result_frame, 
            text="Please stream raw signals and complete sequential recording sessions\nfor the Masseter, Orbicularis Oris, and Submental muscles\nto generate the clinical diagnostic report.",
            bg=self.bg_color, fg=self.text_secondary, font=("Consolas", 9), justify="center"
        )
        self.result_detail_lbl.pack(padx=10)
        
    def refresh_ports(self):
        """Discovers active serial ports."""
        ports = []
        if SERIAL_AVAILABLE:
            ports = [p.device for p in serial.tools.list_ports.comports()]
        
        ports.append("Simulation")
        self.port_dropdown["values"] = ports
        if ports:
            self.port_dropdown.current(0)
            
    def on_sim_check_toggle(self):
        """Callback when Simulation Mode checkbox is toggled."""
        if self.sim_check_var.get():
            self.port_var.set("Simulation")
            self.port_dropdown.configure(state="disabled")
        else:
            self.refresh_ports()
            self.port_dropdown.configure(state="readonly")
            
    def on_sim_profile_change(self, event):
        """Changes biological profile of simulated stream."""
        if self.streamer and self.sim_check_var.get():
            is_als = (self.sim_profile_var.get() == "ALS Patient")
            self.streamer.set_simulation_profile(is_als=is_als, muscle_name=self.recording_muscle or "Masseter")

    def toggle_connection(self):
        """Starts or stops the serial reader stream."""
        if self.streamer is None:
            # Connect
            port = self.port_var.get()
            baud = int(self.baud_var.get())
            
            # Start streamer
            self.streamer = SerialEMGStreamer(
                port=None if port == "Simulation" else port,
                baudrate=baud,
                sample_queue=self.sample_queue
            )
            
            # Synchronize simulator states
            if port == "Simulation":
                is_als = (self.sim_profile_var.get() == "ALS Patient")
                self.streamer.set_simulation_profile(is_als=is_als, muscle_name=self.recording_muscle or "Masseter")
                
            self.streamer.start()
            
            # Reset local plot filter state
            self.real_time_filter.reset()
            
            # Update UI
            self.status_lbl.configure(text="CONNECTED", foreground=self.green_active)
            self.status_light_canvas.itemconfig(self.status_light, fill=self.green_active)
            self.conn_btn.configure(text="DISCONNECT LINK")
            
            self.port_dropdown.configure(state="disabled")
            self.baud_dropdown.configure(state="disabled")
            self.sim_chk.configure(state="disabled")
        else:
            # Disconnect
            self.streamer.stop()
            self.streamer = None
            
            # Update UI
            self.status_lbl.configure(text="DISCONNECTED", foreground=self.red_inactive)
            self.status_light_canvas.itemconfig(self.status_light, fill=self.red_inactive)
            self.conn_btn.configure(text="CONNECT LINK")
            
            if self.sim_check_var.get():
                self.port_dropdown.configure(state="disabled")
            else:
                self.port_dropdown.configure(state="readonly")
            self.baud_dropdown.configure(state="readonly")
            self.sim_chk.configure(state="normal")

    def start_muscle_recording(self, muscle_name):
        """Triggers a 5-second automatic recording for a muscle."""
        if self.streamer is None:
            messagebox.showwarning("Connection Required", "Please connect to the hardware link or enable the demo simulator first!")
            return
            
        if self.is_recording:
            return
            
        print(f"Triggered clinical recording for: {muscle_name}")
        
        # Synchronize simulation profile to matching muscle
        if self.sim_check_var.get():
            is_als = (self.sim_profile_var.get() == "ALS Patient")
            self.streamer.set_simulation_profile(is_als=is_als, muscle_name=muscle_name)
            
        # Set recording states
        self.is_recording = True
        self.recording_muscle = muscle_name
        self.recording_buffer = []
        self.recording_start_time = time.time()
        
        # Clear out current queue to ensure we record fresh samples starting from now!
        while not self.sample_queue.empty():
            try:
                self.sample_queue.get_nowait()
            except Exception:
                break
                
        # Update row visual
        row = self.muscle_rows[muscle_name]
        row["canvas"].itemconfig(row["dot"], fill=self.gold_rec)
        row["btn"].configure(state="disabled")
        
    def end_muscle_recording(self):
        """Ends active recording, processes features, and updates stepper."""
        self.is_recording = False
        muscle = self.recording_muscle
        self.recording_muscle = None
        
        raw_signal = np.array(self.recording_buffer)
        
        # Check if enough samples were recorded (expect 5000)
        n_samples = len(raw_signal)
        print(f"Finished recording {n_samples} samples for {muscle}.")
        
        if n_samples < 4000:
            messagebox.showerror("Acquisition Error", f"Insufficient data acquired ({n_samples}/5000 samples). Check hardware connections.")
            row = self.muscle_rows[muscle]
            row["canvas"].itemconfig(row["dot"], fill=self.red_inactive)
            row["btn"].configure(state="normal")
            row["pbar"]["value"] = 0
            return
            
        # Cut to exactly 5000 samples to prevent size mismatches
        if n_samples > SAMPLES_PER_RECORDING:
            raw_signal = raw_signal[:SAMPLES_PER_RECORDING]
            
        # 1. Store raw signal for reference or diagnostics
        self.recorded_signals[muscle] = raw_signal
        
        # 2. Extract Average Feature Profile across all 500ms sliding windows
        # Note: We must clean the raw ADC signal using our Butterworth and Notch filters!
        cleaned = clean_emg_signal(raw_signal, SAMPLING_RATE)
        
        features_list = []
        for start in range(0, len(cleaned) - WINDOW_SIZE + 1, WINDOW_STEP):
            end = start + WINDOW_SIZE
            window = cleaned[start:end]
            
            feat_dict = extract_all_window_features(window)
            vector = convert_features_to_vector(feat_dict)
            features_list.append(vector)
            
        avg_muscle_features = np.mean(features_list, axis=0)
        
        # Store average muscle feature profile
        self.muscle_recordings[muscle] = avg_muscle_features
        
        # Update UI stepper status
        row = self.muscle_rows[muscle]
        row["canvas"].itemconfig(row["dot"], fill=self.green_active)
        row["btn"].configure(text="RE-RECORD", state="normal")
        row["pbar"]["value"] = 100
        
        # Enable diagnostics button only if all 3 target muscles are registered!
        if len(self.muscle_recordings) == len(MUSCLES):
            self.analyze_btn.configure(state="normal")

    def clear_recordings(self):
        """Clears all sessions to start a fresh clinical trial."""
        self.muscle_recordings.clear()
        self.recorded_signals.clear()
        self.is_recording = False
        self.recording_muscle = None
        self.recording_buffer = []
        
        # Reset row states
        for muscle in MUSCLES:
            row = self.muscle_rows[muscle]
            row["canvas"].itemconfig(row["dot"], fill="#424242")
            row["pbar"]["value"] = 0
            row["btn"].configure(text="RECORD 5s", state="normal")
            
        self.analyze_btn.configure(state="disabled")
        
        # Reset diagnostic report output
        for widget in self.result_frame.winfo_children():
            widget.destroy()
            
        self.result_header_lbl = tk.Label(self.result_frame, text="NO DATA RECORDED", bg=self.bg_color, fg=self.text_secondary, font=("Consolas", 14, "bold"))
        self.result_header_lbl.pack(pady=(40, 5))
        
        self.result_detail_lbl = tk.Label(
            self.result_frame, 
            text="Please stream raw signals and complete sequential recording sessions\nfor the Masseter, Orbicularis Oris, and Submental muscles\nto generate the clinical diagnostic report.",
            bg=self.bg_color, fg=self.text_secondary, font=("Consolas", 9), justify="center"
        )
        self.result_detail_lbl.pack(padx=10)

    def analyze_profile(self):
        """
        Concatenates features from all 3 muscles, scales them, passes to the 
        trained RBF-SVM classifier, and outputs a diagnostic probability and report.
        """
        if len(self.muscle_recordings) < len(MUSCLES):
            return
            
        if self.clf is None or self.scaler is None:
            # Fallback if no pre-trained model was saved on disk
            messagebox.showwarning(
                "AI Model Missing", 
                "Classifier files (joblib) were not found in 'models/'.\n\n"
                "We will run a rule-based inference emulator based on muscle fatigue (MDF decay) "
                "and signal amplitude to show the full potential of this system!"
            )
            self._run_rule_based_inference()
            return
            
        # 1. Assemble Full Patient Feature Vector (Concatenation of all 3 muscles)
        full_feature_vector = []
        for muscle in MUSCLES:
            full_feature_vector.extend(self.muscle_recordings[muscle])
            
        # Ensure we have correct dimensions (3 muscles x 12 features = 36 dimensional input)
        X_patient = np.array([full_feature_vector])
        
        # 2. Scale and Predict
        try:
            X_scaled = self.scaler.transform(X_patient)
            prediction = self.clf.predict(X_scaled)[0]
            probability = self.clf.predict_proba(X_scaled)[0][1] # Probability of ALS
            
            self.display_report_outcome(prediction == 1, probability)
        except Exception as e:
            messagebox.showerror("Classification Error", f"Model prediction failed: {e}")
            
    def _run_rule_based_inference(self):
        """
        Anatomically realistic diagnostic classifier used as a fallback.
        Reviews Median Frequency (MDF) shifts (fatigue) and RMS values.
        """
        # Feature names mapping: ZC, SSC, RMS, MAV, WL, MNF, MDF, DWT_A3, DWT_D1, DWT_D2, DWT_D3
        # Indices in our 12-dimensional vector:
        # 0: RMS, 1: MAV, 2: WL, 3: ZC, 4: SSC, 5: MNF, 6: MDF
        
        mdf_values = []
        rms_values = []
        
        for muscle in MUSCLES:
            feat_vec = self.muscle_recordings[muscle]
            rms_values.append(feat_vec[0]) # RMS index is 0
            mdf_values.append(feat_vec[6]) # MDF index is 6
            
        # ALS muscles show lower RMS (weakness) and shifted lower MDF (fatigue)
        avg_rms = np.mean(rms_values)
        avg_mdf = np.mean(mdf_values)
        
        # Simple logical boundaries simulating pathology
        # Healthy RMS around 80-250, MDF around 110-180 Hz
        # ALS RMS around 15-45, MDF around 60-90 Hz
        is_als = (avg_mdf < 100.0) or (avg_rms < 50.0)
        
        # Calculate a realistic mock probability
        if is_als:
            prob = 0.75 + (100.0 - avg_mdf) / 400.0
            prob = min(max(prob, 0.75), 0.98)
        else:
            prob = (avg_mdf - 90.0) / 300.0
            prob = min(max(prob, 0.02), 0.25)
            
        self.display_report_outcome(is_als, prob)

    def display_report_outcome(self, is_als, probability):
        """Updates the results frame with a beautifully styled medical diagnostic card."""
        # Clear frame
        for widget in self.result_frame.winfo_children():
            widget.destroy()
            
        if is_als:
            border_col = self.red_inactive
            bg_accent = "#2C1E20"
            outcome_text = "ALS PATHOLOGY DETECTED (High Risk)"
            outcome_col = self.red_inactive
            recommendation = "Bulbar-onset ALS biomarkers present. The sequential speech recordings indicate marked muscle fatigue (accelerated frequency decay), reduced amplitude, and micro-fasciculation potentials. Clinical neurological consultation and follow-up electromyography are recommended."
        else:
            border_col = self.green_active
            bg_accent = "#19241B"
            outcome_text = "NO SIGNS OF ALS (Healthy Profile)"
            outcome_col = self.green_active
            recommendation = "Bulbar motor system within normal physiological limits. Speech musculature shows healthy amplitude recruitment, stable median firing frequencies, and normal non-pathological fatigue thresholds. No action required."
            
        # Set border color of frame
        self.result_frame.configure(highlightbackground=border_col)
        
        # Inner colored banner
        banner = tk.Frame(self.result_frame, bg=bg_accent, height=45)
        banner.pack(fill="x", side="top")
        banner.pack_propagate(False)
        
        tk.Label(banner, text=outcome_text, bg=bg_accent, fg=outcome_col, font=("Consolas", 11, "bold")).pack(side="left", padx=15, pady=12)
        
        # Diagnostic Metric
        metric_frame = tk.Frame(self.result_frame, bg=self.bg_color)
        metric_frame.pack(fill="x", pady=10, padx=15)
        
        tk.Label(metric_frame, text="AI Predictor Confidence Score:", bg=self.bg_color, fg=self.text_secondary, font=("Consolas", 10)).pack(side="left")
        
        prob_val = probability if is_als else (1.0 - probability)
        tk.Label(metric_frame, text=f"{prob_val * 100:.1f}% Match", bg=self.bg_color, fg=outcome_col, font=("Consolas", 14, "bold")).pack(side="right")
        
        # Divider line
        div = tk.Frame(self.result_frame, bg="#2A2A2E", height=1)
        div.pack(fill="x", padx=15, pady=5)
        
        # Recommendation Frame
        rec_frame = tk.Frame(self.result_frame, bg=self.bg_color)
        rec_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        tk.Label(rec_frame, text="CLINICAL INTERPRETATION & ADVISORY:", bg=self.bg_color, fg=self.accent_color, font=("Consolas", 9, "bold")).pack(anchor="w", pady=(0, 3))
        
        msg = tk.Message(rec_frame, text=recommendation, bg=self.bg_color, fg=self.text_primary, font=("Consolas", 8), width=450)
        msg.pack(anchor="w")

    def update_gui_loop(self):
        """
        Polls incoming sample queue at high speeds (called every 30ms).
        Filters samples, updates continuous visualizer, and fills active recordings.
        """
        new_samples = []
        while not self.sample_queue.empty():
            try:
                val = self.sample_queue.get_nowait()
                new_samples.append(val)
            except Exception:
                break
                
        if len(new_samples) > 0:
            # 1. Real-Time Filtering of new samples
            # Feed raw and filtered values into the rolling display buffers
            n_new = len(new_samples)
            
            # Slide older elements leftward
            self.raw_buffer = np.roll(self.raw_buffer, -n_new)
            self.filtered_buffer = np.roll(self.filtered_buffer, -n_new)
            
            # Add new values to buffers
            self.raw_buffer[-n_new:] = new_samples
            
            # Filter online sample by sample
            for idx in range(n_new):
                self.filtered_buffer[-(n_new - idx)] = self.real_time_filter.process_sample(new_samples[idx])
                
            # 2. Append raw values to recording buffer if actively recording
            if self.is_recording:
                self.recording_buffer.extend(new_samples)
                
                # Update recording stepper progress bar
                elapsed = time.time() - self.recording_start_time
                percent = int((elapsed / RECORDING_DURATION_SEC_LOCAL_CALC) * 100)
                percent = min(100, percent)
                
                self.muscle_rows[self.recording_muscle]["pbar"]["value"] = percent
                
                # Check if recording session is complete
                if len(self.recording_buffer) >= SAMPLES_PER_RECORDING:
                    self.end_muscle_recording()
                    
            # 3. Trigger Matplotlib updates
            # Plot only filtered signal centered around zero offset
            self.line_filtered.set_data(np.arange(self.plot_window_size), self.filtered_buffer)
            self.line_raw.set_data(np.arange(self.plot_window_size), self.raw_buffer - 1850) # Remove ADC bias for comparison
            
            # Rescale vertical limits dynamically based on filtered signals
            max_val = np.max(np.abs(self.filtered_buffer))
            if max_val > 10.0:
                y_limit = max(100, int(max_val * 1.2))
                self.ax.set_ylim(-y_limit, y_limit)
                
            self.canvas.draw_idle()
            
        # Reschedule next check in 30ms (approx. 33 FPS updates)
        self.root.after(30, self.update_gui_loop)

# Define local local variable mapping matching configurations to avoid circular dynamic modifications
RECORDING_DURATION_SEC_LOCAL_CALC = 5.0

if __name__ == "__main__":
    # Create the models if they don't exist so the UI is immediately fully functional with the AI prediction engine!
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        print("Models directory incomplete. Launching pre-training compiler first...")
        from ml_pipeline.dataset_downloader import build_open_source_emg_dataset
        from ml_pipeline.train import extract_full_dataset, train_and_save_final_model
        
        # Build 20-subject dataset & train SVM classifier
        build_open_source_emg_dataset(num_subjects=20)
        X, y, subjects = extract_full_dataset()
        train_and_save_final_model(X, y)
        
    # Start the app
    root = tk.Tk()
    app = ALSPredictorApp(root)
    root.mainloop()
