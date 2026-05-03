import React from "react";
import { Activity, AlertTriangle, Clock, Target, ExternalLink } from "lucide-react";
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

function Sparkline({ ranks }: { ranks: (number | null)[] }) {
  const width = 120;
  const height = 32;
  const maxR = maxRank(ranks);
  
  const points = ranks
    .map((r, i) => {
      if (r === null) return null;
      const x = (i / (ranks.length - 1)) * width;
      // rank 1 is top (y=2), maxR is bottom (y=height-2)
      const y = 2 + ((r - 1) / (maxR > 1 ? maxR - 1 : 1)) * (height - 4);
      return `${x},${y}`;
    })
    .filter(Boolean);

  if (points.length === 0) {
    return <div className="w-[120px] h-[32px] bg-gray-50 rounded flex items-center justify-center text-xs text-gray-400">无数据</div>;
  }

  const d = `M ${points.join(" L ")}`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <path d={d} fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {ranks.map((r, i) => {
        if (r === null) return null;
        const x = (i / (ranks.length - 1)) * width;
        const y = 2 + ((r - 1) / (maxR > 1 ? maxR - 1 : 1)) * (height - 4);
        return <circle key={i} cx={x} cy={y} r={i === ranks.length - 1 ? "3" : "2"} fill={i === ranks.length - 1 ? "#4f46e5" : "white"} stroke="#6366f1" strokeWidth="1.5" />;
      })}
    </svg>
  );
}

export function Moderate() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans" style={{ fontFamily: "'Manrope', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      <style>{`
        @keyframes sweep {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .radar-sweep {
          transform-origin: center;
          animation: sweep 6s linear infinite;
        }
        .card-hover {
          transition: all 0.2s ease;
        }
        .card-hover:hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
        }
      `}</style>

      {/* Hero Section */}
      <div className="bg-white border-b border-slate-200 overflow-hidden relative">
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: "radial-gradient(#000 1px, transparent 1px)", backgroundSize: "20px 20px" }}></div>
        <div className="max-w-5xl mx-auto px-6 py-12 relative flex items-center justify-between">
          <div className="max-w-md z-10">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-lg shadow-indigo-200">
                <Activity size={24} />
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">PulseRadar</h1>
              <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs font-semibold rounded-full tracking-wide">
                {META.mode_label}
              </span>
            </div>
            <p className="text-slate-500 text-lg leading-relaxed mb-8">
              Real-time resonance detection across multiple platforms.
            </p>

            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 px-4 py-2.5 rounded-lg shadow-sm">
                <Target size={16} className="text-indigo-500" />
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">采集</span>
                  <span className="text-sm font-semibold text-slate-800">{META.total_titles}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 px-4 py-2.5 rounded-lg shadow-sm">
                <Activity size={16} className="text-emerald-500" />
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">命中</span>
                  <span className="text-sm font-semibold text-slate-800">{META.hot_news_count}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 px-4 py-2.5 rounded-lg shadow-sm">
                <Clock size={16} className="text-amber-500" />
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">时间</span>
                  <span className="text-sm font-semibold text-slate-800">{META.time_str}</span>
                </div>
              </div>
            </div>

            {META.failed_ids.length > 0 && (
              <div className="mt-4 flex items-center gap-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md border border-red-100 inline-flex w-fit">
                <AlertTriangle size={14} />
                <span>采集异常: {META.failed_ids.join(", ")}</span>
              </div>
            )}
          </div>

          <div className="relative w-[300px] h-[300px] hidden md:block">
            <svg viewBox="0 0 300 300" className="w-full h-full opacity-80">
              <defs>
                <linearGradient id="radarSweep" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="#4f46e5" stopOpacity="0" />
                </linearGradient>
              </defs>
              <circle cx="150" cy="150" r="140" fill="none" stroke="#e2e8f0" strokeWidth="1" />
              <circle cx="150" cy="150" r="100" fill="none" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4 4" />
              <circle cx="150" cy="150" r="60" fill="none" stroke="#e2e8f0" strokeWidth="1" />
              <circle cx="150" cy="150" r="20" fill="none" stroke="#e2e8f0" strokeWidth="1" />
              
              <g className="radar-sweep">
                <path d="M150 150 L150 10 A140 140 0 0 1 290 150 Z" fill="url(#radarSweep)" />
                <line x1="150" y1="150" x2="150" y2="10" stroke="#4f46e5" strokeWidth="2" opacity="0.5" />
              </g>

              {/* Dots for stories */}
              <circle cx="210" cy="80" r="4" fill="#4f46e5" />
              <circle cx="90" cy="120" r="5" fill="#f43f5e" />
              <circle cx="180" cy="220" r="3" fill="#10b981" />
              <circle cx="120" cy="190" r="4" fill="#f59e0b" />
              <circle cx="240" cy="170" r="6" fill="#8b5cf6" />
              
              {/* Plus markers */}
              <path d="M147 150 h6 m-3 -3 v6" stroke="#4f46e5" strokeWidth="1.5" />
              <path d="M150 0 v8 m0 284 v8 m-150 -150 h8 m284 0 h8" stroke="#cbd5e1" strokeWidth="2" />
            </svg>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="space-y-12">
          {KEYWORD_STATS.map((stat, idx) => (
            <div key={idx} className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-6 w-1 bg-indigo-500 rounded-full"></div>
                <h2 className="text-xl font-bold text-slate-900 tracking-tight">{stat.word}</h2>
                <span className="text-sm font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md">
                  {stat.count} 条记录
                </span>
              </div>

              <div className="space-y-3 pl-4">
                {stat.titles.map((title, tIdx) => (
                  <div key={tIdx} className="bg-white rounded-xl p-5 border border-slate-100 shadow-sm card-hover flex flex-col sm:flex-row sm:items-center gap-6">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start gap-3 mb-2">
                        {title.is_new && (
                          <span className="mt-0.5 shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-indigo-500 text-white leading-none">
                            新
                          </span>
                        )}
                        <a href={title.url} className="text-[17px] font-medium text-slate-800 hover:text-indigo-600 transition-colors line-clamp-2">
                          {title.title}
                        </a>
                      </div>
                      
                      <div className="flex flex-wrap items-center gap-2 mt-3">
                        <span className="text-xs text-slate-400 mr-2 flex items-center gap-1">
                          <Clock size={12} /> {title.time_display}
                        </span>
                        
                        {title.hits.map((hit) => {
                          const conf = PLATFORM_COLORS[hit] || { bg: "bg-slate-100", text: "text-slate-600" };
                          return (
                            <span key={hit} className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${conf.bg} ${conf.text}`}>
                              {PLATFORM_LABELS[hit] || hit}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                    
                    <div className="shrink-0 flex items-center justify-end sm:w-[150px]">
                      <div className="flex flex-col items-end gap-1">
                        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">排名趋势</span>
                        <Sparkline ranks={title.ranks} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
