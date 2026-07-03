# buddyMe 项目架构文档

> 本文档为架构总览，各子系统的详细文档已拆分为独立文件，请点击链接查看。

## 一、项目概述

**buddyMe** 是一个基于多模型 LLM 的自主 Agent 框架，支持智谱 GLM、DeepSeek、百度 ERNIE、小米 MiMo、通义千问等多种大模型。它具备任务规划、子任务分解执行、工具调用、技能系统、记忆系统和定时心跳任务等能力。

## 二、目录结构

```
buddyme/
├── .env                          # 环境变量（API Keys）
├── pyproject.toml                # 项目依赖配置
├── run.sh                        # 启动脚本
└── BuddyMe/                      # 主包
    ├── main.py                   # 本地开发入口
    ├── cli.py                    # CLI 入口
    ├── __main__.py               # python -m buddyMe 入口
    ├── agent_moudle/             # Agent 核心模块
    │   └── agent.py              # AgentMain 主类
    ├── llm_moudle/               # LLM 调用层
    │   ├── model_config.py       # 多模型配置管理
    │   └── basic_llm.py          # 统一客户端工厂
    ├── anthropic_standard/       # 协议适配层
    │   ├── basic_anthropic_client.py  # 基础客户端（OpenAI兼容）
    │   ├── anthropic_code_plan_base.py # Anthropic协议客户端
    │   ├── basic_anthropic_tool.py    # BaseTool/ToolExecutor 基类
    │   └── unified_client.py          # 统一客户端（自动选协议）
    ├── tool_moudle/              # 工具模块
    │   ├── baidu_search_tool.py  # 百度搜索工具
    │   ├── bash_tool.py          # Bash/文件操作工具集
    │   └── invoke_skill_tool.py  # Skill 激活工具
    ├── cmd_library/              # 命令系统（/前缀拦截）
    │   ├── base.py               # 命令基类定义
    │   ├── registry.py           # 命令注册表
    │   └── builtin/              # 内置命令
    │       ├── system_cmds.py    # /help, /model, /exit 等
    │       ├── memory_cmds.py    # /memory 记忆管理
    │       ├── skill_cmds.py     # /skill 技能管理
    │       └── loop_cmds.py      # /loop 定时任务管理
    ├── initspace/                # 初始化与运行时支撑
    │   ├── brain/                # 人格分层文件
    │   │   ├── SOUL.md           # L0 人格内核
    │   │   ├── IDENTITY.md       # L1 角色身份
    │   │   ├── AGENT.md          # 执行规范
    │   │   ├── HEARTBEAT.md      # 心跳任务规范
    │   │   ├── SUB_AGENT.md      # 子任务安全规则
    │   │   └── USER.md           # 用户记忆（自进化）
    │   ├── contextbuild.py       # System Prompt 动态构建器
    │   ├── heartbeat.py          # 心跳/定时任务管理器
    │   ├── memorybuild.py        # 对话记录持久化
    │   ├── use_memory.py         # 用户记忆管理（提取/去重/衰减）
    │   ├── memory_extractor.py   # 记忆提取器
    │   ├── skill_loader.py       # Skill 三层渐进式加载引擎
    │   ├── loop_skill_manager.py # Loop Skill 管理器
    │   ├── loop_prompt_enhancer.py # Loop Prompt 增强器
    │   ├── todo_manager.py       # 任务规划与管理
    │   └── memorys/              # 运行时数据存储
    └── skill_library/            # 技能库
        ├── index.json            # 技能索引
        ├── skills/               # 标准技能（SKILL.md规范）
        └── loop_skills/          # 循环技能（定时执行）
```

## 三、核心模块概览

> 📄 详见 [核心模块详解与模块间调用关系](core-modules.md)

