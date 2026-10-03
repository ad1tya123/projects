"""
ACMG Classification Service
Implements ACMG/AMP 2015 guidelines for variant classification
"""

from enum import Enum
from typing import Dict, Tuple, Optional, List
from loguru import logger
import numpy as np

class ACMGClassification(str, Enum):
    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely Pathogenic"
    VUS = "Variant of Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"

class ACMGService:
    """ACMG/AMP 2015 variant classification service"""
    
    def __init__(self):
        self.criteria = {
            'PVS1': 1.0,   # Null variant
            'PS1': 0.9,    # Same amino acid change
            'PS2': 0.9,    # De novo
            'PS3': 0.9,    # Functional studies
            'PS4': 0.9,    # ClinVar Pathogenic
            'PM1': 0.6,    # Hotspot
            'PM2': 0.6,    # Moderate protein impact
            'PM3': 0.6,    # ClinVar Likely Pathogenic
            'PM4': 0.6,    # Protein length change
            'PM5': 0.6,    # Novel missense
            'PP1': 0.3,    # Co-segregation
            'PP2': 0.3,    # Missense in gene
            'PP3': 0.3,    # Computational evidence
            'PP4': 0.3,    # Phenotype
            'PP5': 0.3,    # Reputable source
            'BA1': -1.0,   # Allele frequency >5%
            'BS1': -0.9,   # Allele frequency >1%
            'BS2': -0.9,   # Early-onset healthy
            'BS3': -0.9,   # Functional benign
            'BS4': -0.9,   # ClinVar Benign
            'BP1': -0.3,   # Missense different property
            'BP2': -0.3,   # In cis
            'BP3': -0.3,   # In-frame indels
            'BP4': -0.3,   # Computational benign
            'BP5': -0.3,   # ClinVar Likely Benign
            'BP6': -0.3,   # Reputable benign
            'BP7': -0.3,   # Synonymous
        }
    
    def classify(
        self,
        mutation_type,
        dna_delta: float,
        protein_delta: float,
        clinvar_data: Optional[Dict] = None
    ) -> Tuple[ACMGClassification, float, Dict[str, List[str]], str]:
        """
        Classify variant using ACMG/AMP 2015 guidelines
        
        Returns:
            classification, posterior_probability, evidence, summary
        """
        
        evidence: Dict[str, List[str]] = {}
        total_score = 0.0
        
        mutation_type_str = mutation_type.value if hasattr(mutation_type, 'value') else str(mutation_type)
        
        # ============================================
        # 1. CLINVAR OVERRIDE (Highest Priority)
        # ============================================
        
        if clinvar_data:
            significance = clinvar_data.get('clinical_significance', '').lower()
            is_found = clinvar_data.get('found', False)
            
            # If ClinVar says Pathogenic - override to Pathogenic
            if 'pathogenic' in significance and 'likely' not in significance:
                evidence['PS4'] = ["ClinVar: Pathogenic"]
                classification = ACMGClassification.PATHOGENIC
                posterior = 0.95
                summary = f"Pathogenic (ClinVar: {clinvar_data.get('clinical_significance')})"
                logger.info(f"📋 ClinVar override: Pathogenic")
                return classification, posterior, evidence, summary
            
            # If ClinVar says Likely Pathogenic
            elif 'likely pathogenic' in significance:
                evidence['PM3'] = ["ClinVar: Likely Pathogenic"]
                classification = ACMGClassification.LIKELY_PATHOGENIC
                posterior = 0.85
                summary = f"Likely Pathogenic (ClinVar: {clinvar_data.get('clinical_significance')})"
                logger.info(f"📋 ClinVar override: Likely Pathogenic")
                return classification, posterior, evidence, summary
            
            # If ClinVar says Benign - override to Benign
            elif 'benign' in significance and 'likely' not in significance:
                evidence['BS4'] = ["ClinVar: Benign"]
                classification = ACMGClassification.BENIGN
                posterior = 0.05
                summary = f"Benign (ClinVar: {clinvar_data.get('clinical_significance')})"
                logger.info(f"📋 ClinVar override: Benign")
                return classification, posterior, evidence, summary
            
            # If ClinVar says Likely Benign
            elif 'likely benign' in significance:
                evidence['BP5'] = ["ClinVar: Likely Benign"]
                classification = ACMGClassification.LIKELY_BENIGN
                posterior = 0.15
                summary = f"Likely Benign (ClinVar: {clinvar_data.get('clinical_significance')})"
                logger.info(f"📋 ClinVar override: Likely Benign")
                return classification, posterior, evidence, summary
            
            # If ClinVar says Uncertain, don't override
            elif 'uncertain' in significance or 'unknown' in significance:
                logger.info(f"📋 ClinVar says Uncertain, using computational evidence")
        
        # ============================================
        # 2. MUTATION TYPE EVIDENCE
        # ============================================
        
        # PVS1: Null variant (nonsense, frameshift)
        if mutation_type_str in ['frameshift', 'nonsense']:
            evidence['PVS1'] = ["Null variant - loss of function"]
            total_score += self.criteria['PVS1']
            logger.info(f"✅ PVS1: Null variant, score += {self.criteria['PVS1']}")
        
        # PM4: Protein length change (frameshift)
        if mutation_type_str == 'frameshift':
            evidence['PM4'] = ["Frameshift causing protein length change"]
            total_score += self.criteria['PM4']
            logger.info(f"✅ PM4: Frameshift, score += {self.criteria['PM4']}")
        
        # ============================================
        # 3. PROTEIN IMPACT EVIDENCE (for missense)
        # ============================================
        
        if mutation_type_str == 'missense':
            if protein_delta < -5.0:
                evidence['PS1'] = [f"Severe protein impact (Δ={protein_delta:.3f})"]
                total_score += self.criteria['PS1']
                logger.info(f"✅ PS1: Severe protein impact, score += {self.criteria['PS1']}")
            elif protein_delta < -2.0:
                evidence['PM2'] = [f"Moderate protein impact (Δ={protein_delta:.3f})"]
                total_score += self.criteria['PM2']
                logger.info(f"✅ PM2: Moderate protein impact, score += {self.criteria['PM2']}")
            elif protein_delta < -1.0:
                evidence['PP3'] = [f"Mild protein impact (Δ={protein_delta:.3f})"]
                total_score += self.criteria['PP3']
                logger.info(f"✅ PP3: Mild protein impact, score += {self.criteria['PP3']}")
        
        # ============================================
        # 4. DNA IMPACT EVIDENCE
        # ============================================
        
        if dna_delta < -0.5:
            evidence['PP3'] = [f"DNA disruptive (Δ={dna_delta:.3f})"]
            total_score += self.criteria['PP3']
            logger.info(f"✅ PP3: DNA disruptive, score += {self.criteria['PP3']}")
        elif dna_delta > 0.5:
            evidence['BP4'] = [f"DNA tolerated (Δ={dna_delta:.3f})"]
            total_score += self.criteria['BP4']
            logger.info(f"✅ BP4: DNA tolerated, score += {self.criteria['BP4']}")
        
        # ============================================
        # 5. SYNVONYMOUS VARIANTS (BP7)
        # ============================================
        
        if mutation_type_str == 'synonymous':
            evidence['BP7'] = ["Synonymous variant - no amino acid change"]
            total_score += self.criteria['BP7']
            logger.info(f"✅ BP7: Synonymous, score += {self.criteria['BP7']}")
        
        # ============================================
        # 6. DETERMINE CLASSIFICATION
        # ============================================
        
        logger.info(f"📊 Total ACMG Score: {total_score:.2f}")
        
        # Calculate posterior probability (0-1 scale)
        posterior = 1.0 / (1.0 + np.exp(-total_score * 0.5))
        posterior = min(0.99, max(0.01, posterior))
        
        # Determine classification based on total score
        if total_score >= 1.0:
            classification = ACMGClassification.PATHOGENIC
            summary = f"Pathogenic (posterior probability {posterior*100:.1f}%)"
        elif total_score >= 0.5:
            classification = ACMGClassification.LIKELY_PATHOGENIC
            summary = f"Likely Pathogenic (posterior probability {posterior*100:.1f}%)"
        elif total_score <= -1.0:
            classification = ACMGClassification.BENIGN
            summary = f"Benign (posterior probability {(1-posterior)*100:.1f}%)"
        elif total_score <= -0.5:
            classification = ACMGClassification.LIKELY_BENIGN
            summary = f"Likely Benign (posterior probability {(1-posterior)*100:.1f}%)"
        else:
            classification = ACMGClassification.VUS
            summary = f"Variant of Uncertain Significance (posterior probability {posterior*100:.1f}%)"
        
        logger.info(f"📋 Classification: {classification.value} (Score: {total_score:.2f})")
        
        return classification, posterior, evidence, summary

# Singleton
acmg_service = ACMGService()