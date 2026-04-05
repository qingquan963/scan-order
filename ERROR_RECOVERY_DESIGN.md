# 任务监控 + 错误恢复机制设计（修订版）

> 修订日期：2026-04-02
> 修订原因：DeepSeek Debugger 评审发现的 5 个高风险问题

---

## 0. 修订说明

### 本次修订解决的 5 个高风险问题

| # | 问题 | 风险等级 | 修复策略 |
|---|------|---------|---------|
| 1 | 依赖管理漏洞 — 依赖任务失败时无级联处理策略 | 🔴 高 | 增加 dependsOn 图验证 + 依赖失败策略配置（strict/fail-fast/optional） |
| 2 | 并发写入竞争 — 多 Agent 同时写 checkpoint.json 互相覆盖 | 🔴 高 | 每个任务独立文件（`checkpoints/<task-id>.json`），主文件仅作汇总索引；写操作使用原子 rename |
| 3 | 非幂等操作风险 — 断点恢复时重复执行产生副作用 | 🔴 高 | 所有步骤设计为幂等；记录外部状态快照（数据库版本号、文件 MD5 等） |
| 4 | 强制终止丢进度 — kill -9 等极端情况丢失最近进度 | 🟠 中 | 关键节点（任务开始/每个子步骤完成）强制同步写盘（fsync），禁用缓冲 |
| 5 | Windows 路径问题 — 混合分隔符 + 260 字符路径限制 | 🟠 中 | 统一用 `path.join`；长路径加 `\\?\` 前缀；路径总长度控制在 200 以内 |

---

## 1. Checkpoint 数据结构设计

### 1.1 文件结构：主索引 + 任务独立文件

```
checkpoints/
├── _index.json          # 主索引文件（仅汇总，不含任务详情）
├── <task-id-1>.json     # 每个任务独立的 checkpoint
├── <task-id-2>.json
└── ...
```

**`_index.json`（主索引）**

```json
{
  "version": "2.0",
  "sessionId": "uuid-v4",
  "projectRoot": "C:\\path\\to\\project",
  "createdAt": "2026-04-02T10:00:00+08:00",
  "updatedAt": "2026-04-02T10:30:00+08:00",
  "globalTokenBudget": {
    "limit": 100000,
    "warningThreshold": 0.80
  },

  "taskIndex": {
    "<task-id>": {
      "status": "pending | running | completed | failed",
      "assignedAgent": "executor-1 | planner | coder",
      "priority": 1,
      "dependsOn": ["<task-id>", "<task-id>"],
      "dependsOnPolicy": "strict | fail-fast | optional",
      "createdAt": "ISO8601",
      "startedAt": "ISO8601 | null",
      "completedAt": "ISO8601 | null",
      "retry": {
        "count": 0,
        "maxRetries": 3,
        "lastRetryAt": "ISO8601 | null"
      }
    }
  },

  "executionPlan": {
    "orderedTaskIds": ["task-1", "task-2", "task-3"],
    "currentTaskId": "task-2",
    "completedTaskIds": ["task-1"],
    "failedTaskIds": [],
    "pendingTaskIds": ["task-3"],
    "blockedTasks": ["task-3"]
  },

  "tokenUsage": {
    "sessionStartTime": "ISO8601",
    "inputTokens": 45000,
    "outputTokens": 32000,
    "totalTokens": 77000,
    "budgetLimit": 100000,
    "usagePercent": 0.77,
    "lastCheckedAt": "ISO8601"
  }
}
```

**`<task-id>.json`（任务独立 checkpoint）**

```json
{
  "version": "2.0",
  "taskId": "<task-id>",
  "sessionId": "uuid-v4",

  "checkpoint": {
    "currentNode": "node-name",
    "nextStep": "具体下一步操作描述",
    "completedItems": [
      "已完成步骤1",
      "已完成步骤2"
    ],
    "lastCheckpointAt": "ISO8601",
    "progressPercent": 65,
    "checkpointSequence": 12
  },

  "externalStateSnapshot": {
    "description": "幂等恢复所需的外部状态快照",
    "databaseVersion": "20260402103000",
    "fileSnapshots": {
      "src/data.json": {
        "md5": "a1b2c3d4e5f6",
        "modifiedAt": "ISO8601"
      }
    },
    "apiSnapshots": {},
    "notes": "用于判断断点后步骤是否需要真正执行"
  },

  "result": {
    "summary": "任务执行结果摘要",
    "filesModified": ["file1.md", "file2.ts"],
    "filesCreated": ["newfile.txt"]
  },

  "error": {
    "code": "ERR_TOKEN_EXCEEDED | ERR_PROCESS_CRASH | ERR_NETWORK_TIMEOUT | ...",
    "message": "错误原始信息",
    "stack": "错误堆栈（如果有）",
    "failedAtNode": "出错的节点名",
    "loggedAt": "ISO8601",
    "logFile": "logs/tasks/<task-id>/error-20260402.log"
  }
}
```

> **设计理由**：主索引 `_index.json` 只存任务元数据和状态，不存进度详情。任务详情写入各自独立文件，彻底避免多 Agent 并发写同一文件的竞争问题。写入时每个任务只写自己的文件，粒度更小、冲突概率为零。

---

### 1.2 错误日志文件格式（每任务独立）

```
========================
Task ID: <task-id>
Task Name: <name>
Failed At: ISO8601
Error Code: ERR_XXX
Error Message: <message>
Stack Trace:
<stack>

