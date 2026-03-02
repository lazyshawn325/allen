# Multi-agent run

Task: v3 smoke test
Summary: 1/1 success

## Final Synthesis

A. 最终方案摘要  
目标是把 `v3 smoke test` 变成“发布闸门（Smoke Gate）”：只验证上线必需链路，不做全量回归。  
通过标准：`关键链路 100% 通过 + 无 P0/P1 缺陷`。  
执行方式：统一一键脚本（本地/CI 共用）+ 统一报告（结果、耗时、失败接口、日志路径）+ 失败即阻断发布并触发回退流程。  
建议最小用例集控制在 8-12 条，覆盖：健康检查、鉴权、核心读、核心写（dryRun/沙箱）、版本配置、关键依赖可达。

B. 执行清单（带优先级）  
P0（今天必须完成）
1. 冻结 Smoke Gate 标准：明确“通过/失败”判定、阻断条件、责任人。  
2. 落地 `smoke/run_v3_smoke.sh` 并参数化 `BASE_URL`、`TOKEN`。  
3. 完成最小用例（先 4 条核心，再扩到 8-12 条）。  
4. 接入 CI（如 `.github/workflows/v3-smoke.yml`），失败即 job fail。  
5. 输出标准化 artifacts：`artifacts/smoke_*.log`，记录失败响应体和日志路径。

P1（本周内）
1. 增加环境指纹校验：版本号、配置哈希，防环境漂移。  
2. 写接口统一使用 `dryRun` 或专用测试租户+可清理数据前缀。  
3. 外部依赖失败分级：阻断失败 vs 观察失败；关键依赖允许 1 次重试。  
4. 每条用例至少校验 1 个关键业务字段，避免“HTTP 200 假绿”。

P2（稳定性增强）
1. 增加趋势看板：通过率、耗时、失败 Top 接口。  
2. 增加自动回滚触发器（或至少自动阻断发布并通知）。

C. 今日可直接执行的3步  
1. 创建并执行脚本  
- 新建 `smoke/run_v3_smoke.sh`（用你给的版本），`chmod +x`。  
- 配置环境变量后跑首轮：  
```bash
export BASE_URL="https://staging.example.com"
export TOKEN="xxxx"
./smoke/run_v3_smoke.sh
```

2. 接入 CI 闸门  
- 新建 `.github/workflows/v3-smoke.yml`，使用 `workflow_dispatch` 先手动触发验证。  
- 将 `BASE_URL`、`SMOKE_TOKEN` 放入仓库 secrets。

3. 设定发布阻断规则并演练一次失败场景  
- 规则：smoke fail => 禁止继续发布。  
- 演练：故意让一个用例失败，确认能看到失败报告、日志路径、阻断生效。

D. 风险与回退方案  
1. 环境漂移（staging/production 不一致）  
- 防护：执行前打印版本/配置哈希并入报告。  
- 回退：指纹不匹配直接 `FAIL FAST`，停止发布。

2. 测试污染共享数据  
- 防护：仅 `dryRun` 或专用租户。  
- 回退：保留清理脚本；发现污染立即清理并冻结该写用例。

3. 第三方依赖抖动导致误报  
- 防护：关键依赖 1 次重试，失败分类（阻断/观察）。  
- 回退：若仅观察失败，允许发布但标记风险并人工确认。

4. 假绿（只看状态码）  
- 防护：关键字段断言（如 `success=true`、`id` 存在、版本匹配）。  
- 回退：发现假绿后立即补断言并回放最近一次发布前 smoke。  

如果你愿意，我下一步可以把这份方案直接转成一个 `v3-smoke-checklist.md`（可贴到你们发布流程里直接执行）。

## Action Checklist
- [x] P1 codex deliverable review

