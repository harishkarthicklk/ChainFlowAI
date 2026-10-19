
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coordinator.coordinator_agent import request_human_decision

if __name__ == "__main__":
    decision = request_human_decision("SHIP-KEYBOARD-TEST")
    print(f"You entered: {decision}")
