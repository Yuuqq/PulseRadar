import React from "react";
import { AlertCircle, Clock, Database, CheckCircle, XCircle } from "lucide-react";
import { KEYWORD_STATS, META, PLATFORM_LABELS, type NewsTitle, type Platform, maxRank } from "./_data";

const PLATFORM_COLORS: Record<Platform, string> = {
  zhihu: "#0066ff",
  weibo: "#ff8200",
  "36kr": "#225599",
  huxiu: "#f5a623",
  douyin: "#000000",
  baidu: "#2932e1",
  tieba: "#3385ff",
  bilibili: "#00a1d6",
  toutiao: "#f04142",
  v2ex: "#333333",
};

function Sparkline({ ranks }: { ranks: (number | null)[] }) {
  const width = 80;
  const height = 24;
  const padding = 2;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  
  // Find max rank in this specific array to scale locally, or use a global max
  // Using global max 50 for consistency, or the maxRank from data.
  // Actually, let's use 50 as a typical max rank for a hotlist.
  const MAX_RANK = 50;
  
  const validPoints = ranks.map((r, i) => ({ r, i })).filter((p) => p.r !== null) as { r: number, i: number }[];
  if (validPoints.length === 0) return <div style={{ width, height }} />;

  const points = validPoints.map(p => {
    const x = padding + (p.i / (ranks.length - 1)) * usableWidth;
    const y = padding + (p.r / MAX_RANK) * usableHeight;
    return `${x},${y}`;
  });
  
  const lastPoint = validPoints[validPoints.length - 1];
  const lastX = padding + (lastPoint.i / (ranks.length - 1)) * usableWidth;
  const lastY = padding + (lastPoint.r / MAX_RANK) * usableHeight;

  return (
    <svg width={width} height={height} className="overflow-visible" style={{ display: 'block' }}>
      <polyline
        fill="none"
        stroke="#1d4ed8"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points.join(" ")}
        opacity={0.6}
      />
      <circle
        cx={lastX}
        cy={lastY}
        r="2"
        fill="#1d4ed8"
      />
    </svg>
  );
}

function ResonanceDots({ hits }: { hits: Platform[] }) {
  return (
    <div className="flex items-center gap-1 ml-2">
      {hits.map((platform) => (
        <div
          key={platform}
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: PLATFORM_COLORS[platform] || "#888" }}
          title={PLATFORM_LABELS[platform]}
        />
      ))}
    </div>
  );
}

export function Conservative() {
  return (
    <div className="min-h-screen bg-gray-100 font-sans text-gray-900 pb-12">
      {/* Header */}
      <header 
        className="px-6 py-8 text-white shadow-sm"
        style={{ background: "linear-gradient(135deg, #1d4ed8 0%, #0f766e 100%)" }}
      >
        <div className="max-w-4xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight mb-2">PulseRadar</h1>
              <div className="flex flex-wrap items-center gap-4 text-sm text-white/80">
                <span className="flex items-center gap-1 bg-black/10 px-2 py-0.5 rounded">
                  {META.mode_label}
                </span>
                <span className="flex items-center gap-1">
                  <Database className="w-4 h-4" /> 采集: {META.total_titles}
                </span>
                <span className="flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" /> 命中: {META.hot_news_count}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" /> {META.time_str}
                </span>
              </div>
            </div>
            
            {META.failed_ids.length > 0 && (
              <div className="flex items-center gap-2 bg-red-500/20 text-red-100 px-3 py-2 rounded border border-red-500/30 text-sm">
                <AlertCircle className="w-4 h-4" />
                <span>失败节点: {META.failed_ids.join(", ")}</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 mt-8 space-y-6">
        {KEYWORD_STATS.map((kw) => (
          <section key={kw.word} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="bg-gray-50/50 px-5 py-3 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">
                {kw.word}
              </h2>
              <span className="text-sm font-medium text-gray-500 bg-gray-200/50 px-2 py-0.5 rounded-full">
                {kw.count} 条记录
              </span>
            </div>
            
            <div className="divide-y divide-gray-100">
              {kw.titles.map((item, idx) => (
                <div key={idx} className="p-4 hover:bg-blue-50/30 transition-colors flex flex-col sm:flex-row sm:items-center gap-4 group">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center flex-wrap gap-2 mb-1.5">
                      <span className="text-xs font-medium text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                        {PLATFORM_LABELS[item.source]}
                      </span>
                      {item.is_new && (
                        <span className="text-xs font-bold text-red-500 bg-red-50 px-1.5 py-0.5 rounded">
                          新
                        </span>
                      )}
                      <span className="text-xs text-gray-400">
                        {item.time_display}
                      </span>
                      <ResonanceDots hits={item.hits} />
                    </div>
                    <a href={item.url} className="text-[15px] font-medium text-gray-800 group-hover:text-blue-700 transition-colors line-clamp-2 leading-snug">
                      {item.title}
                    </a>
                  </div>
                  
                  <div className="flex-shrink-0 flex items-center justify-end">
                    <Sparkline ranks={item.ranks} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </main>
    </div>
  );
}
