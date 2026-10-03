import httpx
from typing import Optional, Dict
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

class EnsemblService:
    def __init__(self):
        self.base_url = "https://rest.ensembl.org"
        # Cache for sequences
        self.cds_cache = {}
        self.transcript_cache = {}
    
    async def get_transcript_for_gene(self, gene: str) -> Optional[str]:
        """Get canonical transcript ID for a gene"""
        if gene in self.transcript_cache:
            return self.transcript_cache[gene]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Content-Type": "application/json"}
                
                # Get gene information
                url = f"{self.base_url}/lookup/symbol/homo_sapiens/{gene}"
                logger.info(f"Fetching gene info: {url}")
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'id' in data:
                        gene_id = data['id']
                        
                        # Get transcripts
                        transcript_url = f"{self.base_url}/lookup/id/{gene_id}?expand=1"
                        response = await client.get(transcript_url, headers=headers)
                        
                        if response.status_code == 200:
                            transcript_data = response.json()
                            
                            # Find canonical transcript
                            for transcript in transcript_data.get('Transcript', []):
                                if transcript.get('is_canonical'):
                                    transcript_id = transcript['id']
                                    self.transcript_cache[gene] = transcript_id
                                    logger.info(f"✅ Found canonical transcript for {gene}: {transcript_id}")
                                    return transcript_id
                            
                            # If no canonical, take first
                            if transcript_data.get('Transcript'):
                                transcript_id = transcript_data['Transcript'][0]['id']
                                self.transcript_cache[gene] = transcript_id
                                logger.info(f"✅ Using first transcript for {gene}: {transcript_id}")
                                return transcript_id
                
                logger.error(f"Could not find transcript for {gene}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get transcript: {e}")
            return None
    
    async def get_cds_sequence(self, gene: str) -> Optional[Dict]:
        """Fetch CDS sequence for a gene's canonical transcript"""
        
        # Check cache
        if gene in self.cds_cache:
            logger.info(f"Using cached CDS for {gene}")
            return self.cds_cache[gene]
        
        # Get transcript ID
        transcript_id = await self.get_transcript_for_gene(gene)
        if not transcript_id:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Content-Type": "application/json"}
                
                # Fetch CDS sequence
                url = f"{self.base_url}/sequence/id/{transcript_id}?type=cds"
                logger.info(f"Fetching CDS from: {url}")
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    cds_seq = data.get('seq', '')
                    
                    if cds_seq:
                        # Fetch protein sequence too
                        protein_url = f"{self.base_url}/sequence/id/{transcript_id}?type=protein"
                        protein_response = await client.get(protein_url, headers=headers)
                        protein_seq = ""
                        
                        if protein_response.status_code == 200:
                            protein_data = protein_response.json()
                            protein_seq = protein_data.get('seq', '')
                        
                        result = {
                            'cds': cds_seq,
                            'protein': protein_seq,
                            'transcript_id': transcript_id,
                            'gene': gene
                        }
                        
                        self.cds_cache[gene] = result
                        logger.info(f"✅ Fetched CDS for {gene}: {len(cds_seq)} bp, Protein: {len(protein_seq)} aa")
                        return result
                    else:
                        logger.error(f"Empty CDS sequence for {gene}")
                        return None
                else:
                    logger.error(f"Failed to fetch CDS: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to fetch CDS: {e}")
            return None
    
    def translate_cds(self, cds_seq: str) -> str:
        """Translate CDS to protein (fallback if protein endpoint fails)"""
        codon_table = {
            'ATA': 'I', 'ATC': 'I', 'ATT': 'I', 'ATG': 'M',
            'ACA': 'T', 'ACC': 'T', 'ACG': 'T', 'ACT': 'T',
            'AAC': 'N', 'AAT': 'N', 'AAA': 'K', 'AAG': 'K',
            'AGC': 'S', 'AGT': 'S', 'AGA': 'R', 'AGG': 'R',
            'CTA': 'L', 'CTC': 'L', 'CTG': 'L', 'CTT': 'L',
            'CCA': 'P', 'CCC': 'P', 'CCG': 'P', 'CCT': 'P',
            'CAC': 'H', 'CAT': 'H', 'CAA': 'Q', 'CAG': 'Q',
            'CGA': 'R', 'CGC': 'R', 'CGG': 'R', 'CGT': 'R',
            'GTA': 'V', 'GTC': 'V', 'GTG': 'V', 'GTT': 'V',
            'GCA': 'A', 'GCC': 'A', 'GCG': 'A', 'GCT': 'A',
            'GAC': 'D', 'GAT': 'D', 'GAA': 'E', 'GAG': 'E',
            'GGA': 'G', 'GGC': 'G', 'GGG': 'G', 'GGT': 'G',
            'TCA': 'S', 'TCC': 'S', 'TCG': 'S', 'TCT': 'S',
            'TTC': 'F', 'TTT': 'F', 'TTA': 'L', 'TTG': 'L',
            'TAC': 'Y', 'TAT': 'Y', 'TAA': '*', 'TAG': '*',
            'TGC': 'C', 'TGT': 'C', 'TGA': '*', 'TGG': 'W',
        }
        protein = []
        for i in range(0, len(cds_seq) - 2, 3):
            codon = cds_seq[i:i+3]
            if len(codon) == 3:
                aa = codon_table.get(codon, 'X')
                if aa == '*':
                    break
                protein.append(aa)
        return ''.join(protein)