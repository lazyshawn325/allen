#!/usr/bin/env bash
set -euo pipefail

# Default: Monday 13:00 UTC
SCHEDULE="${1:-0 13 * * 1}"
CMD="cd /home/ubuntu/.openclaw/workspace && /usr/bin/env python3 multi_agent/v5_runner.py --notify-mode fail-only >> /home/ubuntu/.openclaw/workspace/multi_agent/runs/cron_v5.log 2>&1"

( crontab -l 2>/dev/null | grep -v 'multi_agent/v5_runner.py' ; echo "$SCHEDULE $CMD" ) | crontab -

echo "Installed v5 cron: $SCHEDULE"
