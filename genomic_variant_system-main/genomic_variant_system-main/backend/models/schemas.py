from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from enum import Enum
from config import config

class GenomeBuild(str, Enum):
    HG38 = "GRCh38"
    HG19 = "GRCh37"

class MutationType(str, Enum):
    SYNONYMOUS = "synonymous"
    MISSENSE = "missense"
    NONSENSE = "nonsense"
    FRAMESHIFT = "frameshift"

class ACMGClassification(str, Enum):
    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely Pathogenic"
    VUS = "Variant of Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"

class VariantInput(BaseModel):
    chromosome: str
    position: int
    reference_allele: str
    alternate_allele: str
    gene: str
    genome_build: GenomeBuild = GenomeBuild.HG38
    
    @validator('chromosome')
    def format_chromosome(cls, v):
        v = v.replace('chr', '').upper()
        return v
    
    @validator('reference_allele', 'alternate_allele')
    def validate_allele(cls, v):
        v = v.upper()
        if v and not all(c in 'ACGT' for c in v):
            raise ValueError(f'Invalid allele: {v}')
        return v
    
    @validator('gene')
    def normalize_gene(cls, v):
        v = v.upper()
        return config.GENE_ALIASES.get(v, v)

class TranscriptInfo(BaseModel):
    transcript_id: str
    gene_symbol: str
    cds_sequence: str
    protein_sequence: str
    variant_in_cds: bool
    cds_position: Optional[int] = None
    aa_position: Optional[int] = None

class DNAScore(BaseModel):
    ref_pll: float
    alt_pll: float
    delta_score: float
    interpretation: str

class ProteinScore(BaseModel):
    ref_score: float
    alt_score: float
    delta_score: float
    impact: str

class ProteinAnalysis(BaseModel):
    mutation_type: MutationType
    ref_aa: str
    alt_aa: str
    aa_position: int
    protein_score: ProteinScore
    ref_fragment: str
    alt_fragment: str

class UniProtInfo(BaseModel):
    protein_name: str
    function: str
    tissue_expression: List[str]

class ClinVarInfo(BaseModel):
    significance: str
    conditions: List[str]
    review_status: str
    found: Optional[bool] = False

class ACMGResult(BaseModel):
    classification: ACMGClassification
    score: float
    evidence: Dict[str, List[str]]
    summary: str

class AnalysisOutput(BaseModel):
    variant: Dict[str, Any]
    transcript: TranscriptInfo
    dna_score: DNAScore
    protein_analysis: ProteinAnalysis
    uniprot: UniProtInfo
    clinvar: Optional[ClinVarInfo] = None
    acmg: ACMGResult