Checkpoint State:
  Node: <currentNode>
  Next Step: <nextStep>
  Completed Items: <list>
  Checkpoint Sequence: <seq>

External State Snapshot:
  Database Version: <db-version>
  File Snapshots:
    <path>: md5=<md5>, modifiedAt=<time>

Environment:
  Host: <hostname>
  OS: <os>
  Node: <node-version>
  Model: <model-name>
========================
```

---

## 2. 写入 Checkpoint 的时机与策略

### 2.1 必须同步写盘的节点（禁用缓冲，强制 fsync）

| 触发时机 | 写入内容 | 同步级别 |
|---------|---------|---------|
| **任务开始时** | `_index.json` 更新任务状态为 `running`；`<task-id>.json` 写入 `startedAt`、`currentNode` | **强制同步**（fsync） |
| **每个子步骤完成后** | `<task-id>.json` 写入 `completedItems`、`currentNode`、`progressPercent`、`externalStateSnapshot` | **强制同步**（fsync） |
| **任务正常完成时** | `_index.json` 更新状态为 `completed`；`<task-id>.json` 写入 `result.*`、`completedAt` | **强制同步**（fsync） |
| **任务失败时** | `_index.json` 更新状态为 `failed`；`<task-id>.json` 写入 `error.*`；写 `error.log` 文件 | **强制同步**（fsync） |
| **Token 预警触发时** | `_index.json` 更新 `tokenUsage` 快照 | **强制同步**（fsync） |

### 2.2 写入方法：原子 rename（防止写到一半崩溃导致文件损坏）

所有 checkpoint 写操作遵循以下流程：

```
FUNCTION write_checkpoint atomically(file_path, data):
    temp_path = file_path + ".tmp." + uuid + ".tmp"
    WRITE temp_path with JSON.stringify(data)          # 先写临时文件
    RENAME temp_path TO file_path                     # rename 是原子操作
    fsync(dirname(file_path))                          # 强制同步目录元数据
