# Extreme Stack: Skill + MCP + Hook

已准备：

1. **Skill/CLI 能力**
   - `clawhub`（已装）
   - `codex`（已装）
   - `gemini`（已装）
   - `mcporter`（通过 setup 脚本安装）

2. **MCP 模板**
   - `automation_stack/mcp/servers.json`
   - 包含 `filesystem` + `fetch` 两个 server 模板

3. **Hook 模板**
   - `automation_stack/hooks/post_run_summary.sh`
   - 输入 markdown 报告路径，自动提取 `Final Synthesis` 并发 Telegram 摘要

## 一键安装

```bash
bash automation_stack/setup_extreme.sh
```

## 验证

```bash
mcporter --help | head
cat automation_stack/mcp/servers.json
```

## 调用 Hook 示例

```bash
bash automation_stack/hooks/post_run_summary.sh /home/ubuntu/.openclaw/workspace/multi_agent/last_run.md
```