## codex
- role: 技术执行负责人：给出可落地实现步骤、脚本与风险控制
- status: ok
- exit: 0
- attempt: 1/1
- cmd: `codex exec '目标：v3 smoke test
你的角色：技术执行负责人：给出可落地实现步骤、脚本与风险控制
请输出：
1) 你的方案（3-5点）
2) 你负责的具体执行步骤（可直接执行）
3) 风险与兜底
4) 本角色可交付产物
要求：简洁、可落地、中文输出。'`
- stderr: `OpenAI Codex v0.106.0 (research preview)
--------
workdir: /home/ubuntu/.openclaw/workspace
model: gpt-5.3-codex
provider: openai
approval: never
sandbox: read-only
reasoning effort: none
reasoning summaries: none
session id: 019caf65-79bf-7903-b15c-3d9396de1820
--------
user
目标：v3 smoke test
你的角色：技术执行负责人：给出可落地实现步骤、脚本与风险控制
请输出：
1) 你的方案（3-5点）
2) 你负责的具体执行步骤（可直接执行）
3) 风险与兜底
4) 本角色可交付产物
要求：简洁、可落地、中文输出`

```text
**1) 方案（4点）**
1. 先定义 `Smoke Gate`：只验证“能否上线”，不做全量回归；通过标准为 `关键链路100%通过 + 无P0/P1`。  
2. 建立最小用例集（8-12条）：`健康检查`、`鉴权`、`核心读`、`核心写(可回滚/沙箱)`、`版本与配置`、`关键依赖可达`。  
3. 脚本化一键执行：本地与 CI 共用同一脚本，输出统一报告（通过/失败、耗时、失败接口、日志路径）。  
4. 加入风险控制：失败即停、自动采集日志与响应体、失败后自动触发回滚/阻断发布。

**2) 我负责的具体执行步骤（可直接执行）**
```bash
# 0) 准备
mkdir -p smoke artifacts

# 1) 新建脚本
cat > smoke/run_v3_smoke.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

: "${BASE_URL:?need BASE_URL}"
: "${TOKEN:?need TOKEN}"

TS=$(date +%Y%m%d_%H%M%S)
REPORT="artifacts/smoke_${TS}.log"
FAIL=0

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$REPORT"; }

check_get(){
  local name="$1" path="$2" expect="$3"
  local body code
  body=$(mktemp); code=$(mktemp)
  curl -sS -o "$body" -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL$path" > "$code" || true
  http_code=$(cat "$code")
  if [[ "$http_code" != "200" ]]; then
    log "FAIL $name http=$http_code path=$path"; cat "$body" >> "$REPORT"; FAIL=1; return
  fi
  if ! grep -q "$expect" "$body"; then
    log "FAIL $name expect='$expect' path=$path"; cat "$body" >> "$REPORT"; FAIL=1; return
  fi
  log "PASS $name"
}

check_post(){
  local name="$1" path="$2" payload="$3" expect="$4"
  local body code
  body=$(mktemp); code=$(mktemp)
  curl -sS -o "$body" -w "%{http_code}" \
    -X POST "$BASE_URL$path" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$payload" > "$code" || true
  http_code=$(cat "$code")
  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    log "FAIL $name http=$http_code path=$path"; cat "$body" >> "$REPORT"; FAIL=1; return
  fi
  if ! grep -q "$expect" "$body"; then
    log "FAIL $name expect='$expect' path=$path"; cat "$body" >> "$REPORT"; FAIL=1; return
  fi
  log "PASS $name"
}

log "START v3 smoke BASE_URL=$BASE_URL"

check_get  "health"        "/health"               "UP"
check_get  "version"       "/api/v3/version"       "v3"
check_get  "profile"       "/api/v3/me"            "\"id\""
check_post "order_dry_run" "/api/v3/orders"        '{"dryRun":true,"items":[{"sku":"SMOKE-001","qty":1}]}' "\"success\":true"

if [[ $FAIL -ne 0 ]]; then
  log "RESULT=FAIL report=$REPORT"
  exit 1
fi

log "RESULT=PASS report=$REPORT"
EOF

chmod +x smoke/run_v3_smoke.sh

# 2) 执行（示例）
# export BASE_URL="https://staging.example.com"
# export TOKEN="xxxx"
# ./smoke/run_v3_smoke.sh
```

CI 接入（示例，GitHub Actions）：
```yaml
# .github/workflows/v3-smoke.yml
name: v3-smoke
on: [workflow_dispatch]
jobs:
  smoke
```
