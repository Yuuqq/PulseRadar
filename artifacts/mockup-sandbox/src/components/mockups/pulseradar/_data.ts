export type Platform =
  | "zhihu" | "weibo" | "36kr" | "huxiu" | "douyin" | "baidu" | "tieba" | "bilibili" | "toutiao" | "v2ex";

export const PLATFORM_LABELS: Record<Platform, string> = {
  zhihu: "知乎", weibo: "微博", "36kr": "36氪", huxiu: "虎嗅",
  douyin: "抖音", baidu: "百度", tieba: "贴吧", bilibili: "B站",
  toutiao: "今日头条", v2ex: "V2EX",
};

export interface NewsTitle {
  title: string;
  source: Platform;
  ranks: (number | null)[];
  hits: Platform[];
  time_display: string;
  is_new: boolean;
  url: string;
}

export interface KeywordStat {
  word: string;
  count: number;
  titles: NewsTitle[];
}

export interface ReportMeta {
  mode_label: string;
  total_titles: number;
  hot_news_count: number;
  time_str: string;
  failed_ids: string[];
  generated_at: string;
}

export const META: ReportMeta = {
  mode_label: "关键词模式",
  total_titles: 1842,
  hot_news_count: 47,
  time_str: "2026-05-03 14:20",
  failed_ids: ["weibo-realtime"],
  generated_at: "刚刚",
};

export const KEYWORD_STATS: KeywordStat[] = [
  {
    word: "DeepSeek",
    count: 9,
    titles: [
      {
        title: "DeepSeek 发布 V4 模型，推理成本再降 80%，部分指标超越 GPT-5",
        source: "36kr",
        ranks: [12, 8, 5, 3, 2, 1, 1, 1, 2, 3],
        hits: ["36kr", "huxiu", "zhihu", "weibo", "v2ex"],
        time_display: "08:42",
        is_new: true,
        url: "#",
      },
      {
        title: "如何评价 DeepSeek V4 的开源策略？社区一片沸腾",
        source: "zhihu",
        ranks: [null, null, 22, 14, 9, 6, 4, 3, 4, 5],
        hits: ["zhihu", "v2ex", "bilibili"],
        time_display: "10:15",
        is_new: true,
        url: "#",
      },
      {
        title: "实测 DeepSeek V4：本地部署完整指南",
        source: "bilibili",
        ranks: [null, null, null, null, 18, 12, 8, 7, 6, 6],
        hits: ["bilibili", "v2ex"],
        time_display: "11:30",
        is_new: false,
        url: "#",
      },
    ],
  },
  {
    word: "以色列",
    count: 7,
    titles: [
      {
        title: "以色列空袭叙利亚南部，造成至少 12 人死亡",
        source: "weibo",
        ranks: [3, 2, 1, 1, 1, 2, 3, 4, 5, 7],
        hits: ["weibo", "toutiao", "baidu", "zhihu"],
        time_display: "06:20",
        is_new: false,
        url: "#",
      },
      {
        title: "联合国安理会就以色列局势召开紧急会议",
        source: "toutiao",
        ranks: [null, 15, 8, 5, 4, 3, 3, 4, 5, 6],
        hits: ["toutiao", "baidu", "weibo"],
        time_display: "09:05",
        is_new: false,
        url: "#",
      },
    ],
  },
  {
    word: "Apple Vision",
    count: 5,
    titles: [
      {
        title: "Apple Vision Pro 2 国行版定价 25999 元，618 首发",
        source: "huxiu",
        ranks: [null, 25, 16, 9, 5, 4, 4, 5, 6, 8],
        hits: ["huxiu", "36kr", "weibo", "zhihu"],
        time_display: "13:45",
        is_new: true,
        url: "#",
      },
      {
        title: "为什么 Vision Pro 2 砍掉了眼动追踪？",
        source: "zhihu",
        ranks: [null, null, null, 32, 21, 14, 10, 8, 7, 7],
        hits: ["zhihu", "v2ex"],
        time_display: "14:02",
        is_new: true,
        url: "#",
      },
    ],
  },
  {
    word: "高考",
    count: 4,
    titles: [
      {
        title: "2026 高考报名人数 1342 万，连续三年下降",
        source: "baidu",
        ranks: [8, 6, 4, 3, 2, 2, 3, 5, 8, 12],
        hits: ["baidu", "toutiao", "weibo", "zhihu"],
        time_display: "07:30",
        is_new: false,
        url: "#",
      },
    ],
  },
  {
    word: "比亚迪",
    count: 4,
    titles: [
      {
        title: "比亚迪 Q1 财报：净利润同比增长 47%，海外销量翻倍",
        source: "36kr",
        ranks: [null, null, 18, 11, 7, 5, 6, 8, 11, 15],
        hits: ["36kr", "huxiu", "weibo"],
        time_display: "12:00",
        is_new: false,
        url: "#",
      },
    ],
  },
  {
    word: "ChatGPT",
    count: 3,
    titles: [
      {
        title: "OpenAI 回应 DeepSeek：将提前发布 GPT-5 Turbo",
        source: "36kr",
        ranks: [null, null, null, null, null, 28, 19, 12, 9, 11],
        hits: ["36kr", "huxiu", "v2ex"],
        time_display: "13:20",
        is_new: true,
        url: "#",
      },
    ],
  },
];

export function maxRank(ranks: (number | null)[]): number {
  return Math.max(50, ...(ranks.filter((r): r is number => r !== null)));
}

export function resonanceScore(t: NewsTitle): number {
  return t.hits.length;
}
