import React, { useMemo } from "react";
import { KEYWORD_STATS, META, PLATFORM_LABELS, type NewsTitle, type Platform } from "./_data";
import { Activity, AlertTriangle, Radio, Target, Crosshair } from "lucide-react";

const PLATFORM_POSITIONS: Record<Platform, { x: number; y: number }> = {
  zhihu: { x: 50, y: 15 },
  weibo: { x: 80, y: 35 },
  "36kr": { x: 75, y: 65 },
  huxiu: { x: 50, y: 85 },
  douyin: { x: 25, y: 65 },
  baidu: { x: 20, y: 35 },
  tieba: { x: 35, y: 50 },
  bilibili: { x: 65, y: 50 },
  toutiao: { x: 50, y: 35 },
  v2ex: { x: 50, y: 65 },
};

function Sparkline({ ranks }: { ranks: (number | null)[] }) {
  const points = useMemo(() => {
    const validRanks = ranks.map((r) => (r === null ? 50 : r));
    const maxRank = 50; 
    const w = 100;
    const h = 30;
    const stepX = w / (ranks.length - 1);
    
    return validRanks
      .map((r, i) => {
        const x = i * stepX;
        const y = h - ((maxRank - r) / maxRank) * h;
        return `${x},${y}`;
      })
      .join(" ");
  }, [ranks]);

  const fillPoints = useMemo(() => {
    return `${points} 100,30 0,30`;
  }, [points]);

  let lastValidIdx = -1;
  for (let i = ranks.length - 1; i >= 0; i--) {
    if (ranks[i] !== null) { lastValidIdx = i; break; }
  }
  const lastValidRank = lastValidIdx >= 0 ? ranks[lastValidIdx] : null;
  
  let lastDot = null;
  if (lastValidIdx >= 0 && lastValidRank !== null) {
    const w = 100;
    const h = 30;
    const x = lastValidIdx * (w / (ranks.length - 1));
    const y = h - ((50 - lastValidRank) / 50) * h;
    lastDot = <circle cx={x} cy={y} r="2.5" fill="#3b3aff" className="shadow-sm" />;
  }

  return (
    <div className="w-[100px] h-[30px] shrink-0 relative flex items-center">
      <svg width="100" height="30" viewBox="0 0 100 30" className="overflow-visible">
        <polygon
          points={fillPoints}
          fill="rgba(59, 58, 255, 0.1)"
        />
        <polyline
          points={points}
          fill="none"
          stroke="#3b3aff"
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {lastDot}
      </svg>
    </div>
  );
}

function ResonanceRadar({ hits }: { hits: Platform[] }) {
  return (
    <div className="relative w-8 h-8 rounded-full border border-[#e4e7ec] flex items-center justify-center bg-white shrink-0 shadow-sm">
      <div className="absolute inset-0 rounded-full border border-[#0fb5a8]/20 scale-50" />
      <div className="absolute inset-0 rounded-full border border-[#0fb5a8]/10 scale-75" />
      {hits.map((p) => {
        const pos = PLATFORM_POSITIONS[p];
        if (!pos) return null;
        return (
          <div
            key={p}
            className="absolute w-1.5 h-1.5 rounded-full bg-[#0fb5a8] shadow-sm"
            style={{ left: `${pos.x}%`, top: `${pos.y}%`, transform: 'translate(-50%, -50%)' }}
            title={PLATFORM_LABELS[p]}
          />
        );
      })}
    </div>
  );
}

