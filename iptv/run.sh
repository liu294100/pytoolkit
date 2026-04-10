#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

CANDIDATES=""

add_candidate() {
  p="$1"
  [ -n "$p" ] || return 0
  if [ -z "$CANDIDATES" ]; then
    CANDIDATES="$p"
    return 0
  fi
  old_ifs=$IFS
  IFS='
'
  for e in $CANDIDATES; do
    if [ "$e" = "$p" ]; then
      IFS=$old_ifs
      return 0
    fi
  done
  IFS=$old_ifs
  CANDIDATES="$CANDIDATES
$p"
}

if command -v py >/dev/null 2>&1; then
  while IFS= read -r token; do
    ver="$(printf '%s' "$token" | sed 's/^-V://')"
    p="$(py "-$ver" -c 'import sys; print(sys.executable)' 2>/dev/null || true)"
    if [ -n "$p" ] && [ -x "$p" ]; then
      add_candidate "$p"
    fi
  done <<EOF
$(py -0 2>/dev/null | awk '{print $1}' || true)
EOF
fi

for cmd in python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    add_candidate "$(command -v "$cmd")"
  fi
done

if command -v which >/dev/null 2>&1; then
  for cmd in python3 python; do
    while IFS= read -r p; do
      if [ -n "$p" ] && [ -x "$p" ]; then
        add_candidate "$p"
      fi
    done <<EOF
$(which -a "$cmd" 2>/dev/null || true)
EOF
  done
fi

if [ -z "$CANDIDATES" ]; then
  echo "未找到可用的 Python 解释器"
  exit 1
fi

echo "检测到以下 Python:"
idx=1
old_ifs=$IFS
IFS='
'
for p in $CANDIDATES; do
  echo "[$idx] $p"
  idx=$((idx + 1))
done
IFS=$old_ifs

printf "请输入序号并回车: "
read -r choice

case "$choice" in
  ''|*[!0-9]*|0)
    echo "输入无效"
    exit 1
    ;;
esac

count=$(printf '%s\n' "$CANDIDATES" | sed '/^$/d' | wc -l | tr -d ' ')
if [ "$choice" -gt "$count" ]; then
  echo "输入超出范围"
  exit 1
fi

python_exe="$(printf '%s\n' "$CANDIDATES" | sed -n "${choice}p")"
echo "使用: $python_exe"
exec "$python_exe" app.py
