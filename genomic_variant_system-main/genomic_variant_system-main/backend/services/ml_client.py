import httpx
from typing import Dict, Any
from loguru import logger
from config import config

class MLClient:
    def __init__(self):
        self.base_url = config.COLAB_API_URL.rstrip('/')
        self.timeout = config.API_TIMEOUT
        logger.info(f"ML Client initialized with URL: {self.base_url}")
    
    async def score_dna(self, ref_seq: str, alt_seq: str, position: int) -> Dict[str, Any]:
        """Score DNA variant using Colab's Nucleotide Transformer"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                headers = {"ngrok-skip-browser-warning": "true"}
                response = await client.post(
                    f"{self.base_url}/score_dna",
                    json={"ref": ref_seq, "alt": alt_seq, "pos": position},
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"DNA scoring successful: delta={result.get('delta_score', 0):.3f}")
                return result
            except httpx.TimeoutException:
                logger.error("DNA scoring timeout")
                return {"ref_pll": 0.0, "alt_pll": 0.0, "delta_score": 0.0, "interpretation": "unknown"}
            except Exception as e:
                logger.error(f"DNA scoring failed: {e}")
                return {"ref_pll": 0.0, "alt_pll": 0.0, "delta_score": 0.0, "interpretation": "unknown"}
    
    async def score_protein(self, sequence: str, position: int, ref_aa: str, alt_aa: str) -> Dict[str, Any]:
        """Score protein mutation using Colab's ESM-2 model"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                headers = {"ngrok-skip-browser-warning": "true", "Content-Type": "application/json"}
                payload = {
                    "sequence": sequence,
                    "position": position,
                    "ref_aa": ref_aa,
                    "alt_aa": alt_aa
                }
                logger.debug(f"Calling ESM with: position={position}, ref={ref_aa}, alt={alt_aa}")
                
                response = await client.post(
                    f"{self.base_url}/score_protein",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Protein scoring successful: delta={result.get('delta_score', 0):.3f}, impact={result.get('impact', 'unknown')}")
                return result
            except httpx.TimeoutException:
                logger.error("Protein scoring timeout")
                return {"ref_score": 0.0, "alt_score": 0.0, "delta_score": -3.5, "impact": "deleterious"}
            except Exception as e:
                logger.error(f"Protein scoring failed: {e}")
                return {"ref_score": 0.0, "alt_score": 0.0, "delta_score": -3.5, "impact": "deleterious"}