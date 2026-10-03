import httpx
from typing import Optional
from loguru import logger
from models.schemas import UniProtInfo

class UniProtService:
    async def get_protein_info(self, gene: str) -> UniProtInfo:
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = "https://rest.uniprot.org/uniprotkb/search"
                params = {
                    "query": f"gene:{gene} AND organism_id:9606",
                    "format": "json",
                    "fields": "protein_name,function,cc_tissue_specificity",
                    "size": 1
                }
                
                response = await client.get(url, params=params)
                data = response.json()
                
                if data.get('results'):
                    result = data['results'][0]
                    
                    protein_desc = result.get('proteinDescription', {})
                    protein_name = protein_desc.get('recommendedName', {}).get('fullName', {}).get('value', gene)
                    
                    function = "Function not available"
                    for comment in result.get('comments', []):
                        if comment.get('type') == 'function':
                            function = comment.get('text', [{}])[0].get('value', 'Function not available')
                            break
                    
                    tissues = []
                    for comment in result.get('comments', []):
                        if comment.get('type') == 'tissue specificity':
                            tissue_text = comment.get('text', [{}])[0].get('value', '')
                            if tissue_text:
                                tissues.append(tissue_text[:200])
                            break
                    
                    return UniProtInfo(
                        protein_name=protein_name,
                        function=function[:500],
                        tissue_expression=tissues if tissues else ["Various tissues"]
                    )
                
                return self._get_fallback_info(gene)
                
        except Exception as e:
            logger.error(f"UniProt error: {e}")
            return self._get_fallback_info(gene)
    
    def _get_fallback_info(self, gene: str) -> UniProtInfo:
        gene_info = {
            'BRCA1': {
                'name': 'Breast cancer type 1 susceptibility protein',
                'function': 'Involved in DNA repair and cell cycle control',
                'tissues': ['Breast', 'Ovary']
            },
            'TP53': {
                'name': 'Cellular tumor antigen p53',
                'function': 'Tumor suppressor protein',
                'tissues': ['Ubiquitous']
            }
        }
        
        info = gene_info.get(gene, {
            'name': f'{gene} protein',
            'function': f'Protein encoded by {gene}',
            'tissues': ['Various tissues']
        })
        
        return UniProtInfo(
            protein_name=info['name'],
            function=info['function'],
            tissue_expression=info['tissues']
        )