```

> **Windows 注意**：`fsync` 在 Windows 上只能同步文件自身，需额外调用 `FlushFileBuffers`。在 Node.js 中使用 `fsync`（`fs.fsyncSync(fd)`）或 `fs.writeFileSync` 后立即 `fs.fsyncSync`。
>
> **长路径支持**：Windows 路径超过 260 字符时，写入时使用 `\\?\` 前缀：
> ```js
> // Windows 长路径前缀
> const longPath = path.startsWith("\\\\?\\") ? path : "\\\\?\\" + path;
> ```

### 2.3 不写入 checkpoint 的情况

- `pending` 状态（任务还未开始，不需要恢复点）
- 任务内部极细粒度的中间计算（避免频繁 IO）
- 非幂等操作执行中（见第 4 节幂等性保证）

---

## 3. 依赖管理与级联失败策略

### 3.1 dependsOn 图验证

任务启动前和每次 checkpoint 写入后，调度器必须验证依赖图：

```json
{
  "validationRules": {
    "noCircularDependency": true,
    "noSelfDependency": true,
    "allDependenciesExist": true,
    "orphanTasksDetectable": true
  }
}
```

**验证流程：**

1. **图构建**：从所有任务的 `dependsOn` 字段构建 DAG（有向无环图）
2. **环检测**：使用 Kahn算法（拓扑排序）检测环 — 若检测到环，立即失败并报告
3. **自引用检测**：`dependsOn` 中不得包含自身
4. **缺失依赖检测**：所有 `dependsOn` 引用的任务 ID 必须在 `taskIndex` 中存在
5. **拓扑序校验**：恢复时按拓扑序重新排列 `executionPlan.orderedTaskIds`

### 3.2 依赖失败策略（`dependsOnPolicy`）

每个任务可配置依赖失败时的行为策略：

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| `strict`（默认） | 任何依赖任务失败，当前任务立即标记为 `failed`，原因：`ERR_DEPENDENCY_FAILED` | 强耦合任务，后置任务无法独立工作 |
| `fail-fast` | 依赖任务失败时，立即停止当前任务，不等待完成 | 希望快速失败、快速反馈 |
| `optional` | 依赖任务失败时，记录警告但继续执行；前置任务结果缺失时使用缓存/降级逻辑 | 独立子任务，不强制依赖 |

```json
{
  "dependsOn": ["task-1"],
  "dependsOnPolicy": "strict",
  "fallbackResult": {
    "description": "当 task-1 失败时的降级处理说明",
    "useCachedResult": true,
    "skipIfUnavailable": false
  }
}
```

### 3.3 级联失败处理流程

```
FUNCTION handle_dependency_failure(failed_task_id, dependent_tasks):
    FOR each task in dependent_tasks:
        policy = task.dependsOnPolicy  # strict | fail-fast | optional

        IF policy == "strict":
            task.status = "failed"
            task.error = {
                "code": "ERR_DEPENDENCY_FAILED",
                "message": "依赖任务 <failed_task_id> 失败，当前任务强制终止",
                "failedDependency": failed_task_id
            }
            WRITE checkpoint atomically
            # 继续级联检查此任务的依赖者
            recurse

        ELSE IF policy == "fail-fast":
            task.status = "failed"
            task.error = {
                "code": "ERR_DEPENDENCY_FAILED",
                "message": "依赖任务 <failed_task_id> 失败，当前任务 fail-fast"
            }
            WRITE checkpoint atomically

        ELSE IF policy == "optional":
            task.status = "running"  # 继续执行
            task.warnings.append("依赖任务 <failed_task_id> 失败，使用降级逻辑")
            # 使用 fallbackResult 或缓存继续
```

---

## 4. 幂等性保证

### 4.1 幂等步骤设计原则

所有任务步骤必须满足以下条件之一，以确保恢复后重复执行不产生副作用：

1. **天然幂等**：执行一次和执行多次结果相同（如文件读取、HTTP GET、幂等 API 调用）
2. **去重执行**：非幂等操作前先查询"是否已执行"（如检查文件是否已存在、记录是否已插入）
3. **状态比对**：执行前记录外部状态快照，执行后比对，状态未变则跳过

### 4.2 externalStateSnapshot — 外部状态快照机制

每个任务 checkpoint 必须记录执行前的外部依赖状态：

```json
{
  "externalStateSnapshot": {
    "databaseVersion": "20260402103000",
    "fileSnapshots": {
      "src/data.json": {
        "md5": "a1b2c3d4e5f6",
        "modifiedAt": "ISO8601",
        "size": 12345
      },
      "output/report.md": {
        "md5": null,
        "exists": false
      }
    },
    "apiSnapshots": {
      "external-api-v1": {
        "etag": "\"abc123\"",
        "lastModified": "ISO8601"
      }
    }
  }
}
```

**快照比对逻辑（恢复时）：**

```
FUNCTION should_execute_step(step, task_checkpoint):
    snapshot = task_checkpoint.externalStateSnapshot

    FOR each external_dependency in step.dependsOn:
        IF external_dependency.type == "file":
            current_md5 = md5(file_path)
            expected_md5 = snapshot.fileSnapshots[file_path].md5
            IF current_md5 != expected_md5:
                RETURN true  # 文件变了，需要重新执行

        ELSE IF external_dependency.type == "database":
            current_version = db.get_version()
            expected_version = snapshot.databaseVersion
            IF current_version != expected_version:
                RETURN true  # 数据库版本变了

        ELSE IF external_dependency.type == "api":
            current_etag = api.get_etag(endpoint)
            expected_etag = snapshot.apiSnapshots[endpoint].etag
            IF current_etag != expected_etag:
                RETURN true  # API 数据变了

    RETURN false  # 状态未变，跳过此步骤
