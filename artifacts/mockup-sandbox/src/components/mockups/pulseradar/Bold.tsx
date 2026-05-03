import React, { useMemo } from "react";
import { KEYWORD_STATS, META, PLATFORM_LABELS, type NewsTitle, type Platform } from "./_data";
import { Activity, ShieldAlert, AlertTriangle, Radio, Target, Crosshair } from "lucide-react";

// Platform coordinates for the mini-radar (resonance visualization)
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
    const maxRank = 50; // Assume 50 is max
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

  const lastValidIdx = ranks.findLastIndex((r) => r !== null);
  const lastValidRank = lastValidIdx >= 0 ? ranks[lastValidIdx] : null;
  
  let lastDot = null;
  if (lastValidIdx >= 0 && lastValidRank !== null) {
    const w = 100;
    const h = 30;
    const x = lastValidIdx * (w / (ranks.length - 1));
    const y = h - ((50 - lastValidRank) / 50) * h;
    lastDot = <circle cx={x} cy={y} r="2" fill="#00ff9c" className="glow-dot" />;
  }

  return (
    <div className="w-[100px] h-[30px] shrink-0 relative flex items-center">
      <svg width="100" height="30" viewBox="0 0 100 30" className="overflow-visible">
        <polyline
          points={points}
          fill="none"
          stroke="#00e5ff"
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          className="opacity-70"
        />
        {lastDot}
      </svg>
    </div>
  );
}

