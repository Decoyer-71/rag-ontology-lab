# .githooks 공용 — 각 훅이 source 한다. (CLAUDE.md §15-5)
#
# ⚠ 파이썬을 **저장소 루트 → 이 훅 폴더의 부모** 순서로 찾는다.
#   core.hooksPath 가 상대경로(.githooks)든 절대경로든 같은 검사기를 부르게 하기 위해서다.
#   LAB_PYTHON 을 세우면 그것을 쓴다 (자가시험용).
#
# ⚠⚠ fail-closed — 파이썬이 없으면 검사를 못 하므로 **막는다.**

hook_dir=$(cd "$(dirname "$0")" && pwd)
top_dir=$(git rev-parse --show-toplevel 2>/dev/null)

lab_py="${LAB_PYTHON:-}"
for cand in "$top_dir/.venv/Scripts/python.exe" "$top_dir/.venv/bin/python" \
            "$(dirname "$hook_dir")/.venv/Scripts/python.exe" "$(dirname "$hook_dir")/.venv/bin/python"; do
  [ -n "$lab_py" ] && break
  [ -x "$cand" ] && lab_py="$cand"
done

run_scan() {
  if [ -z "$lab_py" ] || [ ! -x "$lab_py" ]; then
    echo "[privacy] ⛔ .venv 파이썬을 못 찾아 개인정보 검사를 못 합니다 — 막습니다 (docs/SETUP.md §2)" >&2
    exit 1
  fi
  "$lab_py" "$hook_dir/privacy_scan.py" "$@"
}

# 커밋하자마자 원격으로 올린다. 올리기 직전에 pre-push(개인정보 관문 ②)가 한 번 더 본다.
# ⚠ 실패해도 커밋은 로컬에 남는다 — 훅은 0 으로 끝나 커밋을 되돌리지 않는다.
auto_push() {
  git_dir=$(git rev-parse --git-dir 2>/dev/null) || return 0

  # rebase·merge·cherry-pick 도중이면 올리지 않는다 — 중간 상태를 공개하지 않는다
  for f in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    [ -e "$git_dir/$f" ] && return 0
  done

  if [ "$(git config --bool lab.autopush)" = "false" ]; then
    echo "[auto-push] 꺼져 있습니다 (git config lab.autopush false) — 올리지 않았습니다" >&2
    return 0
  fi

  branch=$(git symbolic-ref --short -q HEAD) || return 0
  upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) || {
    echo "[auto-push] ⚠ $branch 에 upstream 이 없어 올리지 않았습니다 — git push -u origin $branch" >&2
    return 0
  }

  # ⚠ GIT_TERMINAL_PROMPT=0 — 자격증명을 물으며 멈추느니 실패하고 알린다
  out=$(GIT_TERMINAL_PROMPT=0 git push --quiet 2>&1)
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "[auto-push] ✅ $branch → $upstream 올림 ($1)" >&2
  else
    [ -n "$out" ] && printf '%s\n' "$out" | sed 's/^/  /' >&2
    echo "[auto-push] ⚠ 올리지 못했습니다 — 커밋은 로컬에 남아 있습니다." >&2
    echo "            원인(오프라인 · 개인정보 관문 · 원격이 앞섬)을 해결한 뒤 git push" >&2
  fi
  return 0
}
