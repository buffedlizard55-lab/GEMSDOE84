import sys
from pathlib import Path
_root = Path(__file__).resolve().parent
sys.path[:0] = [str(_root / "vendor"), str(_root / "src")]
