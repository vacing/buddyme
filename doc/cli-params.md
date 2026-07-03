# 命令行参数配置

本文档描述 `cli.py` 和 `main.py` 的命令行参数支持、优先级规则以及入口文件对应关系。

## 一、参数说明

| 参数 | 短选项 | 类型 | 说明 |
|------|--------|------|------|
| `--model` | `-m` | str | 主模型名称，覆盖环境变量 `BUDDYME_MODEL` |
| `--sub-model` | `-s` | str | 子任务模型名称，覆盖环境变量 `BUDDYME_SUB_MODEL` |

## 二、优先级规则

```
命令行参数 > 环境变量 > 默认值 (glm_code_plan)
```

## 三、使用示例

```bash
# 通过命令行参数指定模型
python buddyMe/main.py --model deepseek --sub-model glm_code_plan

# 使用短选项
python buddyMe/main.py -m deepseek -s mimo

# CLI 入口同样支持
buddyme --model deepseek --sub-model mimo

# 不传参数时，回退到环境变量或默认值
python buddyMe/main.py
```

## 四、入口文件对应关系

| 启动方式 | 入口文件 | 参数支持 | UI 风格 |
|----------|----------|----------|---------|
| `python buddyMe/main.py` | `main.py` | `--model`, `--sub-model` | 原生 print（简洁） |
| `python -m buddyMe` | `__main__.py` → `cli.py` | `--model`, `--sub-model` | Rich（彩色+spinner） |
| `buddyme` | `cli.py` | `--model`, `--sub-model` | Rich（彩色+spinner） |

`cli.py` 是 `main.py` 的**增强版生产包装**，包裹了相同的 Agent 核心逻辑，但增加了 Rich UI、多线程 spinner、优雅退出等生产级特性。
