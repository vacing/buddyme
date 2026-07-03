# Agent 初始化详解

本文档详细描述 buddyMe Agent 从启动到就绪的完整初始化流程，以及背后的机制。

## 一、入口文件关系

```mermaid
flowchart TD
    subgraph 启动方式
        M1["python buddyMe/main.py"]
        M2["python -m buddyMe"]
        M3["buddyme (CLI)"]
    end
    
    M1 --> MainPy["main.py"]
    M2 --> UnderscoreMain["__main__.py"]
    M3 --> CLI["cli.py"]
    
    UnderscoreMain --> CLI
    CLI --> |调用| AgentInit["AgentMain.__init__()"]
    MainPy --> |调用| AgentInit
```

| 启动方式 | 入口文件 | 参数支持 | UI 风格 | 说明 |
|----------|----------|----------|---------|------|
| `python buddyMe/main.py` | `main.py` | `--model`, `--sub-model` | 原生 print | 本地开发模式，`data_dir` 为源码目录 |
| `python -m buddyMe` | `__main__.py` → `cli.py` | `--model`, `--sub-model` | Rich | 包安装模式，`data_dir` 为 `~/.buddyme/` |
| `buddyme` | `cli.py` | `--model`, `--sub-model` | Rich | 包安装模式（同上），只是入口命令不同 |

**关键区别**：
- `main.py` 使用原生 print 输出，`data_dir` 指向源码目录（本地开发模式）
- `cli.py` 使用 Rich UI（spinner + 彩色），`data_dir` 为 `~/.buddyme/`（生产模式）
- `__main__.py` 仅是 `cli.py` 的转发入口（3行代码）

## 二、模型名称解析

模型名称的优先级（从高到低）：

```
命令行参数 (--model/-m) > 环境变量 (BUDDYME_MODEL) > 默认值 (glm_code_plan)
命令行参数 (--sub-model/-s) > 环境变量 (BUDDYME_SUB_MODEL) > 默认值 (glm_code_plan)
```

示例：
```bash
# 通过命令行参数指定模型
python buddyMe/main.py --model deepseek --sub-model glm_code_plan

# 通过环境变量
export BUDDYME_MODEL=deepseek
export BUDDYME_SUB_MODEL=mimo
python -m buddyMe

# 默认值
python -m buddyMe  # model_name="glm_code_plan", sub_model_name="glm_code_plan"
```

## 三、AgentMain.__init__() 初始化流程

```mermaid
flowchart TD
    START["AgentMain.__init__()"] --> STEP1["1. 保存参数: model_name, sub_model_name"]
    STEP1 --> STEP2["2. ModelConfig.get_args(): 获取全局配置"]
    STEP2 --> STEP3["3. 初始化状态变量"]
    
    STEP3 --> STEP4["4. 创建三个 LLM 客户端"]
    STEP4 --> CLIENT1["_client = create_client(model_name)"]
    STEP4 --> CLIENT2["_sub_client = create_client(sub_model_name)"]
    STEP4 --> CLIENT3["_scheduled_sub_client = create_client(sub_model_name)"]
    
    CLIENT1 --> STEP5["5. 计算 max_token 上限"]
    CLIENT2 --> STEP5
    CLIENT3 --> STEP5
    
    STEP5 --> STEP5A["_agent_max_token = _client.max_tokens"]
    STEP5A --> STEP5B["_sub_agent_max_token = _agent_max_token // 4"]
    
    STEP5B --> STEP6["6. 解析目录结构"]
    STEP6 --> DIR1["_PACKAGE_DIR: 包源码根目录（只读）"]
    STEP6 --> DIR2["_USER_DATA_DIR: ~/.buddyme/（可覆盖）"]
    STEP6 --> DIR3["_DATA_DIR: data_dir 或 _USER_DATA_DIR"]
    STEP6 --> DIR4["_WORKSPACE_DIR: 工作空间目录"]
    
    DIR4 --> STEP7["7. 首次运行: _init_user_workspace()"]
    STEP7 --> COPY["递归复制 initspace/ + skill_library/ → ~/.buddyme/"]
    
    COPY --> STEP8["8. 创建 ToolExecutor + 注册工具"]
    STEP8 --> REGTOOLS["注册 BashTool, ReadFileTool, WriteFileTool 等"]
    REGTOOLS --> REGSKILL["注册 InvokeSkillTool"]
    
    REGSKILL --> STEP9["9. 加载 SkillLoader"]
    STEP9 --> SKILLDIRS["扫描 用户目录/skills + 包目录/skills"]
    
    SKILLDIRS --> STEP10["10. 创建 LoopSkillManager"]
    STEP10 --> LOOPSKILLS["加载 skill_library/loop_skills/"]
    
    LOOPSKILLS --> STEP11["11. 构建 system prompt"]
    STEP11 --> SYSPROMPT["build_system_prompt(tool_schemas + brain/ + skill_metadata)"]
    
    SYSPROMPT --> STEP12["12. 初始化记忆系统"]
    STEP12 --> USEMEMORY["UseMemory(brain/USER.md, conversation_log.json)"]
    USEMEMORY --> CONVLOG["ConversationLogger(conversation_log.json)"]
    
    CONVLOG --> STEP13["13. 初始化 HeartbeatManager"]
    STEP13 --> HEARTBEAT["HeartbeatManager(heartbeat.json)"]
    
    HEARTBEAT --> STEP14["14. 创建 TodoManager"]
    STEP14 --> TODOMGR["TodoManager()"]
    
    TODOMGR --> STEP15["15. 创建 CommandRegistry"]
    STEP15 --> CMDS["create_registry() → /help, /model, /loop 等"]
    
    CMDS --> DONE["✅ 初始化完成，Agent 就绪"]
```

