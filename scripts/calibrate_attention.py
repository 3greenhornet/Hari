"""
scripts/calibrate_attention.py — Run attention calibration experiments.

This script:
1. Runs the Canonical Conversation Suite with instrumentation enabled
2. Logs all pressure contributions
3. Produces a calibration report
"""

import asyncio
import json
import os
from datetime import datetime

from engine.generate import TurnPipeline
from psyche.state import HariState
from psyche.grace import GraceTracker
from engine.attention_config import AttentionCalibration, DEFAULT_ATTENTION_CONFIG
from engine.attention_instrumentation import AttentionInstrumentation

# Import the canonical conversation suite from the observatory
from scripts.run_observatory import CANONICAL_CONVERSATIONS


async def calibrate_attention(
    config: AttentionCalibration = DEFAULT_ATTENTION_CONFIG,
    label: str = "default"
):
    """Run a calibration session with the given config."""
    session_id = f"calibration_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    state = HariState()
    grace = GraceTracker()
    pipeline = TurnPipeline(session_id, state, grace)
    
    # Override with custom config if provided
    pipeline.attention_config = config
    pipeline.attention_instrumentation = AttentionInstrumentation(config)
    
    turn_count = 0
    print(f"\n=== Calibration Session: {label} ===")
    print(f"Config: {config}")
    print(f"Experiment ID: {pipeline.attention_instrumentation.config.experiment_id}")
    
    for conv_idx, conversation in enumerate(CANONICAL_CONVERSATIONS):
        print(f"\n--- Conversation {conv_idx + 1} ---")
        for user_input in conversation:
            turn_count += 1
            result = await pipeline.execute(user_input, turn_count)
            print(f"User: {user_input}")
            print(f"Hari: {result['dialogue'][:150]}...")
    
    # End session
    pipeline.shutdown()
    
    # Generate report
    summary = pipeline.attention_instrumentation.get_summary()
    print("\n=== Calibration Report ===")
    print(json.dumps(summary, indent=2))
    
    # Save report
    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/attention_calibration_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nReport saved to {report_path}")
    
    return summary


async def main():
    # Run with default config first
    await calibrate_attention(label="baseline")
    
    # You can create custom configs and run them later
    # custom_config = AttentionCalibration(
    #     relevance_base=0.7,
    #     curiosity_modulation=0.8,
    #     log_pressure_contributions=True,
    #     experiment_id="custom_v1"
    # )
    # await calibrate_attention(config=custom_config, label="custom_v1")


if __name__ == "__main__":
    asyncio.run(main())