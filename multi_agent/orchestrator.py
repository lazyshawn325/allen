#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import shlex
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


async def run_one(agent: AgentSpec, task: str) -> Dict:
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


def summarize(task: str, results: List[Dict]) -> str:
    lines = [f"# Multi-agent run", "", f"Task: {task}", ""]
    for r in results:
        lines.append(f"## {r['agent']}")
        lines.append(f"- status: {r['status']}")
        lines.append(f"- exit: {r['exitCode']}")
        lines.append(f"- cmd: `{r['command']}`")
        if r["stderr"]:
            lines.append(f"- stderr: `{r['stderr'][:300]}`")
        lines.append("")
        preview = (r["stdout"] or "").strip()
        if preview:
            lines.append("```text")
            lines.append(preview[:2000])
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


async def main() -> None:
    ap = argparse.ArgumentParser(description="Run Codex/Gemini in parallel and aggregate output")
    ap.add_argument("task", help="task prompt")
    ap.add_argument("--config", default="multi_agent/agents.json", help="JSON config path")
    ap.add_argument("--out", default="multi_agent/last_run.md", help="summary markdown output")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")

    agents = load_config(cfg_path)
    if not agents:
        raise SystemExit("No agents configured")

    results = await asyncio.gather(*(run_one(a, args.task) for a in agents))

    out = summarize(args.task, results)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(out)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
