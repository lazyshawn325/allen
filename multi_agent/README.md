# Multi-Agent Orchestrator (Codex + Gemini)

## 极致版（v5）

新增：
- `v5_runner.py`：一键执行全流程（plan + synth + push + 汇总）
- 并发锁：避免重复触发导致重叠运行
- 运行元数据落盘：`multi_agent/runs/meta_*.json`
- 通知策略：`always | fail-only | silent`
- `install_weekly_cron_v5.sh`：一键安装周任务（默认失败才通知）

## 一键运行（推荐）

```bash
cd /home/ubuntu/.openclaw/workspace
python3 multi_agent/v5_runner.py --task "做一份本周副业推进复盘" --notify-mode fail-only
```

## 定时任务安装

默认每周一 13:00 UTC：

```bash
bash multi_agent/install_weekly_cron_v5.sh
```

自定义 cron 表达式示例（每天 01:30 UTC）：

```bash
bash multi_agent/install_weekly_cron_v5.sh "30 1 * * *"
```

## v6（多轮 + 验收 + 回滚策略）

```bash
cd /home/ubuntu/.openclaw/workspace
python3 multi_agent/v6_runner.py --goal "做一个大学生副业自动化系统" --push
```

特性：
- 自动拆 3 个子任务并多轮执行
- 自动验收（输出质量门槛）
- 失败自动给回滚策略
- 可选自动 push

## v3/v4/v5 仍可用

- `orchestrator.py`：核心编排引擎
- `v4_runner.sh`：shell 版本 runner
- `v5_runner.py`：单轮极致自动化 runner
