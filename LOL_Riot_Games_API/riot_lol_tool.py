import json
import os
import base64
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional, Tuple

import requests


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_TIMEOUT = 20


PLATFORM_TO_REGIONAL = {
    "BR1": "americas",
    "LA1": "americas",
    "LA2": "americas",
    "NA1": "americas",
    "KR": "asia",
    "JP1": "asia",
    "EUN1": "europe",
    "EUW1": "europe",
    "ME1": "europe",
    "RU": "europe",
    "TR1": "europe",
    "OC1": "sea",
    "SG2": "sea",
    "TW2": "sea",
    "VN2": "sea",
}


DEFAULT_CONFIG = {
    "api_key": "请替换成你的 Riot API Key",
    "default_platform": "NA1",
    "match_count": 10,
    "league_client_path": "",
}


QUEUE_NAMES = {
    400: "匹配模式",
    420: "单双排",
    430: "盲选",
    440: "灵活排位",
    450: "大乱斗",
    700: "极限闪击",
    830: "人机入门",
    840: "人机进阶",
    850: "人机困难",
    900: "无限火力",
    1020: "单中模式",
    1090: "团队激斗",
    1700: "斗魂竞技场",
}


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = DEFAULT_CONFIG.copy()
        save_config(data)
    merged = DEFAULT_CONFIG.copy()
    merged.update(data)
    return merged


def save_config(config: Dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def split_riot_id(text: str) -> Tuple[str, str]:
    value = text.strip()
    if "#" not in value:
        raise ValueError("请输入完整 Riot ID，格式如：Faker#KR1")
    game_name, tag_line = value.split("#", 1)
    game_name = game_name.strip()
    tag_line = tag_line.strip()
    if not game_name or not tag_line:
        raise ValueError("Riot ID 格式不正确，请使用 `名字#标签`")
    return game_name, tag_line


def format_duration(seconds: int) -> str:
    mins, sec = divmod(max(0, int(seconds)), 60)
    hour, mins = divmod(mins, 60)
    if hour > 0:
        return f"{hour}小时{mins}分{sec}秒"
    return f"{mins}分{sec}秒"


def safe_get(mapping: Dict[str, Any], *keys: str, default: Any = "-") -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


class RiotAPIError(Exception):
    pass


class LCUError(Exception):
    pass


@dataclass
class SummonerProfile:
    puuid: str
    riot_id: str
    platform: str
    regional: str


class RiotAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.session = requests.Session()
        self.session.headers.update({"X-Riot-Token": self.api_key})

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.api_key or "请替换" in self.api_key:
            raise RiotAPIError("请先在 config.json 中填写有效的 Riot API Key。")
        try:
            response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as exc:
            raise RiotAPIError(f"请求失败：{exc}") from exc

        if response.status_code == 200:
            return response.json()
        if response.status_code == 401:
            raise RiotAPIError("API Key 无效或已过期。")
        if response.status_code == 403:
            raise RiotAPIError("API Key 没有权限访问该接口。")
        if response.status_code == 404:
            raise RiotAPIError("没有找到该召唤师或当前没有可用数据。")
        if response.status_code == 429:
            raise RiotAPIError("请求过快，触发了 Riot API 限流，请稍后再试。")
        raise RiotAPIError(f"接口报错：HTTP {response.status_code} - {response.text[:200]}")

    def get_account_by_riot_id(self, regional: str, game_name: str, tag_line: str) -> Dict[str, Any]:
        url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return self._get(url)

    def get_active_shard(self, regional: str, puuid: str) -> Dict[str, Any]:
        url = f"https://{regional}.api.riotgames.com/riot/account/v1/active-shards/by-game/lol/by-puuid/{puuid}"
        return self._get(url)

    def get_match_ids(self, regional: str, puuid: str, count: int = 10) -> List[str]:
        url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"start": 0, "count": max(1, min(100, count))}
        return self._get(url, params=params)

    def get_match_detail(self, regional: str, match_id: str) -> Dict[str, Any]:
        url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return self._get(url)

    def get_current_game(self, platform: str, puuid: str) -> Dict[str, Any]:
        url = f"https://{platform.lower()}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        return self._get(url)


