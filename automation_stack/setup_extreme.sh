#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
npm config set prefix "$HOME/.local" >/dev/null 2>&1 || true

# CLIs
npm i -g mcporter @modelcontextprotocol/server-filesystem >/dev/null

mkdir -p /home/ubuntu/.openclaw/workspace/automation_stack/{mcp,hooks}

cat > /home/ubuntu/.openclaw/workspace/automation_stack/mcp/servers.json <<'JSON'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/ubuntu/.openclaw/workspace"
      ]
    }
  }
}
JSON

cat > /home/ubuntu/.openclaw/workspace/automation_stack/hooks/post_run_summary.sh <<'BASH'
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
BASH

chmod +x /home/ubuntu/.openclaw/workspace/automation_stack/hooks/post_run_summary.sh

echo "Done."
echo "MCP config: /home/ubuntu/.openclaw/workspace/automation_stack/mcp/servers.json"
echo "Hook script: /home/ubuntu/.openclaw/workspace/automation_stack/hooks/post_run_summary.sh"