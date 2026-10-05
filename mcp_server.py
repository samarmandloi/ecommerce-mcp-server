import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from ecommerce_mcp.server import mcp