```

### 4.3 非幂等操作的处理模式

对于无法设计为幂等的操作（如发送通知、扣款、写数据库），采用以下模式：

| 操作类型 | 处理模式 | 说明 |
|---------|---------|------|
| 写数据库 | 事务 + 幂等键 | `INSERT ... ON CONFLICT DO NOTHING` |
| 发送通知 | 消息队列 + 去重 | 消息 ID 唯一，重复消费不重复发送 |
| 外部 API POST | 幂等键 + 状态查询 | 提交前查询是否已提交 |
| 文件覆盖写 | 先快照再写 | 写前记录原文件 MD5，恢复时若 MD5 未变则跳过 |
| 删除操作 | 先 MOVE 到 trash 再删除 | 可恢复；删除前检查是否已被标记删除 |

---

## 5. 恢复流程伪代码（修订版）

### 5.1 调度器侧恢复主流程

```
FUNCTION recover_from_checkpoint(session_id):
    1. 读取 checkpoints/_index.json
    2. 验证 version 兼容性（version 必须为 "2.0"，否则拒绝恢复）

    3. 验证依赖图（ Kahn 算法环检测 + 自引用 + 缺失依赖）
       IF graph has cycle:
           ABORT "依赖图存在环，无法恢复"
       IF missing dependencies detected:
           ABORT "依赖任务不存在"

    4. FOR each task in _index.taskIndex:
        task_file = "checkpoints/" + task.id + ".json"
        task_data = READ task_file IF EXISTS

        IF task.status == "running":
            # ========== 问题4修复：强制 fsync 读取 ==========
            PRINT "⚠️  Task <task.id> was interrupted at: <task_data.checkpoint.currentNode>"
            PRINT "    Next step: <task_data.checkpoint.nextStep>"
            PRINT "    Completed: <task_data.checkpoint.completedItems>"

            IF task.retry.count >= task.retry.maxRetries:
                PRINT "❌ Max retries reached. Marking as failed."
                task.status = "failed"
                UPDATE _index.json atomically
                CONTINUE

            # ========== 问题1修复：检查依赖任务状态 ==========
            unmet = []
            FOR dep_id IN task.dependsOn:
                dep_status = _index.taskIndex[dep_id].status
                IF dep_status NOT IN ["completed", "optional"]:
                    unmet.append(dep_id)

            IF unmet not empty:
                policy = task.dependsOnPolicy
                IF policy IN ["strict", "fail-fast"]:
                    task.status = "failed"
                    task.error = { "code": "ERR_DEPENDENCY_FAILED", "unmetDependencies": unmet }
                    UPDATE _index.json atomically
                    CONTINUE  # 级联处理依赖当前任务的其他任务
                ELSE IF policy == "optional":
                    PRINT "⚠️  Optional dependencies unmet, continuing with fallback"

            task.status = "running"
            task.retry.count += 1
            task.retry.lastRetryAt = NOW()
            UPDATE _index.json atomically

            RESUME task from task_data.checkpoint

        ELSE IF task.status == "failed":
            PRINT "❌ Task <task.id> failed previously."
            PRINT "    Error: <task.error.code> - <task.error.message>"
            PRINT "    Log file: <task.error.logFile>"
            # ========== 问题1修复：级联处理依赖者 ==========
            cascade_handle_failure(task.id)

        ELSE IF task.status == "completed":
            PRINT "✅ Task <task.id> already completed."

        ELSE IF task.status == "pending":
            PRINT "⏳ Task <task.id> not started yet."

    5. 按拓扑序（ Kahn 算法）重新排列 executionPlan.orderedTaskIds
    6. 调度剩余未完成任务

