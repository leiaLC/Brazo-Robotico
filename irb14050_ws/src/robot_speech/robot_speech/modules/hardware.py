"""
Deteccion automatica de hardware disponible.
Configura Whisper y llama.cpp segun GPU/CPU.
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def detect_cuda() -> bool:
    """Retorna True si hay GPU NVIDIA con CUDA disponible."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        pass
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi"], capture_output=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


def get_hardware_config(cfg: dict) -> dict:
    """
    Recibe la config base y devuelve una config ajustada
    automaticamente segun el hardware disponible.
    """
    cuda = detect_cuda()

    if cuda:
        logger.info("GPU NVIDIA detectada — usando CUDA")
        whisper_device = "cuda"
        whisper_compute = "float16"
        llama_n_gpu_layers = -1  # todas las capas en GPU
    else:
        logger.info("No hay GPU — usando CPU")
        whisper_device = "cpu"
        whisper_compute = "int8"
        llama_n_gpu_layers = 0  # todo en CPU

    # Whisper
    whisper_cfg = dict(cfg.get("whisper", {}))
    whisper_cfg["device"] = whisper_device
    whisper_cfg["compute_type"] = whisper_compute

    # llama.cpp
    llama_cfg = dict(cfg.get("llama_cpp", {}))
    llama_cfg["n_gpu_layers"] = llama_n_gpu_layers

    return {
        **cfg,
        "whisper": whisper_cfg,
        "llama_cpp": llama_cfg,
        "hardware": {
            "cuda": cuda,
            "device": "cuda" if cuda else "cpu",
        }
    }