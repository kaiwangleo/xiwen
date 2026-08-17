/** 与后端 app.agent.intent 重复，前端短路闲聊以免打 API。本轮不删。 */

const DATA_HINT =
  /(统计|查询|查一下|看看|多少|总额|销量|销售|金额|GMV|AOV|客单价|排行|排名|平均|同比|环比|去年|今年|各地区|会员|商品|品类|省份|地区|订单|成交|品牌|零食|黄金|白银|钻石)/i;

const CHAT =
  /^(你好|您好|嗨|哈喽|hi+|hello|hey|你是谁|你是什么|你叫什么|你是啥|你能做什么|你能干什么|你会什么|你会干什么|你有什么功能|你有什么能力|你可以做什么|能做什么|会什么|干什么用的|有什么用|怎么用|如何使用|使用说明|帮助|help|谢谢|感谢|再见|拜拜|bye)[\s！!？?。.～~]*$/i;

export const CHAT_REPLY =
  "我是析问，只负责把业务问题转成数仓查询，不会闲聊。\n可以直接问销售额、客单价、销量排行，例如：「统计去年各地区的销售总额」。";

/** 业务关键词优先问数；整句寒暄才本地回复。 */
export function isDataQuery(query) {
  const text = (query || "").trim();
  if (!text) return false;
  if (DATA_HINT.test(text)) return true;
  return !CHAT.test(text);
}
