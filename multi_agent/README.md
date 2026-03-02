# Multi-Agent Orchestrator (Codex + Gemini)

这个小工具会并行调用多个 CLI agent，并输出统一汇总。

## 快速开始

```bash
python3 multi_agent/orchestrator.py "给我一个待办 app 的技术方案"
```

输出：
- 终端打印汇总
- 文件 `multi_agent/last_run.md`

## 配置

编辑 `multi_agent/agents.json`：
- `name`: agent 名称
- `command`: 命令模板，支持 `{task}` 占位符
- `timeout`: 单个 agent 超时秒数

你可以加第三个 agent（比如 Claude Code），示例：

```json
{
  "name": "claude",
  "command": ["claude", "-p", "{task}"],
  "timeout": 600
}
```

## 说明

- 这是“主控 + 多执行体”最小可用版本。
- 若某个 CLI 参数与你本机不一致，改 `agents.json` 即可。
