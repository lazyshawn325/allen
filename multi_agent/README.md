# Multi-Agent Orchestrator (Codex + Gemini)

并行调用多个 CLI agent，并输出统一汇总。

## v3 新增能力

- `--plan`：按 agent 角色自动拆任务
- `--synthesize`：追加最终总控整合步骤
- `--synth-agent codex`：指定谁做最终整合
- 保留 v2：`--agents`、`--retries`、`--save-json`、`--git-push`

## 快速开始（v3）

```bash
python3 multi_agent/orchestrator.py "做一个大学生副业自动化执行系统" \
  --agents codex,gemini \
  --plan \
  --synthesize \
  --synth-agent codex \
  --retries 1 \
  --save-json multi_agent/last_run.json
```

## 自动推送到 GitHub

```bash
python3 multi_agent/orchestrator.py "更新本周执行计划" \
  --agents codex \
  --plan --synthesize \
  --git-push --remote lazyshawn325/allen --branch main
```

## 配置文件

编辑 `multi_agent/agents.json`：
- `name`: agent 名称
- `role`: 角色描述（v3 任务拆分会用）
- `command`: 命令模板，支持 `{task}` 占位符
- `timeout`: 单个 agent 超时秒数
