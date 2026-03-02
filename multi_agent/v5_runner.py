#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/ubuntu/.openclaw/workspace')
RUNS = ROOT / 'multi_agent' / 'runs'
LOCK = RUNS / 'v5.lock'


def sh(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=check)


def send_tg(msg: str, target: str) -> None:
    sh([
        'openclaw', 'message', 'send',
        '--channel', 'telegram',
        '--target', target,
        '--message', msg,
    ], check=False)


def extract_synthesis(md_path: Path) -> str:
    text = md_path.read_text(encoding='utf-8', errors='replace')
    start = text.find('## Final Synthesis')
    end = text.find('## Action Checklist')
    if start == -1:
        return ''
    chunk = text[start + len('## Final Synthesis'): end if end != -1 else None].strip()
    return chunk[:1800]


def main() -> int:
    p = argparse.ArgumentParser(description='Extreme automation runner for multi-agent pipeline')
    p.add_argument('--task', default='每周复盘：总结本周副业推进进度，给出下周3个最高优先级动作')
    p.add_argument('--agents', default='codex,gemini')
    p.add_argument('--retries', type=int, default=1)
    p.add_argument('--remote', default='lazyshawn325/allen')
    p.add_argument('--branch', default='main')
    p.add_argument('--target', default=os.getenv('TG_TARGET', '7237940670'))
    p.add_argument('--notify-mode', choices=['always', 'fail-only', 'silent'], default='fail-only')
    args = p.parse_args()

    RUNS.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        print('lock exists, skip run:', LOCK)
        return 2
    LOCK.write_text(str(os.getpid()), encoding='utf-8')

    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    out_md = RUNS / f'run_{ts}.md'
    out_json = RUNS / f'run_{ts}.json'

    try:
        cmd = [
            'python3', 'multi_agent/orchestrator.py', args.task,
            '--agents', args.agents,
            '--plan', '--synthesize', '--synth-agent', 'codex',
            '--retries', str(args.retries),
            '--out', str(out_md),
            '--save-json', str(out_json),
            '--git-push', '--remote', args.remote, '--branch', args.branch,
        ]
        proc = sh(cmd, check=False)

        ok = proc.returncode == 0
        summary = extract_synthesis(out_md) if out_md.exists() else ''
        if not summary:
            summary = f'运行完成={ok}，详见 {out_md.name}'

        payload = {
            'timestamp': ts,
            'ok': ok,
            'task': args.task,
            'returncode': proc.returncode,
            'stdout_tail': proc.stdout[-1500:],
            'stderr_tail': proc.stderr[-1000:],
            'report': str(out_md),
            'json': str(out_json),
        }
        (RUNS / f'meta_{ts}.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

        if args.notify_mode == 'always' or (args.notify_mode == 'fail-only' and not ok):
            status = '✅ 成功' if ok else '❌ 失败'
            msg = f"[Multi-Agent V5] {status} ({ts} UTC)\n\n任务：{args.task}\n\n{summary}"
            if not ok:
                msg += f"\n\n错误摘要:\n{proc.stderr[-500:]}"
            send_tg(msg, args.target)

        print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        return proc.returncode
    finally:
        if LOCK.exists():
            LOCK.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
