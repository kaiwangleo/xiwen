import re

CHAT_REPLY = (
    "我是析问，只负责把业务问题转成数仓查询，不会闲聊。\n"
    "可以直接问销售额、客单价、销量排行，例如：「统计去年各地区的销售总额」。"
)

# 明显是问数：即使带「你能」也走标准流程
_DATA_HINT = re.compile(
    r"(统计|查询|查一下|看看|多少|总额|销量|销售|金额|GMV|AOV|客单价|"
    r"排行|排名|平均|同比|环比|去年|今年|各地区|会员|商品|品类|省份|地区|"
    r"订单|成交|品牌|零食|黄金|白银|钻石)",
    re.I,
)

# 整句是寒暄 / 能力 / 身份，才拦截
_CHAT = re.compile(
    r"^("
    r"你好|您好|嗨|哈喽|hi+|hello|hey|"
    r"你是谁|你是什么|你叫什么|你是啥|"
    r"你能做什么|你能干什么|你会什么|你会干什么|"
    r"你有什么功能|你有什么能力|你可以做什么|"
    r"能做什么|会什么|干什么用的|有什么用|"
    r"怎么用|如何使用|使用说明|帮助|help|"
    r"谢谢|感谢|再见|拜拜|bye"
    r")[\s！!？?。.～~]*$",
    re.I,
)


def is_data_query(query: str) -> bool:
    """业务关键词优先走问数；整句寒暄才当闲聊。"""
    text = (query or "").strip()
    if not text:
        return False
    if _DATA_HINT.search(text):
        return True
    return not _CHAT.match(text)


def chat_reply() -> str:
    """闲聊固定回复，不调大模型。"""
    return CHAT_REPLY
