# 模型 API Key 配置

本文档描述 buddyMe 所有模型的 API Key 配置方式、环境变量映射和优先级规则。

## 一、支持的模型及对应环境变量

| 模型系列 | 环境变量 | 配置示例 |
|----------|----------|----------|
| 智谱 GLM | `GLM_API_KEY` | `GLM_API_KEY=your_zhipu_api_key` |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API_KEY=your_deepseek_key` |
| 百度 ERNIE | `ERNIE_API_KEY` | `ERNIE_API_KEY=your_ernie_key` |
| 小米 MiMo | `MIMO_API_KEY` | `MIMO_API_KEY=your_mimo_key` |
| 通义千问 | `QWEN_API_KEY` | `QWEN_API_KEY=your_qwen_key` |

## 二、配置方式

### 方式一：`.env` 文件（推荐）

项目已集成 python-dotenv，在项目根目录创建 `.env` 文件：
```
GLM_API_KEY=你的智谱API密钥
DEEPSEEK_API_KEY=你的DeepSeek密钥
```

### 方式二：终端临时设置
```bash
export GLM_API_KEY="你的智谱API密钥"
python -m buddyMe
```

### 方式三：写入 shell 配置文件（永久生效）
```bash
echo 'export GLM_API_KEY="你的智谱API密钥"' >> ~/.bashrc
source ~/.bashrc
```

### 方式四：运行时动态设置
```python
ModelConfig.set_api_key("sub_agent_code_plan", "你的API密钥")
```

## 三、模型共享 API Key

以下模型配置共享同一个环境变量 `GLM_API_KEY`：

- `glm`
- `glm_code_plan`
- `sub_agent_code_plan`

只需设置一个 `GLM_API_KEY`，这三个模型配置即可同时生效。
