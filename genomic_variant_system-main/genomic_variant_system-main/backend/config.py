import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    PROJECT_ROOT = Path(__file__).parent
    
    COLAB_API_URL = os.getenv("COLAB_API_URL", "http://localhost:8000")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    ENSEMBL_API = "https://rest.ensembl.org"
    UNIPROT_API = "https://rest.uniprot.org"
    NCBI_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    GENE_ALIASES = {
        'BRCA1': 'BRCA1',
        'BRCA2': 'BRCA2', 
        'TP53': 'TP53',
        'P53': 'TP53',
        'CFTR': 'CFTR',
        'HBB': 'HBB'
    }

config = Config()