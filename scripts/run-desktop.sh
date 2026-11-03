#!/usr/bin/env bash
# Entry point for the Windows desktop shortcut.
# Runs the dashboard, opens the browser, and keeps the window open on failure
# so the error message can be read.
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

bash scripts/run.sh --open "$@"
status=$?

# 0: normal exit, 130: stopped with Ctrl+C
if [[ $status -ne 0 && $status -ne 130 ]]; then
    echo
    read -rp "실행에 실패했습니다 (exit $status). Enter를 누르면 창을 닫습니다... " _
fi
exit "$status"