FUNCTION cascade_handle_failure(failed_task_id):
    dependent_tasks = find_tasks_that_depend_on(failed_task_id)
    handle_dependency_failure(failed_task_id, dependent_tasks)
    FOR each newly_failed IN dependent_tasks:
        cascade_handle_failure(newly_failed.id)  # 递归级联
```

### 5.2 执行器侧任务续跑逻辑

```
FUNCTION resume_task(task):
    task_file = "checkpoints/" + task.id + ".json"
    task_data = READ task_file

    PRINT "Resuming from node: <task_data.checkpoint.currentNode>"
    PRINT "Completed so far: <task_data.checkpoint.completedItems>"

    FOR each step in execution_plan:
        IF step.name == task_data.checkpoint.currentNode:
            starting_step = step
            BREAK

    # 执行从断点之后的所有步骤
    FOR step FROM starting_step TO end:
        # ========== 问题3修复：幂等性检查 ==========
        IF NOT should_execute_step(step, task_data):
            PRINT "⏭️  Step <step.name> skipped (external state unchanged)"
            task_data.checkpoint.completedItems.append(step.description + " [skipped-idempotent]")
        ELSE:
            # ========== 问题4修复：执行前写一次 checkpoint ==========
            task_data.checkpoint.currentNode = step.name
            task_data.checkpoint.lastCheckpointAt = NOW()
            task_data.checkpoint.checkpointSequence += 1
            WRITE task_file atomically  # 强制同步
            # ========== 问题3修复：执行后更新外部状态快照 ==========
            task_data.externalStateSnapshot = capture_external_state(step)
            WRITE task_file atomically  # 强制同步

            EXECUTE step

            IF step fails:
                task_data.error = build_error_object(step)
                task_data.status = "failed"
                WRITE task_file atomically
                WRITE error.log atomically
                UPDATE _index.json atomically
                RETURN error

            # 步骤成功：更新进度
            task_data.checkpoint.completedItems.append(step.description)

        # 每个步骤完成后写一次 checkpoint（强制同步）
        task_data.checkpoint.progressPercent = calculate_progress(current_step, total_steps)
        WRITE task_file atomically
        UPDATE _index.json atomically  # 主索引同步更新任务摘要
```

---

## 6. Token 预警阈值建议

### 推荐分级预警

| 阈值 | 行为 | 说明 |
|------|------|------|
| **80%** | 黄色预警 | 通知主会话"Token 使用已超 80%"，建议开始保存进度、整理已完成的工作 |
| **85%** | 橙色预警 | 立即写一次完整 checkpoint，暂停非关键任务 |
| **90%** | 红色预警 | 停止启动新任务，优先完成正在执行的任务并写 checkpoint |
| **95%** | 强制中断 | 立即保存所有状态，不再启动新的子步骤 |

### 预警触发时机

- **每次 checkpoint 写入时**自动检查一次 token 使用率
- **任务开始前**检查一次
- 预警消息格式示例：
  > ⚠️ **[Token 预警]** 当前使用率 **82.3%**（77,000 / 100,000），建议保存当前进度并评估后续任务。

---

## 7. Windows 路径规范

### 7.1 路径使用规范

所有路径操作必须使用 `path.join()` 或 `path.resolve()`，**禁止手写字符串拼接路径**。

```js
// ✅ 正确
const checkpointDir = path.join(projectRoot, "checkpoints");
const taskFile = path.join(checkpointDir, `${taskId}.json`);
const logFile = path.join(projectRoot, "logs", "tasks", taskId, `error-${date}.log`);

// ❌ 错误（禁止）
const badPath = projectRoot + "\\checkpoints\\" + taskId + ".json";
const alsoBad = `${projectRoot}/checkpoints/${taskId}.json`;  // 混用分隔符
```

### 7.2 Windows 长路径支持

Windows 默认路径长度限制为 260 字符（MAX_PATH）。对于超出限制的路径，使用 `\\?\` 前缀（UNC 前缀）：

```js
function toLongPath(pathStr) {
    // 如果已经是 UNC 前缀或以 \\ 开头，直接返回
    if (pathStr.startsWith("\\\\?\\") || pathStr.startsWith("\\\\")) {
        return pathStr;
    }
    return "\\\\?\\" + pathStr;
}

