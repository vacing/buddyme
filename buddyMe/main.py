"""buddyMe 本地开发入口"""

import argparse
import os
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    from buddyMe.agent_moudle import agent
except ImportError:
    from agent_moudle import agent

_SRC_DIR = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(description="buddyMe 本地开发模式")
parser.add_argument("--model", "-m", type=str, default=None,
                    help="主模型名称（覆盖环境变量 BUDDYME_MODEL）")
parser.add_argument("--sub-model", "-s", type=str, default=None,
                    help="子任务模型名称（覆盖环境变量 BUDDYME_SUB_MODEL）")
args = parser.parse_args()

model_name = args.model or os.environ.get("BUDDYME_MODEL", "glm_code_plan")
sub_model_name = args.sub_model or os.environ.get("BUDDYME_SUB_MODEL", "glm_code_plan")

print("=" * 60)
print("buddyMe — 本地开发模式")
print(f"源码目录: {_SRC_DIR}")
print(f"默认模型: {model_name}")
print("输入 /help 查看可用命令")
print("=" * 60)

ag = agent.AgentMain(model_name=model_name, sub_model_name=sub_model_name, data_dir=str(_SRC_DIR))

try:
    from buddyMe.tool_moudle.baidu_search_tool import BaiduSearchTool
except ImportError:
    from tool_moudle.baidu_search_tool import BaiduSearchTool
ag.register_tool(BaiduSearchTool())

while True:
    time.sleep(1)
    inp = input("query: ")
    reply = ag.invoke(inp)
    if reply:
        print(reply)
    if ag._last_cmd_should_exit:
        break