class LCUClient:
    def __init__(self, league_client_path: str = ""):
        self.league_client_path = league_client_path.strip()

    def _candidate_lockfiles(self) -> List[Path]:
        candidates: List[Path] = []
        if self.league_client_path:
            client_file = Path(self.league_client_path)
            for parent in [client_file.parent, client_file.parent.parent, client_file.parent.parent.parent]:
                if parent and str(parent) not in {"", "."}:
                    candidates.append(parent / "lockfile")

        common_roots = [
            Path("C:/Riot Games/League of Legends"),
            Path("D:/Riot Games/League of Legends"),
            Path("E:/Riot Games/League of Legends"),
            Path("F:/Riot Games/League of Legends"),
            Path("G:/Riot Games/League of Legends"),
        ]
        for root in common_roots:
            candidates.append(root / "lockfile")

        unique: List[Path] = []
        seen = set()
        for item in candidates:
            key = str(item).lower()
            if key not in seen:
                unique.append(item)
                seen.add(key)
        return unique

    def _read_lockfile(self) -> Tuple[int, str]:
        for lockfile in self._candidate_lockfiles():
            if not lockfile.exists():
                continue
            try:
                content = lockfile.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            parts = content.split(":")
            if len(parts) >= 5:
                try:
                    port = int(parts[2])
                except ValueError:
                    continue
                token = parts[3]
                return port, token
        raise LCUError(
            "没有找到客户端 `lockfile`。\n\n请先打开并登录英雄联盟客户端，再重试。\n"
            "如果你不是默认安装目录，也请确保 `客户端路径` 已指向你的游戏安装位置。"
        )

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> requests.Response:
        port, token = self._read_lockfile()
        auth = base64.b64encode(f"riot:{token}".encode("utf-8")).decode("utf-8")
        headers = {"Authorization": f"Basic {auth}"}
        url = f"https://127.0.0.1:{port}{path}"
        try:
            return requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=json_body,
                timeout=DEFAULT_TIMEOUT,
                verify=False,
            )
        except requests.RequestException as exc:
            raise LCUError(f"连接本地客户端失败：{exc}") from exc

    def spectate_by_puuid(self, riot_id: str, puuid: str) -> None:
        payload = {
            "allowObserveMode": "ALL",
            "dropInSpectateGameId": riot_id,
            "gameQueueType": "",
            "puuid": puuid,
        }
        response = self._request("POST", "/lol-spectator/v1/spectate/launch", json_body=payload)
        if response.status_code in {200, 201, 202, 204}:
            return
        raise LCUError(f"客户端观战发起失败：HTTP {response.status_code} - {response.text[:300]}")


class LoLScoutApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LoL 战绩 / 观战工具")
        self.root.geometry("1180x760")

        self.config = load_config()
        self.api = RiotAPIClient(self.config["api_key"])
        self.lcu = LCUClient(self.config.get("league_client_path", ""))
        self.profile: Optional[SummonerProfile] = None
        self.match_details_by_id: Dict[str, Dict[str, Any]] = {}
        self.current_game_data: Optional[Dict[str, Any]] = None

        self.platform_var = tk.StringVar(value=self.config["default_platform"])
        self.riot_id_var = tk.StringVar()
        self.client_path_var = tk.StringVar(value=self.config.get("league_client_path", ""))
        self.status_var = tk.StringVar(value="准备就绪")

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        top.columnconfigure(4, weight=1)

        ttk.Label(top, text="Riot ID").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(top, textvariable=self.riot_id_var).grid(row=0, column=1, sticky="ew", padx=(0, 12))

        ttk.Label(top, text="默认平台").grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Combobox(
            top,
            textvariable=self.platform_var,
            values=sorted(PLATFORM_TO_REGIONAL.keys()),
            state="readonly",
            width=10,
        ).grid(row=0, column=3, sticky="w", padx=(0, 12))

        ttk.Button(top, text="搜索并加载", command=self.search_profile).grid(row=0, column=4, sticky="w", padx=(0, 8))
        ttk.Button(top, text="刷新战绩", command=self.refresh_matches).grid(row=0, column=5, sticky="w", padx=(0, 8))
        ttk.Button(top, text="当前对局", command=self.refresh_current_game).grid(row=0, column=6, sticky="w")

        client_row = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        client_row.grid(row=1, column=0, sticky="ew")
        client_row.columnconfigure(1, weight=1)

        ttk.Label(client_row, text="客户端路径").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(client_row, textvariable=self.client_path_var).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(client_row, text="选择 EXE", command=self.pick_client_exe).grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Button(client_row, text="保存配置", command=self.save_current_config).grid(row=0, column=3, sticky="w")

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.matches_tab = ttk.Frame(notebook, padding=8)
        self.match_detail_tab = ttk.Frame(notebook, padding=8)
        self.spectator_tab = ttk.Frame(notebook, padding=8)
        notebook.add(self.matches_tab, text="最近战绩")
        notebook.add(self.match_detail_tab, text="战绩详情")
        notebook.add(self.spectator_tab, text="观战")

        self._build_matches_tab()
        self._build_match_detail_tab()
        self._build_spectator_tab()

        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 4))
        status_bar.grid(row=3, column=0, sticky="ew")

    def _build_matches_tab(self) -> None:
        self.matches_tab.columnconfigure(0, weight=1)
        self.matches_tab.rowconfigure(0, weight=1)

        columns = ("match_id", "queue", "champion", "kda", "result", "duration", "date")
        self.matches_tree = ttk.Treeview(self.matches_tab, columns=columns, show="headings", height=20)
        headers = {
            "match_id": "对局 ID",
            "queue": "模式",
            "champion": "英雄",
            "kda": "KDA",
            "result": "结果",
            "duration": "时长",
            "date": "开始时间",
        }
        widths = {"match_id": 160, "queue": 120, "champion": 120, "kda": 100, "result": 80, "duration": 100, "date": 180}
        for key in columns:
            self.matches_tree.heading(key, text=headers[key])
            self.matches_tree.column(key, width=widths[key], anchor="center")
        self.matches_tree.grid(row=0, column=0, sticky="nsew")
        self.matches_tree.bind("<<TreeviewSelect>>", self.on_match_selected)

        scroll = ttk.Scrollbar(self.matches_tab, orient="vertical", command=self.matches_tree.yview)
        self.matches_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

    def _build_match_detail_tab(self) -> None:
        self.match_detail_tab.columnconfigure(0, weight=1)
        self.match_detail_tab.rowconfigure(0, weight=1)
        self.match_text = tk.Text(self.match_detail_tab, wrap="word", font=("Consolas", 11))
        self.match_text.grid(row=0, column=0, sticky="nsew")
        detail_scroll = ttk.Scrollbar(self.match_detail_tab, orient="vertical", command=self.match_text.yview)
        self.match_text.configure(yscrollcommand=detail_scroll.set)
        detail_scroll.grid(row=0, column=1, sticky="ns")

    def _build_spectator_tab(self) -> None:
        self.spectator_tab.columnconfigure(0, weight=1)
        self.spectator_tab.rowconfigure(1, weight=1)

        btn_bar = ttk.Frame(self.spectator_tab)
        btn_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(btn_bar, text="刷新当前对局", command=self.refresh_current_game).pack(side="left", padx=(0, 8))
        ttk.Button(btn_bar, text="一键观战", command=self.launch_spectator).pack(side="left")
        ttk.Button(btn_bar, text="通过客户端观战", command=self.launch_spectator_via_lcu).pack(side="left", padx=(8, 0))
        ttk.Button(btn_bar, text="复制观战参数", command=self.copy_spectate_params).pack(side="left", padx=(8, 0))

        self.spectator_text = tk.Text(self.spectator_tab, wrap="word", font=("Consolas", 11))
        self.spectator_text.grid(row=1, column=0, sticky="nsew")
        spectator_scroll = ttk.Scrollbar(self.spectator_tab, orient="vertical", command=self.spectator_text.yview)
        self.spectator_text.configure(yscrollcommand=spectator_scroll.set)
        spectator_scroll.grid(row=1, column=1, sticky="ns")

    def pick_client_exe(self) -> None:
        path = filedialog.askopenfilename(
            title="选择英雄联盟游戏可执行文件（League of Legends.exe）",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
        )
        if path:
            self.client_path_var.set(path)

    def save_current_config(self) -> None:
        self.config["default_platform"] = self.platform_var.get().strip() or "NA1"
        self.config["league_client_path"] = self.client_path_var.get().strip()
        save_config(self.config)
        self.lcu = LCUClient(self.config.get("league_client_path", ""))
        self.status_var.set("配置已保存")
        messagebox.showinfo("提示", "配置已保存到 config.json")

    def run_task(self, title: str, func) -> None:
        def runner():
            self.status_var.set(f"{title}中...")
            try:
                func()
                self.status_var.set(f"{title}完成")
            except Exception as exc:
                self.status_var.set(f"{title}失败")
                error_message = str(exc)
                self.root.after(0, lambda msg=error_message: messagebox.showerror("错误", msg))

        threading.Thread(target=runner, daemon=True).start()

    def search_profile(self) -> None:
        def task():
            game_name, tag_line = split_riot_id(self.riot_id_var.get())
            fallback_platform = self.platform_var.get().strip() or "NA1"
            fallback_regional = PLATFORM_TO_REGIONAL.get(fallback_platform, "americas")
            account = self.api.get_account_by_riot_id(fallback_regional, game_name, tag_line)
            puuid = account["puuid"]

            detected_platform = fallback_platform
            detected_regional = fallback_regional
            try:
                shard = self.api.get_active_shard(fallback_regional, puuid)
                if shard.get("activeShard"):
                    detected_platform = shard["activeShard"].upper()
                    detected_regional = PLATFORM_TO_REGIONAL.get(detected_platform, fallback_regional)
            except RiotAPIError:
                pass

            self.profile = SummonerProfile(
                puuid=puuid,
                riot_id=f"{account.get('gameName', game_name)}#{account.get('tagLine', tag_line)}",
                platform=detected_platform,
                regional=detected_regional,
            )
            self.root.after(0, self._render_profile_loaded)
            self.root.after(0, self.refresh_matches)
            self.root.after(0, self.refresh_current_game)

        self.run_task("搜索召唤师", task)

    def _render_profile_loaded(self) -> None:
        if not self.profile:
            return
        self.platform_var.set(self.profile.platform)
        self.status_var.set(f"已加载 {self.profile.riot_id}，平台 {self.profile.platform}")

    def refresh_matches(self) -> None:
        if not self.profile:
            messagebox.showwarning("提示", "请先搜索 Riot ID")
            return

        def task():
            match_ids = self.api.get_match_ids(self.profile.regional, self.profile.puuid, self.config.get("match_count", 10))
            details: List[Tuple[str, Dict[str, Any]]] = []
            for match_id in match_ids:
                details.append((match_id, self.api.get_match_detail(self.profile.regional, match_id)))
            self.match_details_by_id = {match_id: detail for match_id, detail in details}
            self.root.after(0, lambda: self._render_matches(details))

        self.run_task("刷新战绩", task)

    def _render_matches(self, details: List[Tuple[str, Dict[str, Any]]]) -> None:
        for item in self.matches_tree.get_children():
            self.matches_tree.delete(item)

        if not self.profile:
            return

        for match_id, detail in details:
            participant = self._find_my_participant(detail)
            info = detail.get("info", {})
            start_ts = info.get("gameStartTimestamp") or info.get("gameCreation") or 0
            date_text = "-"
            if start_ts:
                import datetime as _dt

                date_text = _dt.datetime.fromtimestamp(start_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")

            queue_id = info.get("queueId", 0)
            queue_name = QUEUE_NAMES.get(queue_id, str(queue_id))
            champion = participant.get("championName", "-")
            kda = f"{participant.get('kills', 0)}/{participant.get('deaths', 0)}/{participant.get('assists', 0)}"
            result = "胜利" if participant.get("win") else "失败"
            duration = format_duration(self._resolve_duration_seconds(info))

            self.matches_tree.insert(
                "",
                "end",
                iid=match_id,
                values=(match_id, queue_name, champion, kda, result, duration, date_text),
            )

        if details:
            first_match_id = details[0][0]
            self.matches_tree.selection_set(first_match_id)
            self.show_match_detail(first_match_id)

    def _resolve_duration_seconds(self, info: Dict[str, Any]) -> int:
        duration = int(info.get("gameDuration", 0) or 0)
        if info.get("gameEndTimestamp"):
            return duration
        if duration > 100000:
            return duration // 1000
        return duration

    def _find_my_participant(self, detail: Dict[str, Any]) -> Dict[str, Any]:
        participants = safe_get(detail, "info", "participants", default=[])
        if not self.profile:
            return {}
        for participant in participants:
            if participant.get("puuid") == self.profile.puuid:
                return participant
        return participants[0] if participants else {}

    def on_match_selected(self, _event=None) -> None:
        selected = self.matches_tree.selection()
        if not selected:
            return
        self.show_match_detail(selected[0])

    def show_match_detail(self, match_id: str) -> None:
        detail = self.match_details_by_id.get(match_id)
        if not detail:
            return
        info = detail.get("info", {})
        me = self._find_my_participant(detail)
        lines = [
            f"对局 ID: {match_id}",
            f"平台: {info.get('platformId', '-')}",
            f"模式: {QUEUE_NAMES.get(info.get('queueId', 0), info.get('queueId', '-'))}",
            f"地图模式: {info.get('gameMode', '-')}",
            f"时长: {format_duration(self._resolve_duration_seconds(info))}",
            "",
            "我的数据",
            f"英雄: {me.get('championName', '-')}",
            f"KDA: {me.get('kills', 0)}/{me.get('deaths', 0)}/{me.get('assists', 0)}",
            f"结果: {'胜利' if me.get('win') else '失败'}",
            f"位置: {me.get('teamPosition') or me.get('individualPosition') or '-'}",
            f"补刀: {int(me.get('totalMinionsKilled', 0)) + int(me.get('neutralMinionsKilled', 0))}",
            f"经济: {me.get('goldEarned', 0)}",
            f"造成伤害: {me.get('totalDamageDealtToChampions', 0)}",
            f"承受伤害: {me.get('totalDamageTaken', 0)}",
            f"视野得分: {me.get('visionScore', 0)}",
            "",
            "全场玩家",
        ]

        participants = info.get("participants", [])
        for participant in participants:
            riot_name = participant.get("riotIdGameName") or participant.get("summonerName") or "Unknown"
            tag = participant.get("riotIdTagline")
            if tag:
                riot_name = f"{riot_name}#{tag}"
            role = participant.get("teamPosition") or participant.get("individualPosition") or "-"
            row = (
                f"[{'W' if participant.get('win') else 'L'}] "
                f"{participant.get('championName', '-'):<15} "
                f"{participant.get('kills', 0)}/{participant.get('deaths', 0)}/{participant.get('assists', 0):<5} "
                f"{role:<8} "
                f"{riot_name}"
            )
            lines.append(row)

        self.match_text.delete("1.0", tk.END)
        self.match_text.insert("1.0", "\n".join(lines))

    def refresh_current_game(self) -> None:
        if not self.profile:
            messagebox.showwarning("提示", "请先搜索 Riot ID")
            return

        def task():
            try:
                current = self.api.get_current_game(self.profile.platform, self.profile.puuid)
            except RiotAPIError as exc:
                self.current_game_data = None
                error_message = f"当前不在游戏中，或暂时无法观战。\n\n详细信息：{exc}"
                self.root.after(0, lambda msg=error_message: self._render_spectator_text(msg))
                return
            self.current_game_data = current
            self.root.after(0, self._render_current_game)

        self.run_task("获取当前对局", task)

    def _render_current_game(self) -> None:
        data = self.current_game_data
        if not data:
            self._render_spectator_text("当前没有可观战的进行中对局。")
            return

        queue_text = QUEUE_NAMES.get(data.get("gameQueueConfigId", 0), str(data.get("gameQueueConfigId", "-")))
        params = self.get_spectate_params()
        lines = [
            f"当前玩家: {self.profile.riot_id if self.profile else '-'}",
            f"平台: {data.get('platformId', '-')}",
            f"Game ID: {data.get('gameId', '-')}",
            f"模式: {queue_text}",
            f"地图模式: {data.get('gameMode', '-')}",
            f"已进行时长: {format_duration(int(data.get('gameLength', 0) or 0))}",
            "",
            "说明",
            "1. 点击“一键观战”会尝试直接拉起你本地的英雄联盟客户端。",
            "2. 点击“通过客户端观战”会调用已登录的 LoL 客户端本地接口（LCU），通常比命令行方式更稳。",
            "3. 你需要已经安装对应区服客户端，并且 `客户端路径` 指向正确的可执行文件。",
            "4. 若客户端/区服不匹配，观战可能启动失败。",
            "",
            "观战参数（可复制）",
            f"platformId = {params.get('platformId', '-')}",
            f"gameId = {params.get('gameId', '-')}",
            f"encryptionKey = {params.get('encryptionKey', '-')}",
            f"server = {params.get('server', '-')}",
            "",
            "手动启动命令（Windows CMD）",
            params.get("manual_command", "-"),
        ]
        self._render_spectator_text("\n".join(lines))

    def _render_spectator_text(self, text: str) -> None:
        self.spectator_text.delete("1.0", tk.END)
        self.spectator_text.insert("1.0", text)

    def get_spectate_params(self) -> Dict[str, str]:
        """
        返回一组“观战参数”，便于复制/分享/手动启动。
        依赖 spectator-v5 返回的 gameId/platformId/encryptionKey。
        """
        data = self.current_game_data or {}
        platform_id = str(data.get("platformId") or "")
        game_id = str(data.get("gameId") or "")
        encryption_key = str(safe_get(data, "observers", "encryptionKey", default="") or "")
        server = f"spectator.{platform_id.lower()}.lol.riotgames.com:80" if platform_id else ""
        client_path = self.client_path_var.get().strip()

        manual_command = ""
        if client_path and server and encryption_key and game_id and platform_id:
            # 用双引号包裹路径，便于直接粘贴到 CMD
            manual_command = f"\"{client_path}\" spectator {server} {encryption_key} {game_id} {platform_id}"

        return {
            "platformId": platform_id,
            "gameId": game_id,
            "encryptionKey": encryption_key,
            "server": server,
            "manual_command": manual_command,
        }

    def copy_spectate_params(self) -> None:
        if not self.current_game_data:
            messagebox.showwarning("提示", "请先获取当前对局。")
            return
        params = self.get_spectate_params()
        if not params.get("platformId") or not params.get("gameId") or not params.get("encryptionKey"):
            messagebox.showerror("错误", "当前对局缺少必要观战参数。")
            return

        # 复制为“单行可粘贴”格式，最接近 OPGG 的分享方式
        # spectator <server> <encryptionKey> <gameId> <platformId>
        one_line = f"spectator {params['server']} {params['encryptionKey']} {params['gameId']} {params['platformId']}"
        self.root.clipboard_clear()
        self.root.clipboard_append(one_line)
        self.root.update()  # 确保剪贴板写入
        messagebox.showinfo("已复制", "观战参数已复制到剪贴板。")

    def launch_spectator_via_lcu(self) -> None:
        if not self.profile:
            messagebox.showwarning("提示", "请先搜索并加载玩家。")
            return

        def task():
            self.lcu = LCUClient(self.client_path_var.get().strip())
            self.lcu.spectate_by_puuid(self.profile.riot_id, self.profile.puuid)
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "已发送",
                    "已经向已登录的 LoL 客户端发送观战请求。\n如果客户端已打开并登录，应该会由客户端接管观战。",
                ),
            )

        self.run_task("通过客户端发起观战", task)

    def launch_spectator(self) -> None:
        if not self.current_game_data:
            messagebox.showwarning("提示", "请先获取当前对局。")
            return

        client_path = self.client_path_var.get().strip()
        if not client_path:
            messagebox.showwarning("提示", "请先选择英雄联盟游戏可执行文件（League of Legends.exe）。")
            return
        client_file = Path(client_path)
        if not client_file.exists():
            messagebox.showerror("错误", "客户端路径不存在，请重新选择。")
            return
        if client_file.is_dir():
            messagebox.showerror("错误", "你当前选择的是文件夹，不是可执行文件，请选择 `League of Legends.exe`。")
            return

        file_name = client_file.name.lower()
        if file_name in {"leagueclient.exe", "riotclientservices.exe", "riot client.exe"}:
            messagebox.showerror(
                "错误",
                "你选择的是启动器，不是游戏进程。\n\n请改选游戏目录里的 `League of Legends.exe`，通常在 `...\\League of Legends\\Game\\League of Legends.exe`。",
            )
            return
        if file_name != "league of legends.exe":
            confirm = messagebox.askyesno(
                "确认路径",
                f"当前选择的文件是：{client_file.name}\n\n观战通常需要 `League of Legends.exe`。\n仍然继续尝试启动吗？",
            )
            if not confirm:
                return

        data = self.current_game_data
        platform_id = data.get("platformId")
        game_id = data.get("gameId")
        encryption_key = safe_get(data, "observers", "encryptionKey")
        if not platform_id or not game_id or not encryption_key:
            messagebox.showerror("错误", "当前对局缺少必要观战参数。")
            return

        server = f"spectator.{str(platform_id).lower()}.lol.riotgames.com:80"
        args = ["spectator", server, str(encryption_key), str(game_id), str(platform_id)]

        launch_errors: List[str] = []
        launched = False

        try:
            subprocess.Popen([client_path, *args], cwd=str(client_file.parent))
            launched = True
        except OSError as exc:
            launch_errors.append(f"直接启动失败：{exc}")

        if not launched and os.name == "nt":
            cmd_line = subprocess.list2cmdline([client_path, *args])
            try:
                subprocess.Popen(
                    f'cmd /c start "" {cmd_line}',
                    cwd=str(client_file.parent),
                    shell=True,
                )
                launched = True
            except OSError as exc:
                launch_errors.append(f"cmd/start 启动失败：{exc}")

        if not launched and os.name == "nt" and hasattr(os, "startfile"):
            try:
                os.startfile(client_path, arguments=subprocess.list2cmdline(args), cwd=str(client_file.parent))
                launched = True
            except OSError as exc:
                launch_errors.append(f"os.startfile 启动失败：{exc}")

        if not launched:
            details = "\n".join(launch_errors) if launch_errors else "未知错误"
            manual_command = f'"{client_path}" spectator {server} {encryption_key} {game_id} {platform_id}'
            messagebox.showerror(
                "错误",
                "拉起客户端失败。\n\n"
                f"{details}\n\n"
                "你可以先确认：\n"
                "1. 当前选择的是 `League of Legends.exe`\n"
                "2. 右键该 EXE -> 属性 -> 兼容性，确认没有勾选“以管理员身份运行此程序”\n"
                "3. Riot Client 和该游戏 EXE 的权限级别一致\n"
                "4. 当前区服客户端就是 KR 客户端\n\n"
                "也可以手动在 CMD 里执行下面命令测试：\n"
                f"{manual_command}",
            )
            return

        self.config["league_client_path"] = client_path
        save_config(self.config)
        messagebox.showinfo(
            "已尝试启动",
            "已尝试拉起客户端进行观战。\n如果没有成功，通常是客户端路径不对、区服不匹配，或本机没有对应区服客户端。",
        )


def main() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise SystemExit(f"无法启动图形界面：{exc}")
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    app = LoLScoutApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
