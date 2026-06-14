# hari/engine/__init__.py
import os
from typing import Dict, Any

# Global Feature Flags loaded from environment configs
USE_MEMORY = os.getenv("USE_MEMORY", "False").lower() == "true"
USE_WORKSPACE = os.getenv("USE_WORKSPACE", "False").lower() == "true"
USE_MONOLOGUE = os.getenv("USE_MONOLOGUE", "False").lower() == "true"
USE_CURIOSITY_GRAPH = False

from .generate import generate_lightweight_response

# Stubs for future phases
from .attention import compute_salience, load_workspace
from .memory import embed, store_memory, retrieve_similar
from .prediction import generate_prediction, compute_prediction_error
from .memory_consolidation import promote_workspace_item, decay_curiosity_graph

async def generate_hari_response(
    user_input: str,
    state,
    grace_tracker,
    turn_count: int,
    session_id: str = "test",
    use_memory: bool = None,
    use_workspace: bool = None,
    use_monologue: bool = None
) -> Dict[str, Any]:
    
# If explicit boolean overrides aren't provided by the caller, fallback to global .env defaults
    if use_memory is None:
        use_memory = USE_MEMORY
    if use_workspace is None:
        use_workspace = USE_WORKSPACE
    if use_monologue is None:
        use_monologue = USE_MONOLOGUE
        
    # Relaying variables straight into our updated generate.py engine layer
    return await generate_lightweight_response(
        user_input=user_input, 
        state=state, 
        grace_tracker=grace_tracker, 
        turn_count=turn_count, 
        session_id=session_id, 
        use_memory=use_memory, 
        use_workspace=use_workspace,
        use_monologue=use_monologue
    )