import React, { useMemo } from "react";
import { Activity, Clock, TrendingUp, AlertTriangle } from "lucide-react";
import { KEYWORD_STATS, META, PLATFORM_LABELS, type NewsTitle, type Platform, maxRank } from "./_data";

const PLATFORM_COLORS: Record<Platform, { bg: string; text: string }> = {
  zhihu: { bg: "bg-blue-100", text: "text-blue-700" },
  weibo: { bg: "bg-red-100", text: "text-red-700" },
  "36kr": { bg: "bg-blue-50", text: "text-blue-600" },
  huxiu: { bg: "bg-gray-100", text: "text-gray-800" },
  douyin: { bg: "bg-black", text: "text-white" },
  baidu: { bg: "bg-blue-100", text: "text-blue-800" },
  tieba: { bg: "bg-blue-50", text: "text-blue-600" },
  bilibili: { bg: "bg-pink-100", text: "text-pink-600" },
  toutiao: { bg: "bg-red-50", text: "text-red-600" },
  v2ex: { bg: "bg-gray-200", text: "text-gray-700" },
};

function Sparkline({ ranks, color = "#f59e0b" }: { ranks: (number | null)[]; color?: string }) {
  const width = 60;
  const height = 20;
  const maxR = maxRank(ranks);
  
  const points = ranks
    .map((r, i) => {
      if (r === null) return null;
      const x = (i / (ranks.length - 1)) * width;
      const y = 2 + ((r - 1) / (maxR > 1 ? maxR - 1 : 1)) * (height - 4);
      return `${x},${y}`;
    })
    .filter(Boolean);

  if (points.length === 0) {
    return <div className="w-[60px] h-[20px] bg-gray-50 rounded flex items-center justify-center text-[10px] text-gray-400">--</div>;
  }

  const d = `M ${points.join(" L ")}`;
  const lastPoint = points[points.length - 1]?.split(",") || [0, 0];

  return (
    <svg width={width} height={height} className="overflow-visible">
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lastPoint[0]} cy={lastPoint[1]} r="2" fill={color} />
    </svg>
  );
}

