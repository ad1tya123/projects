import numpy as np
import scipy.signal

# Safe import for PyWavelets (pywt)
try:
    import pywt
    PYWT_AVAILABLE = True
except ImportError:
    PYWT_AVAILABLE = False

from ml_pipeline.config import SAMPLING_RATE, WAVELET_FAMILY, WAVELET_LEVEL

def extract_time_domain_features(window, threshold=0.015):
    """
    Extracts time-domain features from an EMG window.
    Inputs:
      window: 1D numpy array of filtered EMG samples.
      threshold: noise threshold in volts/ADC units to avoid counting background hum for ZC/SSC.
    Returns:
      dict: time-domain features.
    """
    n = len(window)
    if n == 0:
        return {"RMS": 0.0, "MAV": 0.0, "WL": 0.0, "ZC": 0, "SSC": 0}
        
    # 1. Root Mean Square (RMS)
    rms = np.sqrt(np.mean(window ** 2))
    
    # 2. Mean Absolute Value (MAV)
    mav = np.mean(np.abs(window))
    
    # 3. Waveform Length (WL)
    wl = np.sum(np.abs(np.diff(window)))
    
    # 4. Zero Crossings (ZC)
    # Detects sign changes exceeding noise threshold
    zc = 0
    for i in range(n - 1):
        if (window[i] * window[i+1] < 0) and (np.abs(window[i] - window[i+1]) >= threshold):
            zc += 1
            
    # 5. Slope Sign Changes (SSC)
    # Detects peaks or troughs exceeding noise threshold
    ssc = 0
    for i in range(1, n - 1):
        cond1 = (window[i] > window[i-1]) and (window[i] > window[i+1])
        cond2 = (window[i] < window[i-1]) and (window[i] < window[i+1])
        if (cond1 or cond2) and (max(np.abs(window[i] - window[i-1]), np.abs(window[i] - window[i+1])) >= threshold):
            ssc += 1
            
    return {
        "RMS": rms,
        "MAV": mav,
        "WL": wl,
        "ZC": float(zc) / n,  # Normalized by window size
        "SSC": float(ssc) / n  # Normalized by window size
    }

def extract_frequency_domain_features(window, fs=SAMPLING_RATE):
    """
    Extracts frequency-domain features from an EMG window.
    Computes Power Spectral Density (PSD) using FFT.
    Returns:
      dict: Mean Frequency (MNF) and Median Frequency (MDF).
    """
    n = len(window)
    if n < 2 or np.all(window == 0):
        return {"MNF": 0.0, "MDF": 0.0}
        
    # Compute Power Spectral Density (PSD)
    # We use rfft (Real FFT) and compute the power of positive frequencies
    fft_vals = np.fft.rfft(window)
    psd = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0/fs)
    
    sum_psd = np.sum(psd)
    if sum_psd == 0:
        return {"MNF": 0.0, "MDF": 0.0}
        
    # 1. Mean Frequency (MNF)
    mnf = np.sum(freqs * psd) / sum_psd
    
    # 2. Median Frequency (MDF)
    # MDF is the frequency that divides the PSD into two equal parts
    cumulative_psd = np.cumsum(psd)
    half_power = sum_psd / 2.0
    mdf_idx = np.searchsorted(cumulative_psd, half_power)
    # Safety check on indices
    mdf_idx = min(max(mdf_idx, 0), len(freqs) - 1)
    mdf = freqs[mdf_idx]
    
    return {
        "MNF": mnf,
        "MDF": mdf
    }

def extract_wavelet_features(window, wavelet=WAVELET_FAMILY, level=WAVELET_LEVEL):
    """
    Decomposes the EMG window using Discrete Wavelet Transform (DWT).
    Extracts energy (mean square) of approximation and detail coefficients.
    Returns:
      dict: Wavelet energy features.
    """
    features = {}
    if not PYWT_AVAILABLE:
        # Fallback if PyWavelets is not installed
        for i in range(1, level + 1):
            features[f"DWT_D{i}_Energy"] = 0.0
        features[f"DWT_A{level}_Energy"] = 0.0
        return features

    try:
        # 3-Level DWT decomposition (e.g. for db4, returns [A3, D3, D2, D1])
        coeffs = pywt.wavedec(window, wavelet, level=level)
        
        # Coeffs are returned in order: [cA_n, cD_n, cD_n-1, ..., cD_1]
        approx_coeff = coeffs[0]
        detail_coeffs = coeffs[1:]  # This is [cD_3, cD_2, cD_1]
        
        # Calculate Energy of Approximation coefficients (cA_3)
        features[f"DWT_A{level}_Energy"] = np.mean(approx_coeff ** 2)
        
        # Calculate Energy of Detail coefficients (cD_3, cD_2, cD_1)
        # Note: detail_coeffs contains details in descending order of level (D3, D2, D1)
        for idx, det in enumerate(detail_coeffs):
            current_level = level - idx
            features[f"DWT_D{current_level}_Energy"] = np.mean(det ** 2)
            
    except Exception:
        # Fallback if DWT fails due to size bounds or errors
        for i in range(1, level + 1):
            features[f"DWT_D{i}_Energy"] = 0.0
        features[f"DWT_A{level}_Energy"] = 0.0
        
    return features

def extract_all_window_features(window):
    """
    Extracts all Time-Domain, Frequency-Domain, and Wavelet features from an EMG window
    and returns a flattened dictionary of numeric features.
    """
    # Ensure window is a numpy array
    window = np.array(window)
    
    # Extract features
    td_feat = extract_time_domain_features(window)
    fd_feat = extract_frequency_domain_features(window)
    wt_feat = extract_wavelet_features(window)
    
    # Merge dictionaries
    all_features = {}
    all_features.update(td_feat)
    all_features.update(fd_feat)
    all_features.update(wt_feat)
    
    return all_features

def get_feature_names():
    """
    Returns the exact list of feature keys in the correct order.
    """
    # Keys from time domain
    keys = ["RMS", "MAV", "WL", "ZC", "SSC"]
    # Keys from frequency domain
    keys += ["MNF", "MDF"]
    # Keys from wavelet domain (A3, D3, D2, D1)
    keys += [f"DWT_A{WAVELET_LEVEL}_Energy"]
    for i in range(1, WAVELET_LEVEL + 1):
        keys += [f"DWT_D{i}_Energy"]
    return keys

def convert_features_to_vector(features_dict):
    """
    Converts a features dictionary to a sorted float list vector.
    """
    names = get_feature_names()
    return [features_dict.get(name, 0.0) for name in names]
