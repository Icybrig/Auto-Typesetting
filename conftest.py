"""Root conftest.py — ensures the project root is on sys.path so tests can
import from the ``src`` package without requiring an editable install."""

import sys
from pathlib import Path

# Insert project root so `import src.xxx` resolves correctly when pytest is
# invoked from any working directory.
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
