"""LoL Scout v3 启动入口

python riot_lol_tool_v3.py
"""

import sys

try:
    import customtkinter  # noqa: F401
except ImportError:
    print("缺少依赖，请先执行：pip install -r requirements.txt")
    sys.exit(1)

from lol_scout.app import main

if __name__ == "__main__":
    main()
