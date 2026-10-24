#!/usr/bin/env bash
# 한 번에 배포: 받기 → 빌드(버전 자동) → 점검 → 커밋 → push → 배포 끝날 때까지 기다리기 → 새 버전 확인.
#
#   tools/deploy.sh "바뀐 점 한 줄"
#   tools/deploy.sh "$(printf '바뀐 점\n\n자세한 설명\n\nCo-Authored-By: …')"   (커밋 끝 줄까지 직접)
#
# 환경값(선택):
#   DW_VERSION=2026.10.24-3   버전 직접 정하기 (없으면 오늘 날짜-순번 자동)
#   DW_QUICK=1                화면 점검을 휴대폰 · PC 밝은 화면만 (빠르게)
#   DW_SKIP_TEST=1            화면 · 돈 점검 건너뛰기 (문법 검사는 함) — 글자만 고쳤을 때만
#   DW_TRAILER='…'            커밋 메시지 끝에 붙일 줄 (예: Co-Authored-By / Claude-Session)
#
# 원본은 src/ 안만 고친다. index.html · forms/*.html · sw.js · version.json 은 빌드가 만든다.
set -euo pipefail
cd "$(dirname "$0")/.."
MSG="${1:-}"
if [ -z "$MSG" ]; then echo '사용법: tools/deploy.sh "바뀐 점"'; exit 2; fi
[ -n "${DW_TRAILER:-}" ] && MSG="$MSG"$'\n\n'"$DW_TRAILER"
BR="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BR" != main ]; then echo "main 브랜치에서만 배포해요 (지금: $BR)"; exit 2; fi

echo "== 깃허브와 맞추기"
git fetch -q origin main
if [ "$(git rev-list --count HEAD..origin/main)" != 0 ]; then
  if git diff --quiet && git diff --cached --quiet; then git merge -q --ff-only origin/main
  else
    echo "멈춤: 깃허브에 다른 곳에서 올린 새 변경이 있어요. 먼저 합친 뒤 다시 배포하세요:"
    echo "  git stash && git pull --rebase origin main && git stash pop   (그다음 다시 tools/deploy.sh)"
    exit 1
  fi
fi

echo "== 빌드"
python3 build.py ${DW_VERSION:-}
VER="$(python3 -c 'import json;print(json.load(open("forms/version.json"))["version"])')"

if [ "${DW_SKIP_TEST:-}" = 1 ]; then
  echo "== 점검 (문법만)"; python3 tools/test/syntax.py
else
  tools/test/run.sh
fi

echo "== 커밋"
git add -A
# 비밀 키가 섞여 들어가면 멈춤 (수파베이스 secret · service_role JWT). publishable 키(sb_publishable_)는 괜찮음.
if git diff --cached -U0 | grep -E '^\+' | grep -Eq 'sb_secret_[A-Za-z0-9_-]{8,}|eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}'; then
  echo "멈춤: 비밀 키처럼 보이는 글이 들어 있어요. 올리지 않았어요."; git reset -q; exit 1
fi
if git diff --cached --quiet; then echo "바뀐 게 없어요."; exit 0; fi
printf '%s\n' "$MSG" | git commit -q -F -
git push -q origin main
SHA="$(git rev-parse --short=7 HEAD)"
echo "== 올림: $SHA (버전 $VER)"

if command -v gh >/dev/null 2>&1; then
  echo "== 배포 기다리는 중 (보통 1~2분)"
  R=""
  for _ in $(seq 1 60); do
    R="$(gh api 'repos/dog1377/seosik/actions/runs?per_page=1' --jq '.workflow_runs[0] | "\(.head_sha[0:7]) \(.status) \(.conclusion)"' 2>/dev/null || true)"
    case "$R" in "$SHA"*completed*) break;; esac
    sleep 10
  done
  echo "   배포 결과: ${R:-확인 못 함}"
  LIVE="$(curl -s -m 8 "https://dwfuneral.com/forms/version.json?q=$RANDOM$RANDOM" 2>/dev/null || true)"
  case "$LIVE" in
    *"$VER"*) echo "== 배포 완료 · 사이트 버전 $VER";;
    *) echo "== 저장소 버전: $(gh api 'repos/dog1377/seosik/contents/forms/version.json?ref=main' --jq .content 2>/dev/null | base64 -d 2>/dev/null || echo '?')"
       echo "   (사이트 주소는 여기서 바로 못 열 수 있음 — 배포 결과가 success 면 1~2분 안에 반영)";;
  esac
else
  echo "== 올림 완료 (gh 없음 → 배포 확인은 깃허브 Actions 에서)"
fi
