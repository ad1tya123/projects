import numpy as np
from typing import Dict
from loguru import logger

class CalibrationService:
    def __init__(self):
        self.gene_calibration = {
            "BRCA1": {"pathogenic_mean": -1.2, "pathogenic_std": 0.3, "benign_mean": 0.1, "benign_std": 0.2},
            "TP53": {"pathogenic_mean": -1.5, "pathogenic_std": 0.4, "benign_mean": 0.0, "benign_std": 0.25},
            "default": {"pathogenic_mean": -1.0, "pathogenic_std": 0.35, "benign_mean": 0.05, "benign_std": 0.25}
        }
        
        self.fixed_windows = {
            "BRCA1": {"start": 400, "end": 600, "center": 500},
            "TP53": {"start": 350, "end": 550, "center": 450},
            "default": {"start": 100, "end": 300, "center": 200}
        }
    
    def get_fixed_window(self, gene: str, cds_length: int) -> Dict:
        window = self.fixed_windows.get(gene, self.fixed_windows["default"])
        start = min(window["start"], max(0, cds_length - 200))
        end = min(window["end"], cds_length)
        return {"start": start, "end": end, "center": window["center"]}
    
    def calibrate_dna_score(self, raw_delta: float, gene: str) -> Dict:
        calibration = self.gene_calibration.get(gene, self.gene_calibration["default"])
        
        if raw_delta < -0.5:
            calibrated_score = -1.0
            interpretation = "disruptive"
            confidence = "high"
        elif raw_delta > 0.5:
            calibrated_score = 0.5
            interpretation = "tolerated"
            confidence = "medium"
        else:
            calibrated_score = raw_delta
            interpretation = "neutral"
            confidence = "low"
        

        final_delta = raw_delta if raw_delta != 0 else calibrated_score
        
        return {
            "raw_delta": raw_delta,
            "calibrated_delta": final_delta,
            "interpretation": interpretation,
            "confidence": confidence
        }