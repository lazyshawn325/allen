# Multi-Agent Orchestrator (Codex + Gemini)

并行调用多个 CLI agent，并输出统一汇总。

## v4 新增能力

- 定时自动跑（`install_weekly_cron.sh`）
- 运行后自动推 GitHub（通过 `--git-push`）
- 自动 Telegram 摘要通知（`v4_runner.sh`）

## 快速开始（v4）

```bash
bash multi_agent/v4_runner.sh "做一份本周副业推进复盘"
```

执行后会：
1. 跑 `orchestrator.py`（plan + synthesize）
2. 保存到 `multi_agent/runs/`
3. 自动提交并推送到 `lazyshawn325/allen:main`
4. 自动发 Telegram 摘要

> 默认 Telegram 目标为 `7237940670`，可通过环境变量覆盖：

```bash
TG_TARGET=123456789 bash multi_agent/v4_runner.sh "你的任务"
```

## 安装每周定时任务（UTC）

```bash
bash multi_agent/install_weekly_cron.sh
```

默认每周一 13:00 UTC 运行一次。

## v3 核心参数（保留）

- `--plan`：按 agent 角色自动拆任务
- `--synthesize`：追加最终总控整合步骤
- `--synth-agent codex`：指定谁做最终整合
- `--agents`、`--retries`、`--save-json`、`--git-push`
