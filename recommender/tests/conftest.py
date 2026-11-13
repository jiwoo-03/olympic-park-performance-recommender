"""recommend.py 등이 `import series`처럼 패키지 경로 없이 임포트하므로, 테스트에서도
recommender/ 디렉터리를 sys.path에 넣어줘야 한다(실제 앱도 같은 방식으로 경로를
추가한다 — backend/performances_store.py 참고)."""
import sys
from pathlib import Path

RECOMMENDER_DIR = Path(__file__).resolve().parent.parent
if str(RECOMMENDER_DIR) not in sys.path:
    sys.path.insert(0, str(RECOMMENDER_DIR))