## 四、初始化步骤详解

### 步骤 1-3：参数与状态

```python
self.model_name = model_name
_args = ModelConfig.get_args()  # 全局配置（MAX_TOOLS_COMPRESS_LEN, MAX_SEARCH_CALLS 等）

self.messages = []           # 对话历史
self._used_tools = []        # 本轮使用过的工具
self._used_skills = []       # 本轮使用过的技能
self.max_steps = 11          # 主循环最大步数
self._max_heartbeat_steps = 10  # 心跳最大步数
self.max_messages_length = 20   # 对话历史最大条数
```

### 步骤 4-5：三个 LLM 客户端

| 客户端 | 变量名 | 模型 | 用途 |
|--------|--------|------|------|
| 主客户端 | `_client` | `model_name` | 主对话交互 |
| 子任务客户端 | `_sub_client` | `sub_model_name` | 子任务执行（独立 messages） |
| 心跳客户端 | `_scheduled_sub_client` | `sub_model_name` | 心跳定时任务（独立连接） |

**为什么需要三个客户端？**
- **隔离性**：三个客户端各自维护独立的连接状态，互不干扰
- **上下文隔离**：子任务和心跳任务使用独立的 messages，不污染主对话
- **灵活性**：可以为不同场景选择不同模型（未来规划：强模型做规划，快模型做执行）

**max_token 计算**：
```
_agent_max_token = _client.max_tokens           # 从模型配置获取
_sub_agent_max_token = _agent_max_token // 4    # 子任务只分配 1/4
```

### 步骤 6-7：目录解析与首次部署

```mermaid
flowchart LR
    subgraph 包目录只读模板
        PKG_INITSPACE["initspace/"]
        PKG_SKILLS["skill_library/"]
    end
    
    subgraph 用户数据目录
        USR_INITSPACE["~/.buddyme/initspace/"]
        USR_SKILLS["~/.buddyme/skill_library/"]
    end
    
    PKG_INITSPACE -->|首次运行复制| USR_INITSPACE
    PKG_SKILLS -->|首次运行复制| USR_SKILLS
```

**目录角色**：

| 目录 | 变量名 | 来源 | 属性 |
|------|--------|------|------|
| 包源码根目录 | `_PACKAGE_DIR` | `Path(__file__).resolve().parent.parent` | 只读 |
| 用户数据目录 | `_USER_DATA_DIR` | `BUDDYME_HOME` 环境变量 或 `~/.buddyme/` | 可写 |
| 数据目录 | `_DATA_DIR` | `data_dir` 参数 或 `_USER_DATA_DIR` | 可写 |
| 工作空间目录 | `_WORKSPACE_DIR` | `BUDDYME_WORKSPACE` 环境变量 或 `cwd` | 可写 |

**首次部署逻辑** (`_init_user_workspace`)：
1. 检查 `~/.buddyme/skill_library/skills/` 是否已有内容
2. 若已存在 → 跳过（避免覆盖用户自定义 Skill）
3. 若不存在 → 递归复制 `initspace/` 和 `skill_library/` 到 `~/.buddyme/`
4. 不覆盖已有文件（保护用户修改）

### 步骤 8-9：工具注册

```
ToolExecutor 注册流程:
  ├─ BashTool()       → 文件操作（read/write/edit/grep/glob）
  ├─ BaiduSearchTool  → 外部搜索
  └─ InvokeSkillTool  → Skill 激活
```

每个工具注册时设置 `model_name`，使工具内部调用 LLM 时使用正确的模型。

### 步骤 10：Skill 加载

