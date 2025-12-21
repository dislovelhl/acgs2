import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

try:
    from enhanced_agent_bus.deliberation_layer.voting_service import VotingService
    print("VotingService import SUCCESS")
except ImportError as e:
    print(f"VotingService import FAILED: {e}")

try:
    from enhanced_agent_bus.deliberation_layer.deliberation_queue import DeliberationQueue
    print("DeliberationQueue import SUCCESS")
except ImportError as e:
    print(f"DeliberationQueue import FAILED: {e}")