function safePath(pathStr, maxLen) {
    const long = toLongPath(pathStr);
    if (long.length > maxLen) {
        throw new Error(`Path exceeds ${maxLen} chars: ${long.length} - ${long}`);
    }
    return long;
}
```

### 7.3 路径总长度控制策略

所有工作路径设计时总长度不超过 **200 字符**（为 `\\?\` 前缀和运行时扩展留出余量）：

| 路径层级 | 建议最大长度 | 说明 |
|---------|------------|------|
| `projectRoot` | ≤ 80 字符 | 项目根路径 |
| `checkpoints/` 子目录 | ≤ 30 字符 | 目录名 |
| `<task-id>.json` 文件名 | ≤ 50 字符 | 含扩展名 |
| `logs/tasks/<task-id>/` | ≤ 80 字符 | 含任务 ID |
| 单个错误日志文件名 | ≤ 60 字符 | 含日期戳 |

**路径长度验证（开发时强制检查）：**

```js
// 在 checkpoint 写入前调用
function validatePathLength(pathStr, limit = 200) {
    const longPath = toLongPath(pathStr);
    if (longPath.length > limit) {
        throw new Error(
            `Path too long (${longPath.length} > ${limit}): ${pathStr}\n` +
            `Use a shorter project root path or shorter task IDs.`
        );
    }
}
```

### 7.4 推荐的目录结构（路径长度友好）

```
C:\projects\scan-order\          # projectRoot ≤ 24 字符
├── checkpoints\                  # ≤ 12 字符
│   ├── _index.json
│   └── <tid>.json               # taskId 应 ≤ 30 字符
├── logs\
│   └── tasks\
│       └── <tid>\               # taskId 应 ≤ 30 字符
│           └── error-YYYYMMDD.log
└── workspace\
```

> **Task ID 命名建议**：使用短格式 UUID（如 `t1`, `tsk-a1b2`）或哈希值，避免使用完整 UUID（36 字符）作为文件名。

---

## 8. 文件放置建议

### 建议的目录结构

```
~/.openclaw/workspace/<project>/
├── AGENTS.md                     # 主设计规范
├── ERROR_RECOVERY_DESIGN.md      # 本文档（错误恢复规范）
├── checkpoints/                   # 运行时 checkpoint 目录
│   ├── _index.json               # 主索引
│   └── <task-id>.json            # 任务独立 checkpoint
├── logs/
│   ├── sessions/
│   │   └── <session-id>.log       # Session 执行流水日志
│   └── tasks/
│       └── <task-id>/
│           ├── error-YYYYMMDD.log # 错误日志
│           └── stdout.log         # 标准输出日志
└── workspace/                    # 任务工作区
```

### 配套文件清单

| 文件路径 | 用途 |
|---------|------|
| `ERROR_RECOVERY_DESIGN.md` | 本文档，错误恢复设计规范 |
| `checkpoints/_index.json`（运行时） | 主索引快照 |
| `checkpoints/<task-id>.json`（运行时） | 任务独立 checkpoint |
| `logs/tasks/<id>/error-*.log` | 失败任务的独立错误日志 |
| `logs/sessions/<session-id>.log` | Session 级别的执行流水日志 |
| `recovery-runner.js/ts` | 恢复流程代码实现（实现层） |

---

## 附录：核心设计原则

1. **Checkpoints are the source of truth after interruption** — 恢复时以 checkpoint 为准，不依赖进程内存
2. **Write to disk, not just stdout** — 所有关键状态必须落盘，stdout 在崩溃后不可恢复
3. **Fail loudly, fail to a file** — 错误不只是打印，要写独立的日志文件
4. **Token budget is everyone's business** — 所有子 agent 都应感知 token 使用情况
5. **Idempotent recovery** — 恢复流程本身和每个任务步骤都可以重复执行而不破坏状态
6. **Atomic writes prevent corruption** — 使用 rename + fsync 保证写入原子性
7. **Dependency graph is validated on every operation** — 依赖图在每次操作前验证，环和缺失立即失败
8. **Windows paths are first-class citizens** — 路径规范和长度控制从设计阶段就纳入考量