| 模块 | 所在目录 | 核心职责 |
|------|----------|----------|
| LLM调用层 | `llm_moudle/` + `anthropic_standard/` | 多模型统一调用 |
| 工具系统 | `tool_moudle/` + `basic_anthropic_tool.py` | 工具注册与执行 |
| 技能系统 | `skill_library/` + `skill_loader.py` | 技能渐进式加载与匹配 |
| 记忆系统 | `use_memory.py` + `memory_extractor.py` | 用户记忆自进化 |
| 命令系统 | `cmd_library/` | 零token命令拦截 |
| 运行时支撑 | `initspace/` | 人格/心跳/任务/上下文 |

## 四、核心执行流程概览

> 📄 详见 [核心执行流程与Agent初始化](execution-flow.md)

Agent 从用户输入到最终输出经历三个阶段：
1. **简单任务短路** — 直接单轮 LLM + 工具调用循环
2. **任务规划分解** — LLM 分解子任务 → TodoManager 管理
3. **子任务独立执行 + 最终合并** — 各子任务使用独立 messages，结果汇总

## 五、关键设计特点

| 特性 | 说明 |
|------|------|
| **多模型热切换** | 运行时通过 `switch_model()` 切换，主/子/心跳客户端独立 |
| **三阶段执行** | 简单任务短路 → 任务规划分解 → 子任务独立执行 → 最终合并 |
| **子任务隔离** | 每个子任务使用独立 messages，不污染主对话上下文 |
| **Skill 渐进加载** | Level 1 元数据 → Level 2 指令体 → Level 3 资源，按需加载 |
| **协议自适配** | 根据 base_url 或模型名后缀自动选择 OpenAI/Anthropic 协议 |
| **命令零消耗** | `/` 前缀命令在 LLM 推理前拦截，不消耗 token |
| **记忆自进化** | 对话后自动提取记忆 → 去重 → 评分 → 衰减 → 写入 USER.md |
| **心跳定时任务** | 后台线程定时触发，使用独立客户端和精简 prompt |
| **原子写入** | 文件操作使用 atomic_write 保证数据安全 |

## 六、数据流概览

```
用户输入
  │
  ├─ [/命令] → CommandRegistry → CommandResult → 直接输出
  │
  └─ [自然语言] → AgentMain.invoke()
       │
       ├─ ContextBuild 构建 system prompt
       │    ├─ brain/ 人格文件
       │    ├─ Skill 元数据（Level 1）
       │    ├─ 工具 Schema
       │    └─ 用户记忆摘要
       │
       ├─ 判断任务复杂度
       │    ├─ 简单 → _run_simple（单轮循环）
       │    └─ 复杂 → plan_task → 子任务列表
       │
       ├─ 子任务执行循环
       │    ├─ LLM 推理
       │    ├─ 工具调用 → ToolExecutor
       │    └─ 结果收集
       │
       ├─ 最终合并输出
       │
       └─ 后处理
            ├─ ConversationLogger 持久化对话
            └─ UseMemory 提取/更新记忆
```

## 七、详细子文档索引

| 文档 | 内容 |
|------|------|
| [核心模块详解与模块间调用关系](core-modules.md) | LLM调用层、工具系统、技能系统、记忆系统、命令系统详解 + 模块间调用关系图 |
| [核心执行流程与Agent初始化](execution-flow.md) | 三阶段执行流程、Agent初始化调用关系图、子任务隔离机制、工具结果压缩等 |
| [Agent 初始化详解](agent-initialization.md) | 入口文件关系、模型名称解析、15步初始化流程、目录解析、首次部署、时序图 |
| [CLI 入口线程架构详解](cli-thread-architecture.md) | 主线程/Invoke后台线程/心跳线程/Loop首次执行线程的创建、协作、生命周期管理 |
| [心跳定时任务详解](heartbeat.md) | 心跳用途、工作机制、执行流程、Loop Skill确定性回放、用户交互方式 |
| [模型 API Key 配置](model-apikey.md) | 5大模型系列环境变量映射、4种配置方式、共享API Key的模型列表 |
| [命令行参数配置](cli-params.md) | --model/--sub-model参数说明、优先级规则、入口文件对应关系 |
