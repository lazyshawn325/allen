#!/usr/bin/env bash
set -euo pipefail
REPORT_PATH="${1:-}"
if [[ -z "$REPORT_PATH" || ! -f "$REPORT_PATH" ]]; then
  echo "usage: post_run_summary.sh <report.md>" >&2
  exit 1
fi
SUMMARY="$(awk 'BEGIN{p=0} /^## Final Synthesis/{p=1;next} /^## Action Checklist/{p=0} p{print}' "$REPORT_PATH" | head -c 1200)"
[[ -z "$SUMMARY" ]] && SUMMARY="自动任务完成，见报告：$REPORT_PATH"
openclaw message send --channel telegram --target "7237940670" --message "[Hook] 任务摘要\n\n$SUMMARY" >/dev/null 2>&1 || true
