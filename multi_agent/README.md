# Multi-Agent Orchestrator (Codex + Gemini)

并行调用多个 CLI agent，并输出统一汇总。

## 快速开始

```bash
python3 multi_agent/orchestrator.py "给我一个待办 app 的技术方案"
```

输出：
- 终端打印汇总
- 文件 `multi_agent/last_run.md`

## v2 新增能力

- `--agents codex,gemini`：选择执行体
- `--save-json multi_agent/last_run.json`：保存结构化结果
- `--retries 1`：失败自动重试
- `--git-push --remote lazyshawn325/allen --branch main`：自动提交并推送

## 示例

```bash
python3 multi_agent/orchestrator.py "做一个副业自动化方案" \
  --agents codex,gemini \
  --retries 1 \
  --save-json multi_agent/last_run.json
```

带自动推送：

```bash
python3 multi_agent/orchestrator.py "更新本周执行计划" \
  --agents codex \
  --git-push --remote lazyshawn325/allen --branch main
```

## 配置

编辑 `multi_agent/agents.json`：
- `name`: agent 名称
- `command`: 命令模板，支持 `{task}` 占位符
- `timeout`: 单个 agent 超时秒数

可自行新增第三个 agent（例如 Claude）。
