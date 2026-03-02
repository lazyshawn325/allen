#!/usr/bin/env bash
set -euo pipefail

cd /home/ubuntu/.openclaw/workspace

TASK="${1:-每周复盘：总结本周副业推进进度，给出下周3个最高优先级动作}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT_MD="multi_agent/runs/run_${TS}.md"
OUT_JSON="multi_agent/runs/run_${TS}.json"

mkdir -p multi_agent/runs

python3 multi_agent/orchestrator.py "$TASK" \
  --agents codex,gemini \
  --plan \
  --synthesize \
  --synth-agent codex \
  --retries 1 \
  --out "$OUT_MD" \
  --save-json "$OUT_JSON" \
  --git-push \
  --remote lazyshawn325/allen \
  --branch main

SUMMARY="$(awk 'BEGIN{p=0} /^## Final Synthesis/{p=1;next} /^## Action Checklist/{p=0} p{print}' "$OUT_MD" | head -c 1400)"

if [[ -z "$SUMMARY" ]]; then
  SUMMARY="V4自动任务已完成：${TS}。详见仓库 multi_agent/runs 下最新报告。"
fi

TARGET="${TG_TARGET:-7237940670}"
openclaw message send --channel telegram --target "$TARGET" --message "[Multi-Agent V4] 自动运行完成 (${TS})\n\n${SUMMARY}"

echo "Done: $OUT_MD"
