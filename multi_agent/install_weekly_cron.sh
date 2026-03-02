#!/usr/bin/env bash
set -euo pipefail

CRON_LINE='0 13 * * 1 /home/ubuntu/.openclaw/workspace/multi_agent/v4_runner.sh >> /home/ubuntu/.openclaw/workspace/multi_agent/runs/cron.log 2>&1'

( crontab -l 2>/dev/null | grep -v 'multi_agent/v4_runner.sh' ; echo "$CRON_LINE" ) | crontab -

echo "Installed weekly cron: $CRON_LINE"
