# hari/engine/__init__.py
"""
Engine package for Hari cognitive architecture.
External code should import TurnPipeline from .generate directly.
"""

from .generate import TurnPipeline, generate_lightweight_response

__all__ = ["TurnPipeline", "generate_lightweight_response"]