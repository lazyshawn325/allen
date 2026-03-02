#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


@dataclass
class AgentSpec:
    name: str
    command: List[str]
    timeout: int


DEFAULT_CONFIG = {
    "agents": [
        {
            "name": "codex",
            "command": ["codex", "exec", "{task}"],
            "timeout": 600,
        },
        {
            "name": "gemini",
            "command": ["gemini", "-p", "{task}"],
            "timeout": 600,
        },
    ]
}


def load_config(path: Path) -> List[AgentSpec]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: List[AgentSpec] = []
    for a in data.get("agents", []):
        out.append(
            AgentSpec(
                name=a["name"],
                command=list(a["command"]),
                timeout=int(a.get("timeout", 600)),
            )
        )
    return out


async def run_once(agent: AgentSpec, task: str) -> Dict:
    cmd = [p.format(task=task) for p in agent.command]
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=agent.timeout)
            code = proc.returncode
            status = "ok" if code == 0 else "error"
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            stdout, stderr, code, status = b"", b"TIMEOUT", -1, "timeout"
    except FileNotFoundError:
        stdout, stderr, code, status = b"", b"command not found", 127, "error"

    return {
        "agent": agent.name,
        "startedAt": started,
        "status": status,
        "exitCode": code,
        "command": " ".join(shlex.quote(x) for x in cmd),
        "stdout": stdout.decode("utf-8", errors="replace").strip(),
        "stderr": stderr.decode("utf-8", errors="replace").strip(),
    }


async def run_one(agent: AgentSpec, task: str, retries: int) -> Dict:
    attempts = retries + 1
    last: Dict = {}
    for i in range(1, attempts + 1):
        result = await run_once(agent, task)
        result["attempt"] = i
        result["maxAttempts"] = attempts
        last = result
        if result["status"] == "ok":
            return result
    return last


def summarize(task: str, results: List[Dict]) -> str:
    ok = sum(1 for r in results if r["status"] == "ok")
    lines = ["# Multi-agent run", "", f"Task: {task}", f"Summary: {ok}/{len(results)} success", ""]
    for r in results:
        lines.append(f"## {r['agent']}")
        lines.append(f"- status: {r['status']}")
        lines.append(f"- exit: {r['exitCode']}")
        lines.append(f"- attempt: {r.get('attempt', 1)}/{r.get('maxAttempts', 1)}")
        lines.append(f"- cmd: `{r['command']}`")
        if r["stderr"]:
            lines.append(f"- stderr: `{r['stderr'][:400]}`")
        lines.append("")
        preview = (r["stdout"] or "").strip()
        if preview:
            lines.append("```text")
            lines.append(preview[:2500])
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def git_push(remote: str, branch: str) -> None:
    token_path = Path.home() / ".config/openclaw/github.token"
    if not token_path.exists():
        raise SystemExit(f"token file not found: {token_path}")
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("token file is empty")

    push_url = f"https://{token}@github.com/{remote}.git"
    subprocess.run(["git", "add", "-A"], check=True)
    has_changes = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0
    if has_changes:
        subprocess.run(["git", "commit", "-m", "chore: update multi-agent run artifacts"], check=True)
    subprocess.run(["git", "push", push_url, f"HEAD:{branch}"], check=True)


async def main() -> None:
    ap = argparse.ArgumentParser(description="Run multi agents in parallel and aggregate output")
    ap.add_argument("task", help="task prompt")
    ap.add_argument("--config", default="multi_agent/agents.json", help="JSON config path")
    ap.add_argument("--out", default="multi_agent/last_run.md", help="summary markdown output")
    ap.add_argument("--save-json", default="", help="save raw results to JSON file path")
    ap.add_argument("--agents", default="", help="comma-separated agent names to run (e.g. codex,gemini)")
    ap.add_argument("--retries", type=int, default=0, help="retry count for non-ok results")
    ap.add_argument("--git-push", action="store_true", help="auto git add/commit/push after run")
    ap.add_argument("--remote", default="lazyshawn325/allen", help="owner/repo for --git-push")
    ap.add_argument("--branch", default="main", help="target branch for --git-push")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")

    agents = load_config(cfg_path)
    if not agents:
        raise SystemExit("No agents configured")

    selected = {x.strip() for x in args.agents.split(",") if x.strip()}
    if selected:
        agents = [a for a in agents if a.name in selected]
        if not agents:
            raise SystemExit(f"No matched agents from --agents: {sorted(selected)}")

    results = await asyncio.gather(*(run_one(a, args.task, max(args.retries, 0)) for a in agents))

    out = summarize(args.task, results)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(out)
    print(f"\nSaved: {out_path}")

    if args.save_json:
        jpath = Path(args.save_json)
        jpath.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "task": args.task,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }
        jpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved JSON: {jpath}")

    if args.git_push:
        git_push(args.remote, args.branch)
        print(f"Pushed to {args.remote}:{args.branch}")


if __name__ == "__main__":
    asyncio.run(main())
