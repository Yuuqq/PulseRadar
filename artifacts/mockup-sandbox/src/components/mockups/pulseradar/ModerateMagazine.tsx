import React, { useState } from "react";
import { KEYWORD_STATS, META, PLATFORM_LABELS, type NewsTitle, type Platform, maxRank } from "./_data";
import { Clock } from "lucide-react";

type Lang = "en" | "zh";

const I18N: Record<Lang, {
  brand: string;
  tagline: string;
  separator: string;
  issue: string;
  signals: string;
  modeLabel: string;
  leadStory: string;
  trendingIndex: string;
  heatScore: string;
  resonance: string;
  platformActivity: string;
  newTag: string;
  noData: string;
  toggleTo: string;
}> = {
  en: {
    brand: "PulseRadar",
    tagline: "Today's Pulse",
    separator: "·",
    issue: "ISSUE NO.",
    signals: "SIGNALS",
    modeLabel: "Keyword Mode",
    leadStory: "Lead Story",
    trendingIndex: "Trending Index",
    heatScore: "Heat Score",
    resonance: "Resonance Trajectory",
    platformActivity: "Platform Activity",
    newTag: "New",
    noData: "No Data",
    toggleTo: "中",
  },
  zh: {
    brand: "脉搏雷达",
    tagline: "今日热点",
    separator: "·",
    issue: "第",
    signals: "信号数",
    modeLabel: "关键词模式",
    leadStory: "头条",
    trendingIndex: "趋势索引",
    heatScore: "热度",
    resonance: "热度轨迹",
    platformActivity: "平台活跃度",
    newTag: "新",
    noData: "暂无数据",
    toggleTo: "EN",
  },
};

const PLATFORM_COLORS: Record<Platform, { bg: string; text: string; border: string }> = {
  zhihu: { bg: "bg-[#f2f6ff]", text: "text-[#0052cc]", border: "border-[#d9e6ff]" },
  weibo: { bg: "bg-[#fff5ee]", text: "text-[#cc4d00]", border: "border-[#ffe6d9]" },
  "36kr": { bg: "bg-[#f0f7f4]", text: "text-[#006644]", border: "border-[#d9f2e6]" },
  huxiu: { bg: "bg-[#fffaf0]", text: "text-[#b37700]", border: "border-[#ffeed9]" },
  douyin: { bg: "bg-[#f2f2f2]", text: "text-[#1a1a1a]", border: "border-[#e6e6e6]" },
  baidu: { bg: "bg-[#f2f4fc]", text: "text-[#0033b3]", border: "border-[#d9e0f2]" },
  tieba: { bg: "bg-[#f5f8ff]", text: "text-[#1a55cc]", border: "border-[#e6eeff]" },
  bilibili: { bg: "bg-[#fff0f5]", text: "text-[#cc3366]", border: "border-[#ffe6ee]" },
  toutiao: { bg: "bg-[#fff2f2]", text: "text-[#cc0000]", border: "border-[#ffe6e6]" },
  v2ex: { bg: "bg-[#f7f7f7]", text: "text-[#4d4d4d]", border: "border-[#ebebeb]" },
};

function EditorialSparkline({ ranks, color = "#1a1a1a", strokeWidth = 1.5, height = 40, noDataLabel }: { ranks: (number | null)[], color?: string, strokeWidth?: number, height?: number, noDataLabel: string }) {
  const width = 200;
  const maxR = maxRank(ranks);

  const points = ranks
    .map((r, i) => {
      if (r === null) return null;
      const x = (i / (ranks.length - 1)) * width;
      const y = 4 + ((r - 1) / (maxR > 1 ? maxR - 1 : 1)) * (height - 8);
      return `${x},${y}`;
    })
    .filter(Boolean);

  if (points.length === 0) {
    return <div style={{ width, height }} className="border-t border-b border-[#e5e0d8] flex items-center justify-center text-xs text-[#a39e93]">{noDataLabel}</div>;
  }

  const d = `M ${points.join(" L ")}`;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible" preserveAspectRatio="none">
      <path d={d} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="square" strokeLinejoin="miter" />
      {ranks.map((r, i) => {
        if (r === null) return null;
        const x = (i / (ranks.length - 1)) * width;
        const y = 4 + ((r - 1) / (maxR > 1 ? maxR - 1 : 1)) * (height - 8);
        if (i === ranks.length - 1) {
          return <circle key={i} cx={x} cy={y} r="3" fill={color} />;
        }
        return <circle key={i} cx={x} cy={y} r="1.5" fill={color} />;
      })}
    </svg>
  );
}

