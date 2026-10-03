import numpy as np
from scipy.signal import iirnotch, butter, filtfilt, lfilter
from ml_pipeline.config import SAMPLING_RATE, NOTCH_FREQ, NOTCH_Q, BANDPASS_LOW, BANDPASS_HIGH

def get_notch_coeff(fs=SAMPLING_RATE, f0=NOTCH_FREQ, Q=NOTCH_Q):
    """
    Computes coefficients for an IIR notch filter to remove powerline noise.
    """
    b, a = iirnotch(f0, Q, fs)
    return b, a

def get_bandpass_coeff(fs=SAMPLING_RATE, lowcut=BANDPASS_LOW, highcut=BANDPASS_HIGH, order=4):
    """
    Computes coefficients for a Butterworth bandpass filter.
    """
    # Nyquist frequency is half the sampling rate
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def clean_emg_signal(data, fs=SAMPLING_RATE):
    """
    Applies both Notch and Butterworth Bandpass filters to an array of raw EMG data.
    Uses zero-phase filtfilt to avoid phase-shift distortion, which is critical 
    for preserving wave-shapes for wavelet decomposition.
    """
    # If there are not enough samples to filter, return the raw data
    if len(data) < 15:  # Minimum length for filtfilt is 3 * max(len(a), len(b))
        return data

    # 1. Apply 50Hz Notch Filter
    b_notch, a_notch = get_notch_coeff(fs)
    notch_filtered = filtfilt(b_notch, a_notch, data)
    
    # 2. Apply 20-450Hz Bandpass Filter
    b_band, a_band = get_bandpass_coeff(fs)
    cleaned_signal = filtfilt(b_band, a_band, notch_filtered)
    
    return cleaned_signal

class RealTimeEMGFilter:
    """
    Stateful real-time filter to process single samples or small buffers with low latency.
    Keeps track of historical signal filter state to avoid boundary artifacts.
    """
    def __init__(self, fs=SAMPLING_RATE):
        self.fs = fs
        
        # Initialize notch filter coefficients & state
        self.b_notch, self.a_notch = get_notch_coeff(fs)
        # We initialize the filter state with zeros
        # Note: self.zi_notch will be created/updated dynamically or statically
        self.zi_notch = np.zeros(max(len(self.b_notch), len(self.a_notch)) - 1)
        
        # Initialize bandpass filter coefficients & state
        self.b_band, self.a_band = get_bandpass_coeff(fs)
        self.zi_band = np.zeros(max(len(self.b_band), len(self.a_band)) - 1)
        
    def process_sample(self, val):
        """
        Process a single raw integer ADC sample. Returns a float filtered value.
        """
        # Notch filter
        val_notch, self.zi_notch = lfilter(self.b_notch, self.a_notch, [val], zi=self.zi_notch)
        # Bandpass filter
        val_clean, self.zi_band = lfilter(self.b_band, self.a_band, val_notch, zi=self.zi_band)
        
        return float(val_clean[0])

    def reset(self):
        """Resets the state of the digital filters."""
        self.zi_notch = np.zeros(max(len(self.b_notch), len(self.a_notch)) - 1)
        self.zi_band = np.zeros(max(len(self.b_band), len(self.a_band)) - 1)
