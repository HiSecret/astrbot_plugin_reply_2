from astrbot.api.all import *
from astrbot.api.event.filter import command, permission_type, event_message_type, EventMessageType, PermissionType
from astrbot.api.star import StarTools
from astrbot.api import logger
import json
import os


@register(
    name="reply",
    desc="自定义关键词回复。",
    version="v1.0",
    author="yahaya",
    repo="https://github.com/yahayao/astrbot_plugin_reply"
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

    @command("添加自定义回复")
    @permission_type(PermissionType.ADMIN)
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

    @command("查看自定义回复")
    async def list_replies(self, event: AstrMessageEvent):
        """查看所有关键词回复"""
        if not self.keyword_map:
            yield event.plain_result("暂无自定义回复")
            return
        msg = "当前关键词回复列表：\n" + "\n".join(
            [f"{i+1}. [{k}] -> {v}" for i, (k, v) in enumerate(self.keyword_map.items())]
        )
        yield event.plain_result(msg)

    @command("删除自定义回复")
    @permission_type(PermissionType.ADMIN)
    async def delete_reply(self, event: AstrMessageEvent, keyword: str):
        """/删除自定义回复 关键字 """
        keyword = keyword.strip().lower()
        if keyword not in self.keyword_map:
            yield event.plain_result(f"❌ 未找到关键词：{keyword}")
            return
        del self.keyword_map[keyword]
        self._save_config(self.keyword_map)
        yield event.plain_result(f"✅ 已删除关键词：{keyword}")

    @event_message_type(EventMessageType.ALL)
    async def handle_message(self, event: AstrMessageEvent):
        # 检查是否被@
        if not event.is_at_or_wake_command:
            return
        
        msg = event.message_str.strip().lower()
        # 只进行精确匹配
        if reply := self.keyword_map.get(msg):
            yield event.plain_result(reply)
            return
        # 移除了包含匹配的部分