export default function ModerateMagazine() {
  const [lang, setLang] = useState<Lang>("en");
  const t = I18N[lang];
  const leadKeyword = KEYWORD_STATS[0];
  const secondaryKeywords = KEYWORD_STATS.slice(1, 5);

  return (
    <div className="min-h-screen bg-[#fbf9f4] text-[#1a1a1a] selection:bg-[#c13a2e] selection:text-white pb-20">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700;900&display=swap');
        
        .font-editorial {
          font-family: 'Playfair Display', 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', serif;
        }
        .font-editorial-cn {
          font-family: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', serif;
        }
        .font-sans-editorial {
          font-family: 'Inter', -apple-system, sans-serif;
        }
        .border-ink { border-color: #1a1a1a; }
        .border-hairline { border-color: #e5e0d8; }
        .text-crimson { color: #c13a2e; }
        .bg-crimson { background-color: #c13a2e; }
        
        .magazine-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.8fr) minmax(0, 1fr);
          gap: 2.5rem;
        }
        @media (max-width: 768px) {
          .magazine-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>

      {/* Lang toggle (fixed, top-right) */}
      <button
        onClick={() => setLang(lang === "en" ? "zh" : "en")}
        className="fixed top-4 right-4 z-50 border border-ink bg-white/90 backdrop-blur px-3 py-1.5 text-[11px] font-sans-editorial font-bold uppercase tracking-widest hover:bg-ink hover:text-[#fbf9f4] transition-colors"
        aria-label="Toggle language"
      >
        {t.toggleTo}
      </button>

      {/* Header */}
      <header className="max-w-[1200px] mx-auto px-6 pt-12 pb-6">
        <div className="border-b-[3px] border-ink pb-6 flex flex-col items-center justify-center relative">
          <div className="absolute left-0 top-1/2 -translate-y-1/2 hidden md:block">
            <div className="text-[11px] uppercase tracking-widest font-sans-editorial text-[#555] font-semibold">
              {META.time_str}
            </div>
            <div className="text-[11px] uppercase tracking-widest font-sans-editorial text-[#555]">
              {t.issue} {META.hot_news_count}
            </div>
          </div>

          <h1 className={`text-5xl md:text-6xl ${lang === "zh" ? "font-editorial-cn" : "font-editorial"} font-black tracking-tight text-center`}>
            {t.brand} <span className="text-crimson font-serif mx-2">{t.separator}</span> {t.tagline}
          </h1>

          <div className="absolute right-0 top-1/2 -translate-y-1/2 hidden md:block text-right">
            <div className="text-[11px] uppercase tracking-widest font-sans-editorial text-[#555] font-semibold">
              {t.signals}: {META.total_titles}
            </div>
            <div className="text-[11px] uppercase tracking-widest font-sans-editorial text-[#555]">
              {t.modeLabel}
            </div>
          </div>
        </div>
        <div className="flex md:hidden justify-between items-center py-3 border-b border-ink">
           <div className="text-[10px] uppercase tracking-widest font-sans-editorial text-[#555]">
             {META.time_str}
           </div>
           <div className="text-[10px] uppercase tracking-widest font-sans-editorial text-[#555]">
             {t.signals}: {META.total_titles}
           </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1200px] mx-auto px-6 mt-4">
        <div className="magazine-grid">
          
          {/* LEFT: Lead Feature */}
          <article className="flex flex-col">
            <div className="mb-4 flex items-baseline gap-4 border-b border-hairline pb-4">
              <span className="text-crimson text-[11px] font-sans-editorial font-bold uppercase tracking-[0.2em]">{t.leadStory}</span>
              <div className="flex-1 h-px bg-hairline hidden sm:block"></div>
            </div>
            
            <div className="flex gap-6 items-start mb-8">
              <div className="text-8xl font-editorial font-black leading-none tracking-tighter text-[#1a1a1a] -ml-1">
                01<span className="text-crimson text-5xl align-top">.</span>
              </div>
              <div className="pt-2">
                <h2 className={`text-4xl md:text-5xl ${lang === "zh" ? "font-editorial-cn" : "font-editorial"} font-bold leading-[1.1] mb-3`}>
                  {leadKeyword.word}
                </h2>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-sans-editorial font-semibold bg-ink text-[#fbf9f4] px-2 py-0.5">
                    {t.heatScore}: {leadKeyword.count}
                  </span>
                  <div className="flex items-center gap-1">
                    {Array.from(new Set(leadKeyword.titles.flatMap(t => t.hits))).slice(0, 5).map(platform => (
                      <span key={platform} className="text-[10px] font-sans-editorial font-bold border border-ink px-1 py-0.5">
                        {PLATFORM_LABELS[platform]}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6 flex-1">
              {leadKeyword.titles.map((title, idx) => (
                <div key={idx} className="group relative">
                  <div className="absolute -left-6 top-1 text-crimson opacity-0 group-hover:opacity-100 transition-opacity font-serif text-2xl leading-none">
                    "
                  </div>
                  <h3 className={`text-2xl ${lang === "zh" ? "font-editorial-cn" : "font-editorial"} font-semibold leading-snug mb-3`}>
                    <a href={title.url} className="hover:text-crimson transition-colors decoration-1 underline-offset-4 decoration-hairline group-hover:underline">
                      {title.title}
                    </a>
                  </h3>
                  <div className="flex items-center gap-3 font-sans-editorial">
                    <span className="text-xs font-bold uppercase tracking-wider text-crimson">
                      {PLATFORM_LABELS[title.source]}
                    </span>
                    <span className="text-xs text-[#666] flex items-center gap-1">
                      <Clock size={12} strokeWidth={2} />
                      {title.time_display}
                    </span>
                    {title.is_new && (
                      <span className="text-[9px] font-bold uppercase tracking-widest border border-crimson text-crimson px-1">
                        {t.newTag}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-10 pt-6 border-t border-hairline">
              <div className="text-[10px] font-sans-editorial font-bold uppercase tracking-widest text-[#666] mb-3">
                {t.resonance}
              </div>
              <div className="h-[60px] w-full border border-hairline p-2 bg-white/50">
                {leadKeyword.titles[0] && <EditorialSparkline ranks={leadKeyword.titles[0].ranks} color="#c13a2e" height={44} strokeWidth={2} noDataLabel={t.noData} />}
              </div>
            </div>
          </article>

          {/* RIGHT: Secondary Stories */}
          <aside className="border-l border-hairline pl-0 md:pl-10 pb-8 flex flex-col">
            <div className="mb-6 flex items-baseline gap-4 border-b border-hairline pb-4">
              <span className="text-ink text-[11px] font-sans-editorial font-bold uppercase tracking-[0.2em]">{t.trendingIndex}</span>
            </div>

            <div className="flex flex-col gap-8">
              {secondaryKeywords.map((kw, idx) => (
                <article key={kw.word} className="relative">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className={`text-xl ${lang === "zh" ? "font-editorial-cn" : "font-editorial"} font-bold flex items-center gap-2`}>
                      <span className="text-crimson text-sm font-sans-editorial font-black">
                        {String(idx + 2).padStart(2, '0')}
                      </span>
                      {kw.word}
                    </h3>
                    <div className="text-sm font-sans-editorial font-bold border-b-2 border-ink">
                      {kw.count}
                    </div>
                  </div>
                  
                  <div className="space-y-4 mt-4">
                    {kw.titles.slice(0, 2).map((title, tIdx) => (
                      <div key={tIdx} className="pl-6 border-l border-hairline hover:border-ink transition-colors">
                        <a href={title.url} className={`block text-base ${lang === "zh" ? "font-editorial-cn" : "font-editorial"} font-medium leading-snug mb-1 hover:text-crimson transition-colors`}>
                          {title.title}
                        </a>
                        <div className="flex items-center gap-2 font-sans-editorial mt-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-[#555]">
                            {PLATFORM_LABELS[title.source]}
                          </span>
                          <span className="text-gray-300">|</span>
                          <span className="text-[10px] text-[#666]">
                            {title.time_display}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </aside>
        </div>
      </main>

      {/* Bottom Pulse Strip */}
      <section className="mt-16 border-t-2 border-b-2 border-ink py-2 bg-white">
        <div className="max-w-[1200px] mx-auto px-6">
          <div className="flex flex-wrap items-center justify-between gap-4 md:gap-2">
            <div className="text-[10px] font-sans-editorial font-bold uppercase tracking-[0.2em] text-[#555] shrink-0">
              {t.platformActivity}
            </div>
            <div className="flex-1 flex flex-wrap justify-end gap-x-6 gap-y-2">
              {Object.entries(PLATFORM_LABELS).map(([key, label]) => {
                const conf = PLATFORM_COLORS[key as Platform] || { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-200' };
                const totalHits = KEYWORD_STATS.reduce((sum, kw) =>
                  sum + kw.titles.filter(t => t.hits.includes(key as Platform)).length, 0
                );

                if (totalHits === 0) return null;

                return (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-[10px] font-sans-editorial font-bold uppercase tracking-wider text-[#1a1a1a]">
                      {label}
                    </span>
                    <div className="flex gap-0.5">
                      {Array.from({ length: totalHits }).map((_, i) => (
                        <div key={i} className="w-1.5 h-3 bg-ink"></div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
