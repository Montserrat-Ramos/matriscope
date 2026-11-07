"""Parámetros locales; las selecciones son candidatas, no conclusiones medidas."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv('MATRISCOPE_DATA_DIR', str(Path(__file__).resolve().parents[1] / 'data')))
    ollama_url: str = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
    llm_simple: str = os.getenv('MATRISCOPE_LLM_SIMPLE', 'qwen2.5:3b')
    llm_complex: str = os.getenv('MATRISCOPE_LLM_COMPLEX', 'llama3.2:3b')
    embedding_model: str = os.getenv('MATRISCOPE_EMBEDDING', 'nomic-embed-text')
    embedding_candidate: str = os.getenv('MATRISCOPE_EMBEDDING_CANDIDATE', 'bge-m3')
    top_k: int = max(1, min(int(os.getenv('MATRISCOPE_TOP_K', '5')), 12))
    # Estos umbrales son provisionales y deben calibrarse con casos etiquetados.
    min_similarity: float = float(os.getenv('MATRISCOPE_MIN_SIMILARITY', '0.25'))
    cache_similarity: float = float(os.getenv('MATRISCOPE_CACHE_SIMILARITY', '0.93'))
    cache_ttl_seconds: int = int(os.getenv('MATRISCOPE_CACHE_TTL_SECONDS', '3600'))
    agent_max_iterations: int = max(1, min(int(os.getenv('MATRISCOPE_MAX_ITERATIONS', '2')), 3))
    model_timeout_seconds: int = int(os.getenv('MATRISCOPE_MODEL_TIMEOUT', '90'))

