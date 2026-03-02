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
    role: str = ""


DEFAULT_CONFIG = {
    "agents": [
        {
            "name": "codex",
            "role": "技术执行负责人：给出可落地实现步骤、脚本与风险控制",
            "command": ["codex", "exec", "{task}"],
            "timeout": 600,
        },
        {
            "name": "gemini",
            "role": "研究与策略负责人：给出备选方案、ROI、时间成本对比",
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
                role=str(a.get("role", "")).strip(),
            )
        )
    return out


def build_agent_task(global_task: str, agent: AgentSpec, plan_mode: bool) -> str:
    if not plan_mode:
        return global_task

    role = agent.role or f"{agent.name} 专家"
    return (
        f"目标：{global_task}\n"
        f"你的角色：{role}\n"
        "请输出：\n"
        "1) 你的方案（3-5点）\n"
        "2) 你负责的具体执行步骤（可直接执行）\n"
        "3) 风险与兜底\n"
        "4) 本角色可交付产物\n"
        "要求：简洁、可落地、中文输出。"
    )


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
        "role": agent.role,
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


def make_synth_prompt(global_task: str, results: List[Dict]) -> str:
    chunks = [
        f"请把多智能体结果整合成一个最终可执行方案。\n总目标：{global_task}",
        "输出格式：\nA. 最终方案摘要\nB. 执行清单（带优先级）\nC. 今日可直接执行的3步\nD. 风险与回退方案",
        "以下是各代理原始输出：",
    ]
    for r in results:
        body = (r.get("stdout") or "")[:3000]
        chunks.append(f"\n[{r['agent']}|role={r.get('role','')}]\n{body}\n")
    return "\n".join(chunks)


async def synthesize(global_task: str, results: List[Dict], synth_agent: AgentSpec) -> Dict:
    prompt = make_synth_prompt(global_task, results)
    out = await run_once(synth_agent, prompt)
    out["agent"] = f"synth:{synth_agent.name}"
    return out


def summarize(task: str, results: List[Dict], synthesis: Dict | None = None) -> str:
    ok = sum(1 for r in results if r["status"] == "ok")
    lines = ["# Multi-agent run", "", f"Task: {task}", f"Summary: {ok}/{len(results)} success", ""]

    if synthesis and synthesis.get("stdout"):
        lines.extend(["## Final Synthesis", "", synthesis["stdout"][:5000], ""])

    lines.append("## Action Checklist")
    for i, r in enumerate(results, 1):
        mark = "[x]" if r["status"] == "ok" else "[ ]"
        lines.append(f"- {mark} P{i} {r['agent']} deliverable review")
    lines.append("")

    for r in results:
        lines.append(f"## {r['agent']}")
        if r.get("role"):
            lines.append(f"- role: {r['role']}")
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
    ap.add_argument("--plan", action="store_true", help="enable role-based task decomposition")
    ap.add_argument("--synthesize", action="store_true", help="run a final synthesis step")
    ap.add_argument("--synth-agent", default="codex", help="agent name for final synthesis")
    ap.add_argument("--git-push", action="store_true", help="auto git add/commit/push after run")
    ap.add_argument("--remote", default="lazyshawn325/allen", help="owner/repo for --git-push")
    ap.add_argument("--branch", default="main", help="target branch for --git-push")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")

    agents = load_config(cfg_path)
    if not agents:
        raise SystemExit("No agents configured")

    selected = {x.strip() for x in args.agents.split(",") if x.strip()}
    if selected:
        agents = [a for a in agents if a.name in selected]
        if not agents:
            raise SystemExit(f"No matched agents from --agents: {sorted(selected)}")

    task_map = {a.name: build_agent_task(args.task, a, args.plan) for a in agents}
    results = await asyncio.gather(*(run_one(a, task_map[a.name], max(args.retries, 0)) for a in agents))

    synthesis = None
    if args.synthesize:
        synth = next((a for a in agents if a.name == args.synth_agent), None)
        if synth is None:
            synth = agents[0]
        synthesis = await synthesize(args.task, results, synth)

    out = summarize(args.task, results, synthesis)
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
            "planMode": args.plan,
            "synthesis": synthesis,
            "results": results,
        }
        jpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved JSON: {jpath}")

    if args.git_push:
        git_push(args.remote, args.branch)
        print(f"Pushed to {args.remote}:{args.branch}")


if __name__ == "__main__":
    asyncio.run(main())
