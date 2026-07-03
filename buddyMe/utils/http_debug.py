#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
http_debug.py — HTTP 请求/响应调试打印 & 文件日志工具

通过环境变量 BUDDYME_HTTP_DEBUG 控制：
  - 设置为 "1" / "true" / "yes" / "on" 启用格式化打印 + 文件日志
  - 未设置或为其他值则禁用（零开销）

日志文件：
  - 保存在项目工作空间下的 log/ 目录
  - 文件名格式：<conversation_id>.log
  - 每次对话（invoke）开始时调用 start_conversation() 生成新 ID

打印内容：
  - 请求：方法、URL、请求头（API Key 脱敏）、请求体（JSON 格式化）
  - 响应：状态码、响应体（JSON 格式化）、耗时
  - 超长内容自动截断，保留首尾部分

使用方式：
  # 启用
  export BUDDYME_HTTP_DEBUG=1
  python buddyMe/main.py

  # 禁用（默认）
  python buddyMe/main.py
"""

import json
import os
import logging
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 模块加载时一次性读取环境变量，避免每次请求都查
_DEBUG_ENABLED = os.environ.get("BUDDYME_HTTP_DEBUG", "").lower() in ("1", "true", "yes", "on")

# 单次打印的最大字符数，超出部分自动截断
_MAX_PRINT_LENGTH = 100000

# ===================== 对话级文件日志管理 =====================

# 线程安全的当前对话 ID 和日志文件句柄
_lock = threading.Lock()
_current_conversation_id: str = ""
_log_file = None
_log_dir: Path = Path.cwd() / "log"


def set_log_dir(log_dir: str):
    """设置日志输出目录（通常在 Agent 初始化时调用一次）

    Args:
        log_dir: 日志目录的绝对路径
    """
    global _log_dir
    _log_dir = Path(log_dir)


def start_conversation(conversation_id: str = ""):
    """开始一次新对话，生成对话 ID 并打开日志文件

    Args:
        conversation_id: 可选，外部指定的对话 ID。
                         若为空则自动生成格式：YYYYMMDD_HHMMSS_<4位序号>
    """
    if not _DEBUG_ENABLED:
        return

    global _current_conversation_id, _log_file

    if not conversation_id:
        conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{os.getpid()}"

    with _lock:
        # 关闭上一个日志文件
        if _log_file and not _log_file.closed:
            _log_file.close()

        _current_conversation_id = conversation_id
        _log_dir.mkdir(parents=True, exist_ok=True)
        log_path = _log_dir / f"{conversation_id}.log"
        _log_file = open(log_path, "a", encoding="utf-8")
        _log_file.write(f"# Conversation: {conversation_id}\n")
        _log_file.write(f"# Started: {datetime.now().isoformat()}\n")
        _log_file.write("=" * 60 + "\n\n")
        _log_file.flush()


def end_conversation() -> str:
    """结束当前对话，关闭日志文件

    Returns:
        日志文件的绝对路径（如果写了日志），否则返回空字符串
    """
    if not _DEBUG_ENABLED:
        return ""

    global _log_file
    log_path = ""
    with _lock:
        if _log_file and not _log_file.closed:
            log_path = _log_file.name
            _log_file.write(f"\n# Ended: {datetime.now().isoformat()}\n")
            _log_file.close()
            _log_file = None
    return log_path


def get_current_conversation_id() -> str:
    """获取当前对话 ID"""
    return _current_conversation_id


def _write_to_log(content: str):
    """将内容写入当前对话的日志文件（线程安全）"""
    with _lock:
        if _log_file and not _log_file.closed:
            _log_file.write(content)
            _log_file.flush()


# ===================== 工具函数 =====================

def is_http_debug_enabled() -> bool:
    """检查是否启用了 HTTP 调试打印"""
    return _DEBUG_ENABLED


def _mask_sensitive_headers(headers: dict) -> dict:
    """脱敏处理请求头中的敏感字段（API Key 等）"""
    masked = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in ("authorization", "x-api-key", "api-key"):
            if isinstance(value, str) and len(value) > 12:
                masked[key] = value[:8] + "****" + value[-4:]
            else:
                masked[key] = "****"
        else:
            masked[key] = value
    return masked


def _truncate(content: str, max_length: int = _MAX_PRINT_LENGTH) -> str:
    """截断过长内容，保留首尾部分，中间用省略标注"""
    if len(content) <= max_length:
        return content
    half = max_length // 2
    return (
        content[:half]
        + f"\n... [truncated {len(content) - max_length} chars] ...\n"
        + content[-half:]
    )


def _output(text: str):
    """同时输出到终端和日志文件"""
    # print(text)
    _write_to_log(text + "\n")


# ===================== 核心调试函数 =====================

def http_debug_request(
    method: str,
    url: str,
    headers: dict,
    payload: dict,
    model_name: str = "",
):
    """格式化打印 HTTP 请求信息

    Args:
        method: HTTP 方法（POST / GET 等）
        url: 请求 URL
        headers: 请求头字典（自动脱敏）
        payload: 请求体字典
        model_name: 模型名称，用于标识来源
    """
    if not _DEBUG_ENABLED:
        return

    _output("\n" + "=" * 60)
    _output(f"  HTTP REQUEST  [{model_name}]  {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    _output("=" * 60)
    _output(f"  {method} {url}")
    _output(f"\n  Headers (sensitive fields masked):")
    _output(json.dumps(_mask_sensitive_headers(headers), indent=2, ensure_ascii=False))

    payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
    _output(f"\n  Payload ({len(payload_str)} chars):")
    _output(_truncate(payload_str))
    _output("=" * 60 + "\n")


def http_debug_response(
    status_code: int,
    response_body,
    model_name: str = "",
    elapsed: float = 0.0,
):
    """格式化打印 HTTP 响应信息

    Args:
        status_code: HTTP 状态码
        response_body: 响应体（dict / str / 其他）
        model_name: 模型名称，用于标识来源
        elapsed: 请求耗时（秒）
    """
    if not _DEBUG_ENABLED:
        return

    _output("\n" + "=" * 60)
    _output(f"  HTTP RESPONSE  [{model_name}]  {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    _output("=" * 60)
    _output(f"  Status: {status_code}   Elapsed: {elapsed:.3f}s")

    if isinstance(response_body, dict):
        body_str = json.dumps(response_body, indent=2, ensure_ascii=False)
    elif isinstance(response_body, str):
        try:
            parsed = json.loads(response_body)
            body_str = json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            body_str = response_body
    else:
        body_str = str(response_body)

    _output(f"\n  Response Body ({len(body_str)} chars):")
    _output(_truncate(body_str))
    _output("=" * 60 + "\n")