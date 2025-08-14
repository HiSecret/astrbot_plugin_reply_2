from aiocqhttp import CQHttp
from astrbot.api.all import *
from astrbot.api.star import StarTools
from astrbot.api.event import filter
from astrbot.api import logger
from fuzzywuzzy import process
import json
import os
import asyncio


@register(
    name="reply",
    desc="自定义关键词回复-secret",
    version="v1.0",
    author="yahaya",
    repo="https://github.com/HiSecret/astrbot_plugin_reply"
)
class KeywordReplyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        plugin_data_dir = StarTools.get_data_dir("astrbot_plugin_reply")
        self.config_path = os.path.join(plugin_data_dir, "keyword_reply_config.json")
        self.keyword_map = self._load_config()
        logger.info(f"配置文件路径：{self.config_path}")

    def _load_config(self) -> dict:
        """加载本地配置文件"""
        try:
            if not os.path.exists(self.config_path):
                return {}
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"配置加载失败: {str(e)}")
            return {}

    def _save_config(self, data: dict):
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"配置保存失败: {str(e)}")

    @filter.command("添加自定义回复")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def add_reply(self, event: AstrMessageEvent):
        """/添加自定义回复 关键字|回复内容"""
        # 获取原始消息内容
        full_message = event.get_message_str()

        # 移除命令前缀部分
        command_prefix1 = "/添加自定义回复"
        command_prefix2 = "添加自定义回复 "
        # 去除命令前缀
        if full_message.startswith(command_prefix1):
            args = full_message[len(command_prefix1):].strip()
        elif full_message.startswith(command_prefix2):
            args = full_message[len(command_prefix2):].strip()
        else:
            yield event.plain_result("❌ 格式错误，请在消息前添加命令前缀：\"/添加自定义回复\"")
            return

        # 使用第一个"|"作为分隔符
        parts = args.split("|", 1)
        if len(parts) != 2:
            yield event.plain_result("❌ 格式错误，正确格式：/添加自定义回复 关键字|回复内容")
            return

        keyword = parts[0].strip()
        # 保留回复内容的原始格式，包括空格和换行
        reply = parts[1]
        print(f"keyword: {keyword}, reply: {reply}")

        if not keyword:
            yield event.plain_result("❌ 关键字不能为空")
            return

        self.keyword_map[keyword.lower()] = reply
        self._save_config(self.keyword_map)
        yield event.plain_result(f"✅ 已添加关键词回复： [{keyword}] -> {reply}")

    @filter.command("查看自定义回复")
    async def list_replies(self, event: AstrMessageEvent):
        """查看所有关键词回复"""
        if not self.keyword_map:
            yield event.plain_result("暂无自定义回复")
            return
        msg = "当前关键词回复列表：\n" + "\n".join(
            [f"{i + 1}. [{k}] -> {v}" for i, (k, v) in enumerate(self.keyword_map.items())]
        )
        yield event.plain_result(msg)

    @filter.command("删除自定义回复")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def delete_reply(self, event: AstrMessageEvent, keyword: str):
        """/删除自定义回复 关键字 """
        keyword = keyword.strip().lower()
        if keyword not in self.keyword_map:
            yield event.plain_result(f"❌ 未找到关键词：{keyword}")
            return
        del self.keyword_map[keyword]
        self._save_config(self.keyword_map)
        yield event.plain_result(f"✅ 已删除关键词：{keyword}")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_message(self, event: AstrMessageEvent):
        msg = event.message_str.strip().lower()
        reply = None

        try:
            # 精确匹配  
            if reply_match := self.keyword_map.get(msg):
                reply = reply_match
            else:
                match, score = process.extractOne(msg, self.keyword_map.keys())
                if score > 90:  # 相似度阈值  
                    reply = self.keyword_map[match]
        except Exception as e:
            logger.error(f"自动回复异常: {e}")
            reply = None

        logger.info(f"auto_reply: {str(reply)}")
        if reply:
            # 发送回复并获取机器人发送的消息对象
            response = yield event.plain_result(reply)
            # 检查是否为群消息，非群消息不处理
            group_id = event.get_group_id()
            logger.info(f"撤回消息group_id: {group_id}")
            if not group_id:
                return
            
            # 等待60秒后撤回机器人自己的消息
            await asyncio.sleep(60)

            try:
                self_id = int(event.get_self_id())
                # 从响应中获取机器人发送消息的message_id
                if hasattr(response, 'message_id'):
                    message_id = int(response.message_id)
                elif isinstance(response, dict) and 'message_id' in response:
                    message_id = int(response['message_id'])
                else:
                    logger.error("无法获取机器人发送消息的message_id")
                    return
                    
                logger.info(f"撤回消息self_id: {self_id}, message_id: {message_id}")
                await event.bot.delete_msg(message_id=message_id, self_id=self_id)
            except Exception as e:
                logger.error(f"撤回消息失败: {e}")
