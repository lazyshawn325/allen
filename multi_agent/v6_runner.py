#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/ubuntu/.openclaw/workspace')
RUNS = ROOT / 'multi_agent' / 'runs'
LOCK = RUNS / 'v6.lock'


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def send(msg: str, target: str):
    run([
        'openclaw', 'message', 'send', '--channel', 'telegram', '--target', target, '--message', msg
    ])


def build_subtasks(goal: str) -> list[dict]:
    return [
        {"name": "architecture", "task": f"围绕目标【{goal}】给出技术架构、模块划分、数据流。"},
        {"name": "implementation", "task": f"围绕目标【{goal}】给出最小可用实现步骤与命令。"},
        {"name": "risk", "task": f"围绕目标【{goal}】给出风险清单、监控指标、兜底与回滚。"},
    ]


def evaluate_acceptance(outputs: list[dict]) -> tuple[bool, list[str]]:
    checks = []
    for o in outputs:
        text = o.get('stdout', '')
        checks.append((o['name'], len(text) > 300 and ('步骤' in text or '风险' in text or '架构' in text)))
    ok = all(x[1] for x in checks)
    failed = [name for name, passed in checks if not passed]
    return ok, failed


def orchestrator_call(task: str, out_md: Path, out_json: Path, retries: int, agents: str) -> subprocess.CompletedProcess:
    return run([
        'python3', 'multi_agent/orchestrator.py', task,
        '--agents', agents,
        '--plan', '--synthesize', '--synth-agent', 'codex',
        '--retries', str(retries),
        '--out', str(out_md),
        '--save-json', str(out_json),
    ])


def git_push(remote: str, branch: str):
    token = (Path.home() / '.config/openclaw/github.token').read_text(encoding='utf-8').strip()
    push_url = f'https://{token}@github.com/{remote}.git'
    subprocess.run(['git', 'add', '-A'], cwd=ROOT, check=True)
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode != 0:
        subprocess.run(['git', 'commit', '-m', 'chore: v6 run artifacts'], cwd=ROOT, check=True)
    subprocess.run(['git', 'push', push_url, f'HEAD:{branch}'], cwd=ROOT, check=True)


def main() -> int:
    p = argparse.ArgumentParser(description='V6: multi-round pipeline with acceptance and rollback plan')
    p.add_argument('--goal', required=True, help='总体目标')
    p.add_argument('--agents', default='codex,gemini')
    p.add_argument('--retries', type=int, default=1)
    p.add_argument('--remote', default='lazyshawn325/allen')
    p.add_argument('--branch', default='main')
    p.add_argument('--target', default='7237940670')
    p.add_argument('--notify-mode', choices=['always', 'fail-only', 'silent'], default='fail-only')
    p.add_argument('--push', action='store_true')
    args = p.parse_args()

    RUNS.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        print('v6 lock exists, skip')
        return 2
    LOCK.write_text('running', encoding='utf-8')

    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    work = RUNS / f'v6_{ts}'
    work.mkdir(parents=True, exist_ok=True)

    results = []
    try:
        for st in build_subtasks(args.goal):
            md = work / f"{st['name']}.md"
            js = work / f"{st['name']}.json"
            proc = orchestrator_call(st['task'], md, js, args.retries, args.agents)
            results.append({
                'name': st['name'], 'returncode': proc.returncode,
                'md': str(md), 'json': str(js),
                'stdout': proc.stdout[-3000:], 'stderr': proc.stderr[-1200:]
            })

        ok, failed = evaluate_acceptance(results)

        final_md = work / 'final.md'
        final_lines = [
            '# V6 Pipeline Summary',
            '',
            f'Goal: {args.goal}',
            f'UTC: {ts}',
            f'Acceptance: {"PASS" if ok else "FAIL"}',
            '',
            '## Subtasks',
        ]
        for r in results:
            final_lines += [f"- {r['name']}: rc={r['returncode']} md={Path(r['md']).name}"]
        if not ok:
            final_lines += ['', '## Rollback Plan', '- 停止自动推送', '- 回退到上一个稳定提交', '- 仅保留失败日志，人工复核后重跑']
            final_lines += [f"- Failed checks: {', '.join(failed) if failed else 'unknown'}"]

        final_md.write_text('\n'.join(final_lines), encoding='utf-8')
        meta = {
            'goal': args.goal, 'timestamp': ts, 'ok': ok, 'failed': failed,
            'results': results, 'summary': str(final_md)
        }
        (work / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

        if ok and args.push:
            git_push(args.remote, args.branch)

        if args.notify_mode == 'always' or (args.notify_mode == 'fail-only' and not ok):
            status = '✅ PASS' if ok else '❌ FAIL'
            msg = f"[V6] {status}\nGoal: {args.goal}\nRun: {work.name}\nSummary: {final_md}"
            send(msg, args.target)

        print(final_md.read_text(encoding='utf-8'))
        return 0 if ok else 1
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
