import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import hashlib
import base64
import logging
import os
from dotenv import load_dotenv
load_dotenv()

ENCRYPT_KEY = os.getenv("ENCRYPT_KEY")
assert ENCRYPT_KEY, 'ENCRYPT_KEY is required'

from Crypto.Cipher import AES
from src.feishu_utils.feishu_utils import reply_message, send_message
from src.claude_code import ConversationClient
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class  AESCipher(object):
    def __init__(self, key):
        self.bs = AES.block_size
        self.key=hashlib.sha256(AESCipher.str_to_bytes(key)).digest()
    @staticmethod
    def str_to_bytes(data):
        u_type = type(b"".decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data
    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]
    def decrypt(self, enc):
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return  self._unpad(cipher.decrypt(enc[AES.block_size:]))
    def decrypt_string(self, enc):
        enc = base64.b64decode(enc)
        return  self.decrypt(enc).decode('utf8')

# 处理实例
class HttpRequest(BaseHTTPRequestHandler):
    
    def _send_json(self, data):
        """返回 JSON 响应"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_GET(self):
        self._send_json({"status": "ok"})    
        
    async def chat(self, thread_id, message):
        async with ConversationClient(session_id=thread_id) as client:
            r = await client.chat(message)
            return r.content
        
    def handle_msg(self, msg, msg_id, open_id, chat_id):
        
        if len(msg) ==0:
            return '请输入正确命令'
        
        # 返回正在处理
        ret_msg = asyncio.run(self.chat(None, msg))
        # reply_message(msg_id, ret_msg)
        send_message(chat_id, ret_msg)
        logger.info(f'send_message:{msg_id} {ret_msg}')
        return
    
    def do_POST(self):
        data = self.rfile.read(int(self.headers['content-length']))
        data = data.decode()
        json_data = json.loads(data)
        
        # 获取明文（用 Encrypt Key 解密）
        cipher = AESCipher(ENCRYPT_KEY)
        paint_json = json.loads(cipher.decrypt_string(json_data['encrypt']))
        
        logger.info(f'get message:{json.dumps(paint_json, ensure_ascii=False, indent=4)}')
        
        # URL 验证请求 - 飞书配置时会发送
        if paint_json.get('type') == 'url_verification':
            challenge = paint_json.get('challenge', '')
            logger.info(f'URL verification, challenge: {challenge}')
            self._send_json({"challenge": challenge})
            return
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if 'event' not in paint_json:
            return
        content_json = json.loads(paint_json['event']['message']['content'])
        msg = content_json['text']
            
        # @全员不处理
        if '@_all' in msg:
            logger.info('@ 全员消息不处理')
            self.wfile.write(json.dumps({"status": "@ 全员消息不处理"}, ensure_ascii=False).encode())
            return
        
        # 对话模式        
        # 群发消息 去掉@对象
        if 'mentions' in paint_json['event']['message']:
            mentions = paint_json['event']['message']['mentions']
            for mention in mentions:
                key = mention['key']
                msg = msg.replace(f'{key} ', '')

        # 获取个人id
        open_id = paint_json['event']['sender']['sender_id']['open_id']
        chat_id  = paint_json['event']['message']['chat_id']

        msg_id = paint_json['event']['message']['message_id']
        self.handle_msg(msg, msg_id, open_id, chat_id)
    
        self.wfile.write(json.dumps(paint_json, ensure_ascii=False).encode())

if __name__=='__main__':
    host = ('0.0.0.0', 8000)
    server = HTTPServer(host, HttpRequest)
    logger.info(f'server start on {host}')
    server.serve_forever()