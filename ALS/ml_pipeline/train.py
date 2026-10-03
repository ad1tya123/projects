import os
import numpy as np
import pandas as pd

# Safe import for joblib
try:
    import joblib
except ImportError:
    # Fallback to pickle if joblib is missing, but we will write with joblib and handle fallback
    import pickle as joblib

from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from ml_pipeline.config import (
    MODEL_PATH, SCALER_PATH, MUSCLES, SAMPLING_RATE, 
    WINDOW_SIZE, WINDOW_STEP
)
from ml_pipeline.filters import clean_emg_signal
from ml_pipeline.features import extract_all_window_features, convert_features_to_vector, get_feature_names

def load_subject_trial(subject_dir, muscle_name):
    """
    Loads raw 12-bit ADC data for a specific subject and muscle.
    """
    filename = f"{muscle_name.lower().replace(' ', '_')}.csv"
    filepath = os.path.join(subject_dir, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing data for {muscle_name} at {filepath}")
    return np.loadtxt(filepath, dtype=float)

def extract_trial_features(signal):
    """
    Applies filtering and segments the signal into sliding windows.
    Extracts features for each window and averages them across the trial
    to represent the stable muscle profile.
    """
    # 1. Apply Notch + Butterworth Bandpass
    cleaned = clean_emg_signal(signal, SAMPLING_RATE)
    
    # 2. Extract sliding windows
    features_list = []
    n_samples = len(cleaned)
    
    for start in range(0, n_samples - WINDOW_SIZE + 1, WINDOW_STEP):
        end = start + WINDOW_SIZE
        window = cleaned[start:end]
        
        # Extract features from the current window
        feat_dict = extract_all_window_features(window)
        vector = convert_features_to_vector(feat_dict)
        features_list.append(vector)
        
    # Return the average feature vector across all windows (shape: n_features,)
    if len(features_list) == 0:
        n_features = len(get_feature_names())
        return np.zeros(n_features)
        
    return np.mean(features_list, axis=0)

def extract_full_dataset(data_dir="data"):
    """
    Loads raw data for all subjects, filters and extracts features,
    and returns feature vectors and labels.
    """
    metadata_path = os.path.join(data_dir, "metadata.csv")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata index not found at {metadata_path}. Please run dataset_downloader.py first.")
        
    df_meta = pd.read_csv(metadata_path)
    
    X = []
    y = []
    subjects = []
    
    print("\n--- Extracting features from all clinical subjects ---")
    
    for idx, row in df_meta.iterrows():
        subj_id = row['subject_id']
        label = row['label']
        subj_dir = os.path.join(data_dir, subj_id)
        
        print(f"Processing {subj_id} (Label: {label})...")
        
        # Concatenate features of all 3 muscles for this subject
        subject_features = []
        for muscle in MUSCLES:
            try:
                raw_signal = load_subject_trial(subj_dir, muscle)
                muscle_avg_features = extract_trial_features(raw_signal)
                subject_features.extend(muscle_avg_features)
            except Exception as e:
                print(f"  Error reading {muscle} for {subj_id}: {e}")
                # Append zero padding on failure
                n_feat = len(get_feature_names())
                subject_features.extend(np.zeros(n_feat))
                
        X.append(subject_features)
        y.append(label)
        subjects.append(subj_id)
        
    return np.array(X), np.array(y), subjects

def run_loso_cross_validation(X, y, subjects):
    """
    Performs Leave-One-Subject-Out (LOSO) Cross-Validation.
    This is the gold standard for validating biological ML models to ensure
    subject-independence.
    """
    n_samples = len(X)
    y_true = []
    y_pred = []
    
    print("\n--- Starting Leave-One-Subject-Out (LOSO) Cross-Validation ---")
    
    for test_idx in range(n_samples):
        # 1. Split into train and test sets
        X_test, y_test = X[test_idx:test_idx+1], y[test_idx:test_idx+1]
        
        X_train = np.delete(X, test_idx, axis=0)
        y_train = np.delete(y, test_idx, axis=0)
        
        # 2. Scale features independently per fold to prevent data leakage
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 3. Train RBF Support Vector Classifier (RBF is ideal for non-linear bio-boundaries)
        clf = SVC(kernel='rbf', C=2.0, gamma='scale', probability=True, random_state=42)
        clf.fit(X_train_scaled, y_train)
        
        # 4. Predict
        pred = clf.predict(X_test_scaled)[0]
        
        y_true.append(y_test[0])
        y_pred.append(pred)
        
        status = "PASSED" if pred == y_test[0] else "FAILED"
        print(f"  Fold {test_idx+1}/{n_samples} | Test Subject: {subjects[test_idx]} | True Label: {y_test[0]} | Pred: {pred} | {status}")
        
    # Calculate global metrics
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    print("\n================ LOSO VALIDATION REPORT ================")
    print(f"  Global Accuracy: {acc * 100:.2f}%")
    print(f"  Precision:       {prec * 100:.2f}%")
    print(f"  Recall (Sens.):  {rec * 100:.2f}%")
    print(f"  F1-Score:        {f1 * 100:.2f}%")
    print("========================================================")
    
    return acc

def train_and_save_final_model(X, y):
    """
    Trains the final model on the ENTIRE clinical dataset and saves it
    along with the scaler to disk for live desktop application inference.
    """
    print("\nTraining final diagnostic model on entire dataset...")
    
    # 1. Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 2. Train classifier (RBF SVM)
    clf = SVC(kernel='rbf', C=2.0, gamma='scale', probability=True, random_state=42)
    clf.fit(X_scaled, y)
    
    # 3. Save model components
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    
    print(f"  Saved final model to:  {MODEL_PATH}")
    print(f"  Saved final scaler to: {SCALER_PATH}")
    print("Model ready for real-time inference!")

if __name__ == "__main__":
    # Check if data exists
    if not os.path.exists(os.path.join("data", "metadata.csv")):
        from ml_pipeline.dataset_downloader import build_open_source_emg_dataset
        build_open_source_emg_dataset(num_subjects=20)
        
    X, y, subjects = extract_full_dataset()
    
    # Run Leave-One-Subject-Out validation
    run_loso_cross_validation(X, y, subjects)
    
    # Train and serialize the model
    train_and_save_final_model(X, y)