export default function ModerateTimeline() {
  const { timelineGroups, topKeywords } = useMemo(() => {
    const allTitles: (NewsTitle & { keyword: string })[] = [];
    KEYWORD_STATS.forEach(stat => {
      stat.titles.forEach(t => allTitles.push({ ...t, keyword: stat.word }));
    });

    const groups = new Map<string, typeof allTitles>();
    allTitles.forEach(t => {
      const hour = t.time_display.split(":")[0] + ":00";
      if (!groups.has(hour)) groups.set(hour, []);
      groups.get(hour)!.push(t);
    });

    const sortedGroups = Array.from(groups.entries())
      .sort((a, b) => b[0].localeCompare(a[0]))
      .map(([hour, titles]) => ({
        hour,
        titles: titles.sort((a, b) => b.time_display.localeCompare(a.time_display))
      }));

    const topKeywords = [...KEYWORD_STATS]
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return { timelineGroups: sortedGroups, topKeywords };
  }, []);

  return (
    <div className="min-h-screen flex flex-col font-sans bg-[#f7f8fa] text-gray-900">
      <style>{`
        .moment-card { transition: transform 0.2s, box-shadow 0.2s; }
        .moment-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); }
      `}</style>
      
      {/* Header - Intensity Ribbon */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-20 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500 text-white flex items-center justify-center">
              <Activity size={18} />
            </div>
            <h1 className="text-xl font-bold tracking-tight">Pulse<span className="text-amber-500">Radar</span></h1>
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded font-medium">{META.mode_label}</span>
          </div>
          
          <div className="flex-1 max-w-lg mx-8 h-10 flex items-end">
            <div className="w-full h-full relative flex items-end opacity-50">
                <svg viewBox="0 0 100 20" preserveAspectRatio="none" className="w-full h-full">
                  <path d="M0,20 L0,15 Q10,5 20,12 T40,10 T60,18 T80,8 T100,5 L100,20 Z" fill="#fcd34d" opacity="0.3" />
                  <path d="M0,15 Q10,5 20,12 T40,10 T60,18 T80,8 T100,5" fill="none" stroke="#f59e0b" strokeWidth="1" />
                </svg>
                <div className="absolute right-[10%] top-0 bottom-0 border-l border-amber-500 border-dashed">
                  <div className="absolute top-0 -translate-x-1/2 -translate-y-1/2 w-2 h-2 bg-amber-500 rounded-full" />
                </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4 text-sm text-gray-500 font-medium">
             <div className="flex items-center gap-1"><span className="text-gray-900">{META.total_titles}</span> 采集</div>
             <div className="flex items-center gap-1"><span className="text-amber-600">{META.hot_news_count}</span> 命中</div>
             <div className="flex items-center gap-1"><Clock size={14} /> {META.time_str}</div>
          </div>
        </div>
      </div>

      {/* Main Layout */}
      <div className="flex flex-1 max-w-7xl mx-auto w-full">
        
        {/* Left Rail & Main Column */}
        <div className="flex-1 flex px-6 py-8">
          
          {/* Left Rail - Timeline */}
          <div className="w-24 shrink-0 relative mr-6">
            <div className="absolute top-0 bottom-0 right-4 w-px bg-gray-200" />
            <div className="space-y-12">
              {timelineGroups.map((group, i) => (
                <div key={group.hour} className="relative pr-8 text-right h-12">
                  <span className={`text-sm font-bold ${i === 0 ? 'text-amber-600' : 'text-gray-400'}`}>
                    {group.hour}
                  </span>
                  <div className={`absolute top-1.5 -right-[5px] w-3 h-3 rounded-full border-2 border-white ${i === 0 ? 'bg-amber-500 shadow-[0_0_0_3px_rgba(245,158,11,0.2)]' : 'bg-gray-300'}`} />
                </div>
              ))}
            </div>
          </div>

          {/* Main Column - Moment Cards */}
          <div className="flex-1 max-w-3xl space-y-12">
            {timelineGroups.map((group, i) => (
              <div key={group.hour} className="space-y-4">
                {group.titles.map((title, j) => (
                  <div key={j} className="moment-card bg-white p-5 rounded-xl border border-gray-100 shadow-sm relative">
                    {title.is_new && i === 0 && (
                      <div className="absolute -left-1 top-6 w-1 h-8 bg-amber-500 rounded-r" />
                    )}
                    
                    <div className="flex justify-between items-start gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                           <span className="text-xs font-semibold text-gray-500">{title.time_display}</span>
                           <span className="text-xs font-bold text-gray-900 bg-gray-100 px-2 py-0.5 rounded">{title.keyword}</span>
                           {title.is_new && <span className="text-[10px] font-bold text-white bg-amber-500 px-1.5 py-0.5 rounded uppercase">NEW</span>}
                        </div>
                        <a href={title.url} className="text-lg font-bold text-gray-900 leading-snug hover:text-amber-600 transition-colors">
                          {title.title}
                        </a>
                        <div className="flex flex-wrap items-center gap-2 mt-4">
                          {title.hits.map(hit => {
                            const conf = PLATFORM_COLORS[hit] || { bg: "bg-gray-100", text: "text-gray-600" };
                            return (
                              <span key={hit} className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${conf.bg} ${conf.text}`}>
                                {PLATFORM_LABELS[hit] || hit}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                      
                      <div className="shrink-0 flex flex-col items-end gap-1 bg-gray-50 p-2 rounded-lg border border-gray-100">
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Trend</span>
                        <Sparkline ranks={title.ranks} color={title.is_new ? "#f59e0b" : "#9ca3af"} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Right Sidebar - Trending Now */}
        <div className="w-[280px] shrink-0 bg-[#0e1525] text-white min-h-[calc(100vh-73px)] border-l border-gray-800">
          <div className="sticky top-[73px] p-6">
            <div className="flex items-center gap-2 mb-6">
              <TrendingUp className="text-amber-500" size={18} />
              <h3 className="text-sm font-bold tracking-wider uppercase text-gray-300">Trending Right Now</h3>
            </div>
            
            <div className="space-y-4">
              {topKeywords.map((kw, i) => (
                <div key={kw.word} className="group cursor-pointer">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-gray-200 font-medium group-hover:text-amber-400 transition-colors">{kw.word}</span>
                    <span className="text-xs text-gray-500 font-mono">{kw.count} hits</span>
                  </div>
                  <div className="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500 rounded-full" style={{ width: `${(kw.count / topKeywords[0].count) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
            
            {META.failed_ids.length > 0 && (
              <div className="mt-8 bg-red-500/10 border border-red-500/20 p-3 rounded-lg flex items-start gap-2">
                <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={14} />
                <span className="text-xs text-red-200">Alert: Failed to fetch from {META.failed_ids.join(", ")}</span>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}