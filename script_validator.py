"""向后兼容脚本 — 委托到 domain.schema_validator。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    from domain.schema_validator import main
    sys.exit(main())