function ResonanceRadar({ hits }: { hits: Platform[] }) {
  return (
    <div className="relative w-8 h-8 rounded-full border border-[#5a6b85]/40 flex items-center justify-center bg-[#070b14]/50 shrink-0">
      <div className="absolute inset-0 rounded-full border border-[#00ff9c]/10 scale-50" />
      <div className="absolute inset-0 rounded-full border border-[#00ff9c]/20 scale-75" />
      {hits.map((p) => {
        const pos = PLATFORM_POSITIONS[p];
        if (!pos) return null;
        return (
          <div
            key={p}
            className="absolute w-1.5 h-1.5 rounded-full bg-[#00ff9c] shadow-[0_0_4px_#00ff9c]"
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
    <div className="relative w-full h-[300px] overflow-hidden flex items-center justify-center border-b border-[#5a6b85]/30">
      {/* Radar rings */}
      <div className="absolute w-[600px] h-[600px] rounded-full border border-[#5a6b85]/20" />
      <div className="absolute w-[450px] h-[450px] rounded-full border border-[#5a6b85]/30" />
      <div className="absolute w-[300px] h-[300px] rounded-full border border-[#5a6b85]/40" />
      <div className="absolute w-[150px] h-[150px] rounded-full border border-[#00ff9c]/30" />
      
      {/* Crosshairs */}
      <div className="absolute w-[600px] h-[1px] bg-[#5a6b85]/30" />
      <div className="absolute h-[600px] w-[1px] bg-[#5a6b85]/30" />

      {/* Scanner sweeper */}
      <div className="absolute w-[300px] h-[300px] top-1/2 left-1/2 origin-top-left scanner-sweep">
        <div className="w-[300px] h-[300px] bg-gradient-to-br from-[#00ff9c]/40 to-transparent rounded-br-full" />
      </div>
      
      {/* Blips */}
      <div className="absolute w-2 h-2 rounded-full bg-[#ff3b6f] shadow-[0_0_8px_#ff3b6f] top-[30%] left-[40%] animate-pulse" />
      <div className="absolute w-1.5 h-1.5 rounded-full bg-[#00ff9c] shadow-[0_0_6px_#00ff9c] top-[60%] left-[55%] animate-pulse delay-75" />
      <div className="absolute w-2 h-2 rounded-full bg-[#00e5ff] shadow-[0_0_8px_#00e5ff] top-[45%] left-[70%] animate-pulse delay-150" />

      {/* Stats overlay */}
      <div className="absolute top-4 left-6 flex flex-col space-y-1 font-mono text-xs">
        <div className="flex items-center space-x-2 text-[#00ff9c]">
          <Radio size={14} />
          <span>SYS.ONLINE</span>
        </div>
        <div className="text-[#5a6b85]">UPLINK: {META.time_str}</div>
        <div className="text-[#5a6b85]">MODE: {META.mode_label}</div>
      </div>

      <div className="absolute top-4 right-6 flex flex-col space-y-1 font-mono text-xs text-right">
        <div className="text-[#00e5ff]">SIGNALS: {META.total_titles}</div>
        <div className="text-[#00ff9c]">LOCKED: {META.hot_news_count}</div>
        {META.failed_ids.length > 0 && (
          <div className="text-[#ff3b6f] flex items-center justify-end space-x-1 mt-1">
            <AlertTriangle size={12} />
            <span>ERR: {META.failed_ids.join(", ")}</span>
          </div>
        )}
      </div>

      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center">
        <h1 className="text-2xl font-bold tracking-[0.2em] text-[#e8f0ff] uppercase shadow-black drop-shadow-md">
          Pulse<span className="text-[#00ff9c]">Radar</span>
        </h1>
        <div className="text-[#5a6b85] text-[10px] font-mono mt-1 tracking-widest">
          STRATEGIC INTELLIGENCE COMMAND
        </div>
      </div>
    </div>
  );
}

export function Bold() {
  return (
    <div className="min-h-screen bg-[#070b14] text-[#e8f0ff] font-sans selection:bg-[#00ff9c]/30">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
        
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
        
        .glow-dot {
          filter: drop-shadow(0 0 4px #00ff9c);
        }

        .glass-card {
          background: rgba(10, 15, 26, 0.6);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(90, 107, 133, 0.2);
          transition: all 0.3s ease;
        }
        
        .glass-card:hover {
          border-color: rgba(0, 255, 156, 0.3);
          box-shadow: inset 0 0 20px rgba(0, 255, 156, 0.05);
        }
      `}</style>

      <RadarHero />

      <div className="max-w-5xl mx-auto p-6 space-y-8 pb-20">
        <div className="flex items-center space-x-3 text-[#5a6b85] font-mono text-sm border-b border-[#5a6b85]/20 pb-2">
          <Crosshair size={16} className="text-[#00ff9c]" />
          <span className="tracking-widest">ACTIVE DETECTION CLUSTERS</span>
        </div>

        {KEYWORD_STATS.map((cluster) => (
          <div key={cluster.word} className="glass-card rounded-lg overflow-hidden">
            <div className="px-5 py-3 border-b border-[#5a6b85]/20 bg-[#00ff9c]/5 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Target size={16} className="text-[#00e5ff]" />
                <h2 className="text-lg font-bold tracking-wider text-[#e8f0ff] uppercase">
                  {cluster.word}
                </h2>
              </div>
              <div className="font-mono text-[#00ff9c] text-sm flex items-center space-x-2">
                <Activity size={14} />
                <span>SIG_COUNT: {cluster.count.toString().padStart(2, '0')}</span>
              </div>
            </div>

            <div className="divide-y divide-[#5a6b85]/10">
              {cluster.titles.map((title, idx) => (
                <div key={idx} className="p-4 flex items-center space-x-6 hover:bg-white/[0.02] transition-colors group relative">
                  {title.is_new && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#ff3b6f] shadow-[0_0_10px_#ff3b6f]" />
                  )}
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-1">
                      {title.is_new && (
                        <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[#ff3b6f]/20 text-[#ff3b6f] border border-[#ff3b6f]/50 rounded animate-pulse">
                          NEW
                        </span>
                      )}
                      <span className="text-xs font-mono text-[#5a6b85] uppercase border border-[#5a6b85]/30 px-1.5 py-0.5 rounded">
                        {PLATFORM_LABELS[title.source]}
                      </span>
                      <span className="text-xs font-mono text-[#5a6b85]">{title.time_display}</span>
                    </div>
                    <a
                      href={title.url}
                      className="text-base text-[#e8f0ff] group-hover:text-[#00e5ff] transition-colors line-clamp-2"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {title.title}
                    </a>
                  </div>

                  <div className="flex items-center space-x-8 shrink-0">
                    <div className="flex flex-col items-center space-y-1">
                      <span className="text-[10px] font-mono text-[#5a6b85] tracking-widest">PULSE</span>
                      <Sparkline ranks={title.ranks} />
                    </div>
                    
                    <div className="flex flex-col items-center space-y-1">
                      <span className="text-[10px] font-mono text-[#5a6b85] tracking-widest">RESONANCE</span>
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
