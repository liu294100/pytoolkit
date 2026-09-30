"""模糊匹配：优先使用 rapidfuzz（C 实现，快），不可用时回退到纯 Python 实现

打分规则（0-100）：完全相等 > 前缀 > 子串 > 子序列(首字母/跳字) > 编辑距离相似度
另外对收藏、搜索次数、对局中出现次数做少量加权。
"""

from __future__ import annotations

import difflib
import unicodedata
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, TypeVar

try:
    from rapidfuzz import fuzz as _rf_fuzz  # type: ignore
except ImportError:  # pragma: no cover
    _rf_fuzz = None

T = TypeVar("T")


@lru_cache(maxsize=8192)
def normalize(text: str) -> str:
    """全角转半角、小写、去空白"""
    text = unicodedata.normalize("NFKC", text or "").lower()
    return "".join(ch for ch in text if not ch.isspace())


def _is_subsequence(needle: str, hay: str) -> Tuple[bool, int]:
    """返回 (是否子序列, 跨度)。跨度越小说明字符越集中"""
    pos, start = -1, -1
    for ch in needle:
        pos = hay.find(ch, pos + 1)
        if pos < 0:
            return False, 0
        if start < 0:
            start = pos
    return True, pos - start + 1


def _similarity(a: str, b: str) -> float:
    if _rf_fuzz is not None:
        return float(_rf_fuzz.ratio(a, b))
    return difflib.SequenceMatcher(None, a, b).ratio() * 100


def score(query: str, target: str) -> float:
    q, t = normalize(query), normalize(target)
    if not q or not t:
        return 0.0
    if q == t:
        return 100.0
    if t.startswith(q):
        return 90.0 + 10.0 * len(q) / len(t)
    idx = t.find(q)
    if idx >= 0:
        return 78.0 + 10.0 * len(q) / len(t) - min(idx, 8)
    ok, span = _is_subsequence(q, t)
    if ok:
        return 55.0 + 20.0 * len(q) / max(span, 1)
    if _rf_fuzz is not None and len(q) >= 3:
        # partial_ratio 适合“输错一两个字”
        return float(_rf_fuzz.partial_ratio(q, t)) * 0.7
    return _similarity(q, t) * 0.65


def best_score(query: str, candidates: Sequence[str]) -> float:
    return max((score(query, c) for c in candidates if c), default=0.0)


def fuzzy_filter(query: str, items: Iterable[T], keys: Callable[[T], Sequence[str]],
                 limit: int = 10, threshold: float = 45.0,
                 boost: Optional[Callable[[T], float]] = None) -> List[Tuple[float, T]]:
    results: List[Tuple[float, T]] = []
    for item in items:
        s = best_score(query, keys(item))
        if s < threshold:
            continue
        if boost:
            s += boost(item)
        results.append((s, item))
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:limit]


def player_keys(p: Dict[str, Any]) -> Sequence[str]:
    rid = p.get("riot_id", "")
    name = rid.split("#", 1)[0]
    return (rid, name)


def player_boost(p: Dict[str, Any]) -> float:
    return (6 if p.get("favorite") else 0) + min(int(p.get("hits") or 0), 10) * 0.5 + \
        min(int(p.get("seen") or 0), 20) * 0.1
