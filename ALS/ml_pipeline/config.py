# Machine Learning Pipeline Configurations

import os

# Signal Acquisition Parameters
SAMPLING_RATE = 1000  # Hz
NOTCH_FREQ = 50.0     # Hz (Mains power frequency for Asia/Europe)
NOTCH_Q = 30.0        # Quality factor for IIR notch filter
BANDPASS_LOW = 20.0   # Hz (Eliminates low-freq motion artifacts)
BANDPASS_HIGH = 450.0 # Hz (Standard cutoff for sEMG signal power)

# Windowing Parameters
WINDOW_SIZE_MS = 500  # 500 ms sliding window
WINDOW_STEP_MS = 100  # 100 ms sliding step (75% - 80% overlap)
WINDOW_SIZE = int((WINDOW_SIZE_MS / 1000) * SAMPLING_RATE) # 500 samples
WINDOW_STEP = int((WINDOW_STEP_MS / 1000) * SAMPLING_RATE) # 100 samples

# Protocol Parameters
MUSCLES = ["Masseter", "Orbicularis Oris", "Submental"]
RECORDING_DURATION_SEC = 5 # Duration per muscle session in seconds
SAMPLES_PER_RECORDING = RECORDING_DURATION_SEC * SAMPLING_RATE # 5000 samples

# Machine Learning & Wavelet Settings
WAVELET_FAMILY = 'db4'  # Daubechies 4 wavelet (ideal for sEMG transients)
WAVELET_LEVEL = 3       # 3-level discrete decomposition (D1, D2, D3, A3)

# Model Storage Paths
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "als_emg_classifier.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "als_emg_scaler.joblib")

# Create model directory if it doesn't exist
os.makedirs(MODEL_DIR, exist_ok=True)