function RadarHero() {
  return (
    <div className="relative w-full h-[300px] overflow-hidden flex items-center justify-center border-b border-[#e4e7ec] bg-white">
      {/* Radar rings */}
      <div className="absolute w-[600px] h-[600px] rounded-full border border-[#e4e7ec]" />
      <div className="absolute w-[450px] h-[450px] rounded-full border border-[#e4e7ec]" />
      <div className="absolute w-[300px] h-[300px] rounded-full border border-[#e4e7ec]" />
      <div className="absolute w-[150px] h-[150px] rounded-full border border-[#3b3aff]/30" />
      
      {/* Crosshairs */}
      <div className="absolute w-[600px] h-[1px] bg-[#e4e7ec]" />
      <div className="absolute h-[600px] w-[1px] bg-[#e4e7ec]" />

      {/* Scanner sweeper */}
      <div className="absolute w-[300px] h-[300px] top-1/2 left-1/2 origin-top-left scanner-sweep opacity-30">
        <div className="w-[300px] h-[300px] bg-gradient-to-br from-[#3b3aff] to-transparent rounded-br-full" />
      </div>
      
      {/* Blips */}
      <div className="absolute w-2 h-2 rounded-full bg-[#e11d48] shadow-sm top-[30%] left-[40%] animate-pulse" />
      <div className="absolute w-1.5 h-1.5 rounded-full bg-[#3b3aff] shadow-sm top-[60%] left-[55%] animate-pulse delay-75" />
      <div className="absolute w-2 h-2 rounded-full bg-[#0fb5a8] shadow-sm top-[45%] left-[70%] animate-pulse delay-150" />

      {/* Stats overlay */}
      <div className="absolute top-6 left-8 flex flex-col space-y-1 font-mono text-xs">
        <div className="flex items-center space-x-2 text-[#3b3aff] font-semibold">
          <Radio size={14} />
          <span>SYS.ONLINE</span>
        </div>
        <div className="text-[#64748b] font-medium">UPLINK: {META.time_str}</div>
        <div className="text-[#64748b] font-medium">MODE: {META.mode_label}</div>
      </div>

      <div className="absolute top-6 right-8 flex flex-col space-y-1 font-mono text-xs text-right">
        <div className="text-[#0fb5a8] font-semibold">SIGNALS: {META.total_titles}</div>
        <div className="text-[#3b3aff] font-semibold">LOCKED: {META.hot_news_count}</div>
        {META.failed_ids.length > 0 && (
          <div className="text-[#e11d48] flex items-center justify-end space-x-1 mt-1 font-medium">
            <AlertTriangle size={12} />
            <span>ERR: {META.failed_ids.join(", ")}</span>
          </div>
        )}
      </div>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-center bg-white/80 backdrop-blur-sm px-4 py-2 rounded-xl border border-[#e4e7ec] shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight text-[#0f172a] uppercase">
          Pulse<span className="text-[#3b3aff]">Radar</span>
        </h1>
        <div className="text-[#64748b] text-[10px] font-mono mt-0.5 tracking-widest font-semibold">
          STRATEGIC INTELLIGENCE COMMAND
        </div>
      </div>
    </div>
  );
}

export default function BoldLight() {
  return (
    <div className="min-h-screen bg-[#fafbfc] text-[#0f172a] font-sans selection:bg-[#3b3aff]/20">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');
        
        .font-sans {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        .font-mono {
          font-family: 'JetBrains Mono', monospace;
          font-variant-numeric: tabular-nums;
        }

        @keyframes sweep {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        .scanner-sweep {
          animation: sweep 4s linear infinite;
        }

        .dashboard-card {
          background: #ffffff;
          border: 1px solid #e4e7ec;
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
          transition: all 0.2s ease;
        }
        
        .dashboard-card:hover {
          border-color: #cbd5e1;
          box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.05), 0 2px 4px -2px rgba(15, 23, 42, 0.05);
        }
      `}</style>

      <RadarHero />

      <div className="max-w-5xl mx-auto p-8 space-y-8 pb-20">
        <div className="flex items-center space-x-3 text-[#475569] font-mono text-sm border-b border-[#e4e7ec] pb-3">
          <Crosshair size={16} className="text-[#3b3aff]" />
          <span className="tracking-widest font-semibold uppercase">Active Detection Clusters</span>
        </div>

        {KEYWORD_STATS.map((cluster) => (
          <div key={cluster.word} className="dashboard-card rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[#e4e7ec] bg-[#f3f5f8] flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Target size={18} className="text-[#0fb5a8]" />
                <h2 className="text-lg font-bold tracking-tight text-[#0f172a]">
                  {cluster.word}
                </h2>
              </div>
              <div className="font-mono text-[#3b3aff] text-sm flex items-center space-x-2 font-semibold">
                <Activity size={16} />
                <span>SIG_COUNT: {cluster.count.toString().padStart(2, '0')}</span>
              </div>
            </div>

            <div className="divide-y divide-[#e4e7ec]">
              {cluster.titles.map((title, idx) => (
                <div key={idx} className="p-5 flex items-center space-x-6 hover:bg-[#f8fafc] transition-colors group relative">
                  {title.is_new && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#3b3aff]" />
                  )}
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      {title.is_new && (
                        <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[#3b3aff]/10 text-[#3b3aff] font-bold rounded">
                          NEW
                        </span>
                      )}
                      <span className="text-xs font-mono text-[#64748b] bg-white border border-[#e4e7ec] font-semibold px-1.5 py-0.5 rounded shadow-sm">
                        {PLATFORM_LABELS[title.source]}
                      </span>
                      <span className="text-xs font-mono text-[#64748b] font-medium">{title.time_display}</span>
                    </div>
                    <a
                      href={title.url}
                      className="text-[15px] font-medium text-[#0f172a] group-hover:text-[#3b3aff] transition-colors line-clamp-2 leading-snug"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {title.title}
                    </a>
                  </div>

                  <div className="flex items-center space-x-8 shrink-0">
                    <div className="flex flex-col items-center space-y-1.5">
                      <span className="text-[10px] font-mono text-[#64748b] tracking-widest font-semibold uppercase">Pulse</span>
                      <Sparkline ranks={title.ranks} />
                    </div>
                    
                    <div className="flex flex-col items-center space-y-1.5">
                      <span className="text-[10px] font-mono text-[#64748b] tracking-widest font-semibold uppercase">Resonance</span>
                      <ResonanceRadar hits={title.hits} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
