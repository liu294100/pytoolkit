"""观战启动

两种方式：
1. LCU 客户端内观战（推荐）：客户端已登录且与目标同区服，直接 POST /lol-spectator/v1/spectate/launch
2. 直接拉起游戏进程：使用 spectator-v5 返回的 encryptionKey/gameId，命令行启动 League of Legends.exe
   "League of Legends.exe" "spectator <host> <key> <gameId> <platform>" "-UseRads" "-Locale=zh_CN" "-GameBaseDir=.."
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import APP_DIR
from .lcu import detect_game_exe


@dataclass
class SpectateParams:
    platform: str
    game_id: str
    encryption_key: str
    host: str

    @classmethod
    def from_active_game(cls, game: Dict[str, Any], host_override: str = "") -> "SpectateParams":
        platform = str(game.get("platformId") or "").upper()
        host = host_override or f"spectator.{platform.lower()}.lol.pvp.net:8080"
        return cls(
            platform=platform,
            game_id=str(game.get("gameId") or ""),
            encryption_key=str((game.get("observers") or {}).get("encryptionKey") or ""),
            host=host,
        )

    @property
    def valid(self) -> bool:
        return all([self.platform, self.game_id, self.encryption_key])

    def spectator_arg(self) -> str:
        return f"spectator {self.host} {self.encryption_key} {self.game_id} {self.platform}"


def build_command(exe: Path, params: SpectateParams, locale: str = "zh_CN") -> List[str]:
    return [str(exe), params.spectator_arg(), "-UseRads", f"-Locale={locale}", "-GameBaseDir=.."]


def launch(params: SpectateParams, client_path: str = "", locale: str = "zh_CN") -> Path:
    exe = detect_game_exe(client_path)
    if not exe:
        raise FileNotFoundError("找不到 Game/League of Legends.exe，请在设置中指定客户端路径。")
    if not params.valid:
        raise ValueError("观战参数不完整（缺少 encryptionKey / gameId）")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0
    subprocess.Popen(build_command(exe, params, locale), cwd=str(exe.parent), creationflags=flags)
    return exe


def write_bat(params: SpectateParams, client_path: str = "", locale: str = "zh_CN") -> Path:
    """生成可双击运行的观战脚本（游戏进程启动失败时手动排查用）"""
    exe = detect_game_exe(client_path)
    exe_text = str(exe) if exe else r"C:\Riot Games\League of Legends\Game\League of Legends.exe"
    path = APP_DIR / f"spectate_{params.platform}_{params.game_id}.bat"
    content = (
        "@echo off\r\n"
        f'cd /d "{Path(exe_text).parent}"\r\n'
        f'start "" "League of Legends.exe" "{params.spectator_arg()}" "-UseRads" '
        f'"-Locale={locale}" "-GameBaseDir=.."\r\n'
    )
    path.write_text(content, encoding="gbk", errors="ignore")
    return path