```mermaid
flowchart TD
    SL["SkillLoader(skill_dirs=[user_skills, pkg_skills])"] --> SCAN["扫描两个 skill 目录"]
    SCAN --> INDEX["构建技能索引（name + description）"]
    INDEX --> META["Level 1: 提取元数据 → 注入 system prompt"]
    META --> FULL["Level 2: 匹配后加载完整 SKILL.md → 注入 messages"]
    FULL --> RES["Level 3: 按需读取 scripts/references/assets 资源"]
```

**搜索顺序**：用户目录优先于包内置模板，允许用户覆盖默认 Skill。

### 步骤 11：System Prompt 构建

```
build_system_prompt():
  1. 加载 brain/ 目录下的人格文件（SOUL → IDENTITY → AGENT → HEARTBEAT → SUB_AGENT → USER）
  2. 融合 ToolExecutor 中所有工具的 JSON Schema
  3. 注入 SkillLoader 的元数据 prompt（Level 1）
  4. 组装为完整的 system prompt
```

### 步骤 12：记忆系统

```mermaid
flowchart TD
    UM["UseMemory"] --> EXTRACT["记忆提取器: 从对话中提取记忆"]
    EXTRACT --> DEDUP["去重: 与已有记忆比较"]
    DEDUP --> SCORE["评分: 评估记忆重要性"]
    SCORE --> DECAY["衰减: 时间权重衰减"]
    DECAY --> INTEGRATE["整合: 写入 USER.md"]
    
    CL["ConversationLogger"] --> PERSIST["持久化: JSON格式, 按日期归档"]
    PERSIST --> ROTATE["轮转: 防止日志过大"]
```

### 步骤 13-15：心跳、任务管理、命令系统

| 组件 | 初始化参数 | 职责 |
|------|------------|------|
| `HeartbeatManager` | `config_path=heartbeat.json` | 管理 heartbeat.json 配置、判断活跃时段、调度定时任务 |
| `TodoManager` | 无 | 子任务列表的增删改查、状态追踪 |
| `CommandRegistry` | 无 | 注册 `/help`, `/model`, `/memory`, `/skill`, `/loop` 等命令 |

## 五、初始化时序图

```mermaid
sequenceDiagram
    participant User as 用户/CLI
    participant Main as main.py / cli.py
    participant Agent as AgentMain
    participant LLM as basic_llm
    participant Tool as ToolExecutor
    participant Skill as SkillLoader
    participant Memory as UseMemory
    participant Heartbeat as HeartbeatManager
    
    User->>Main: 启动 + 参数
    Main->>Agent: AgentMain(model_name, sub_model_name, ...)
    
    rect rgb(240, 248, 255)
        Note over Agent: 初始化阶段
        
        Agent->>LLM: create_client(model_name) × 3
        LLM-->>Agent: _client, _sub_client, _scheduled_sub_client
        
        Agent->>Agent: 解析目录 (PACKAGE_DIR, DATA_DIR, WORKSPACE_DIR)
        Agent->>Agent: _init_user_workspace() 首次部署
        
        Agent->>Tool: ToolExecutor() + 注册工具
        Tool-->>Agent: 7个内置工具 + InvokeSkillTool
        
        Agent->>Skill: SkillLoader(user_skills, pkg_skills)
        Skill-->>Agent: Skill 元数据
        
        Agent->>Agent: build_system_prompt(tool_schemas + brain + skill_metadata)
        
        Agent->>Memory: UseMemory(USER.md, conversation_log)
        Agent->>Agent: ConversationLogger(log.json)
        Agent->>Heartbeat: HeartbeatManager(heartbeat.json)
        Agent->>Agent: TodoManager()
        Agent->>Agent: CommandRegistry()
    end
    
    Agent-->>Main: 初始化完成
    Main-->>User: Agent 就绪，等待输入
```

## 六、初始化配置项速查

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 主模型 | `BUDDYME_MODEL` | `glm_code_plan` | 主对话使用的模型 |
| 子任务模型 | `BUDDYME_SUB_MODEL` | `glm_code_plan` | 子任务/心跳使用的模型 |
| 用户数据目录 | `BUDDYME_HOME` | `~/.buddyme/` | 用户数据存储位置 |
| 工作空间 | `BUDDYME_WORKSPACE` | `cwd` | 文件输出目录 |
| 主循环最大步数 | — | `11` | 单次 invoke 最大 LLM 交互轮次 |
| 心跳最大步数 | — | `10` | 心跳 tick 最大 LLM 交互轮次 |
| 对话历史上限 | — | `20` | messages 最大条数 |
| 上下文摘要上限 | — | `6000` 字符 | 记忆摘要最大字符数 |
| 上下文最近轮数 | — | `3` | 保留最近 N 轮对话 |
