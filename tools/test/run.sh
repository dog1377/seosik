#!/usr/bin/env bash
# 전체 점검 한 번에: 문법 검사 → 돈 계산 검산 → 화면 점검.
#   tools/test/run.sh          (휴대폰 · 태블릿 · PC, 밝은/어두운 화면 전부)
#   DW_QUICK=1 tools/test/run.sh   (휴대폰 · PC 밝은 화면만, 빠르게)
# 빌드한 뒤(python3 build.py) 돌린다. 저장소 폴더를 잠깐 로컬 웹서버로 띄움(인터넷 · 실제 서버 안 씀).
set -euo pipefail
cd "$(dirname "$0")/../.."
PORT="${DW_PORT:-$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')}"
python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
for _ in $(seq 1 50); do curl -s -o /dev/null "http://127.0.0.1:$PORT/forms/" && break; sleep 0.1; done
export DW_BASE="http://127.0.0.1:$PORT/"
echo "== 1/3 문법 검사";      python3 tools/test/syntax.py
echo "== 2/3 돈 계산 검산";   python3 tools/test/money.py
echo "== 3/3 화면 점검";      python3 tools/test/smoke.py
echo "== 모두 통과"
