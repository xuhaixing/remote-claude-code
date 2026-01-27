"""
飞书长连接方式接收消息

使用官方 SDK 的 WebSocket 长连接，无需公网域名
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
load_dotenv()  # 必须在导入其他模块之前加载

import json
import logging
import threading

import lark_oapi as lark
from lark_oapi.adapter.flask import *
from lark_oapi.api.im.v1 import *

from src.claude_code import chat_sync
from src.feishu_utils.feishu_utils import send_message
from src.data_base_utils import get_session, save_session

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def chat_with_claude(chat_id: str, message: str) -> str:
    """
    调用 Claude Code，基于 chat_id 保持对话连续性
    """
    # 从 SQLite 获取之前的 session_id
    session_id = get_session(chat_id)
    
    # 调用 Claude
    reply, new_session_id = chat_sync(message, session_id=session_id)
    
    # 保存到 SQLite
    if new_session_id != session_id:
        save_session(chat_id, new_session_id)
        logger.info(f"会话映射: {chat_id[:8]}... -> {new_session_id[:8]}...")
    
    return reply


def handle_message(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """处理接收到的消息"""
    try:
        event = data.event
        message = event.message
        
        # 解析消息内容
        content = json.loads(message.content)
        text = content.get("text", "")
        
        # 去掉 @机器人
        if message.mentions:
            for mention in message.mentions:
                text = text.replace(f"@{mention.name}", "").strip()
        
        if not text:
            return
        
        chat_id = message.chat_id
        logger.info(f"收到消息: {message.message_id}: {text}")
        
        # 异步线程处理，避免飞书超时重试
        def process_async():
            try:
                reply = chat_with_claude(chat_id, text)
                send_message(chat_id, reply)
                logger.info(f"回复: {reply[:100]}...")
            except Exception as e:
                logger.error(f"异步处理失败: {e}")
        
        threading.Thread(target=process_async, daemon=True).start()
        
    except Exception as e:
        logger.error(f"处理消息失败: {e}")


def main():
    # 创建客户端
    client = lark.ws.Client(
        APP_ID,
        APP_SECRET,
        event_handler=lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(handle_message)
            .build(),
        log_level=lark.LogLevel.INFO,
    )
    
    logger.info("启动飞书长连接...")
    client.start()


if __name__ == "__main__":
    main()
