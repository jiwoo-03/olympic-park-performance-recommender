import sys
from pathlib import Path

PREPROCESSING_DIR = Path(__file__).resolve().parent.parent
if str(PREPROCESSING_DIR) not in sys.path:
    sys.path.insert(0, str(PREPROCESSING_DIR))
