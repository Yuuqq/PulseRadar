import React, { useState } from "react";
import { Search, Activity, ExternalLink, BarChart2, Clock } from "lucide-react";
import { KEYWORD_STATS, META, PLATFORM_LABELS, type Platform, maxRank } from "./_data";

const PLATFORM_COLORS: Record<Platform, { bg: string; text: string; hex: string }> = {
  zhihu: { bg: "bg-blue-100", text: "text-blue-700", hex: "#1d4ed8" },
  weibo: { bg: "bg-red-100", text: "text-red-700", hex: "#ef4444" },
  "36kr": { bg: "bg-blue-50", text: "text-blue-600", hex: "#2563eb" },
  huxiu: { bg: "bg-gray-100", text: "text-gray-800", hex: "#475569" },
  douyin: { bg: "bg-black", text: "text-white", hex: "#000000" },
  baidu: { bg: "bg-blue-100", text: "text-blue-800", hex: "#1e40af" },
  tieba: { bg: "bg-blue-50", text: "text-blue-600", hex: "#3b82f6" },
  bilibili: { bg: "bg-pink-100", text: "text-pink-600", hex: "#db2777" },
  toutiao: { bg: "bg-red-50", text: "text-red-600", hex: "#dc2626" },
  v2ex: { bg: "bg-gray-200", text: "text-gray-700", hex: "#334155" },
};

function MiniSparkline({ ranks }: { ranks: (number | null)[] }) {
  const width = 40;
  const height = 12;
  const maxR = maxRank(ranks);
  
  const points = ranks
    .map((r, i) => {
      if (r === null) return null;
      const x = (i / (ranks.length - 1)) * width;
      const y = 1 + ((r - 1) / (maxR > 1 ? maxR - 1 : 1)) * (height - 2);
      return `${x},${y}`;
    })
    .filter(Boolean);

  if (points.length === 0) return <div style={{ width, height }} />;
  const d = `M ${points.join(" L ")}`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <path d={d} fill="none" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TrajectoryChart({ ranks }: { ranks: (number | null)[] }) {
  const width = 300;
  const height = 100;
  const maxR = maxRank(ranks);
  
  const points = ranks
    .map((r, i) => {
      if (r === null) return null;
      const x = (i / (ranks.length - 1)) * width;
      const y = 10 + ((r - 1) / (maxR > 1 ? maxR - 1 : 1)) * (height - 20);
      return { x, y, r };
    })
    .filter((p): p is {x: number; y: number; r: number} => p !== null);

  if (points.length === 0) {
    return <div className="h-[100px] flex items-center justify-center text-slate-400 text-sm">暂无轨迹数据</div>;
  }

  const d = `M ${points.map(p => `${p.x},${p.y}`).join(" L ")}`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <path d={d} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={i === points.length - 1 ? 4 : 3} fill={i === points.length - 1 ? "#2563eb" : "white"} stroke="#2563eb" strokeWidth="2" />
      ))}
    </svg>
  );
}

export default function ModerateBriefing() {
  const [selectedKwIdx, setSelectedKwIdx] = useState(0);
  const [selectedTitleIdx, setSelectedTitleIdx] = useState(0);

  const selectedKeyword = KEYWORD_STATS[selectedKwIdx];
  const selectedTitle = selectedKeyword?.titles[selectedTitleIdx] || selectedKeyword?.titles[0];

  return (
    <div className="flex flex-col h-screen bg-white text-slate-900 font-sans overflow-hidden">
      {/* Top Bar */}
      <header className="h-14 border-b border-slate-200 flex items-center justify-between px-4 shrink-0 bg-white z-10">
        <div className="flex items-center gap-2 w-64 shrink-0">
          <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center text-white">
            <Activity size={18} />
          </div>
          <span className="font-bold text-lg tracking-tight">PulseRadar</span>
        </div>

        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input 
              type="text" 
              placeholder="Search keywords..." 
              className="w-full bg-slate-100 border-none rounded-md py-1.5 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
            />
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="flex bg-slate-100 p-0.5 rounded-md border border-slate-200">
            <button className="px-3 py-1 text-xs font-medium bg-white rounded shadow-sm text-slate-800">今日</button>
            <button className="px-3 py-1 text-xs font-medium text-slate-500 hover:text-slate-700">本周</button>
          </div>
        </div>
      </header>

      {/* Main 3-pane layout */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Left Rail: Keyword List */}
        <div className="w-[260px] border-r border-slate-200 flex flex-col bg-slate-50/50 shrink-0">
          <div className="p-3 border-b border-slate-200 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Events ({KEYWORD_STATS.length})</span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {KEYWORD_STATS.map((kw, idx) => {
              const isSelected = idx === selectedKwIdx;
              const hasNew = kw.titles.some(t => t.is_new);
              return (
                <button
                  key={kw.word}
                  onClick={() => { setSelectedKwIdx(idx); setSelectedTitleIdx(0); }}
                  className={`w-full flex items-center justify-between p-3 border-b border-slate-100 transition-colors relative ${isSelected ? 'bg-white' : 'hover:bg-slate-100'}`}
                >
                  {isSelected && <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600" />}
                  <div className="flex flex-col items-start gap-1">
                    <div className="flex items-center gap-1.5">
                      {hasNew && <div className="w-1.5 h-1.5 rounded-full bg-blue-600" />}
                      <span className={`text-sm font-semibold ${isSelected ? 'text-slate-900' : 'text-slate-700'}`}>{kw.word}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-slate-500 bg-slate-200/70 px-1.5 rounded font-medium">{kw.count} sources</span>
                    </div>
                  </div>
                  <MiniSparkline ranks={kw.titles[0]?.ranks || []} />
                </button>
              );
            })}
          </div>
        </div>

        {/* Center Pane: Thread List */}
        <div className="w-[380px] lg:w-[480px] border-r border-slate-200 flex flex-col bg-white shrink-0">
          <div className="p-3 border-b border-slate-200 flex items-center justify-between bg-white">
            <h2 className="text-lg font-bold text-slate-800">{selectedKeyword?.word}</h2>
            <span className="text-xs text-slate-500">{selectedKeyword?.count} items</span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {selectedKeyword?.titles.map((title, idx) => {
              const isSelected = idx === selectedTitleIdx;
              const pConf = PLATFORM_COLORS[title.source] || PLATFORM_COLORS.v2ex;
              const initials = PLATFORM_LABELS[title.source]?.slice(0, 1) || "P";
              
              return (
                <button
                  key={idx}
                  onClick={() => setSelectedTitleIdx(idx)}
                  className={`w-full text-left p-4 border-b border-slate-100 transition-colors ${isSelected ? 'bg-blue-50/50' : 'hover:bg-slate-50'}`}
                >
                  <div className="flex gap-3">
                    <div className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-xs font-bold ${pConf.bg} ${pConf.text}`}>
                      {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start mb-1 gap-2">
                        <span className="text-xs font-medium text-slate-500 truncate">{PLATFORM_LABELS[title.source]}</span>
                        <span className="text-[10px] text-slate-400 whitespace-nowrap">{title.time_display}</span>
                      </div>
                      <h3 className={`text-sm leading-snug line-clamp-2 ${isSelected ? 'font-bold text-slate-900' : 'font-medium text-slate-700'}`}>
                        {title.is_new && <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-600 mr-1.5 mb-0.5" />}
                        {title.title}
                      </h3>
                      
                      <div className="flex items-center gap-2 mt-2">
                        {title.ranks.filter(r => r !== null).length > 0 && (
                          <div className="flex items-center gap-1 bg-slate-100 px-1.5 py-0.5 rounded text-[10px] text-slate-600 font-medium">
                            <BarChart2 size={10} />
                            Top {Math.min(...title.ranks.filter((r): r is number => r !== null))}
                          </div>
                        )}
                        <div className="flex items-center">
                          {title.hits.slice(0, 3).map((hit, i) => (
                            <div key={hit} className={`w-3 h-3 rounded-full border border-white -ml-1 first:ml-0`} style={{ backgroundColor: PLATFORM_COLORS[hit]?.hex || '#94a3b8', zIndex: 3 - i }} title={PLATFORM_LABELS[hit]} />
                          ))}
                          {title.hits.length > 3 && (
                            <span className="text-[10px] text-slate-400 ml-1">+{title.hits.length - 3}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Pane: Reading Panel */}
        <div className="flex-1 flex flex-col bg-white min-w-0">
          {selectedTitle ? (
            <>
              <div className="px-8 py-6 border-b border-slate-100">
                <div className="flex items-center gap-2 mb-4">
                  <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded">
                    {PLATFORM_LABELS[selectedTitle.source]}
                  </span>
                  <span className="text-sm text-slate-400 flex items-center gap-1">
                    <Clock size={14} /> {selectedTitle.time_display}
                  </span>
                  {selectedTitle.is_new && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded">
                      NEW
                    </span>
                  )}
                </div>
                
                <h1 className="text-2xl font-bold text-slate-900 leading-tight mb-6">
                  {selectedTitle.title}
                </h1>

                <div className="flex gap-4">
                  <a 
                    href={selectedTitle.url} 
                    className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
                  >
                    View Original Source <ExternalLink size={14} />
                  </a>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-8 bg-slate-50/50">
                <div className="max-w-2xl space-y-8">
                  {/* Trajectory */}
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                    <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
                      <BarChart2 size={16} className="text-blue-500" /> 
                      Rank Trajectory
                    </h3>
                    <div className="pl-2 border-l-2 border-slate-100 pb-2">
                      <TrajectoryChart ranks={selectedTitle.ranks} />
                      <div className="flex justify-between text-[10px] text-slate-400 mt-2 w-[300px]">
                        <span>T-9h</span>
                        <span>Now</span>
                      </div>
                    </div>
                  </div>

                  {/* Hits Breakdown */}
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                    <h3 className="text-sm font-bold text-slate-800 mb-4">Platform Resonance ({selectedTitle.hits.length})</h3>
                    <div className="space-y-3">
                      {selectedTitle.hits.map((hit, i) => {
                        const conf = PLATFORM_COLORS[hit] || PLATFORM_COLORS.v2ex;
                        return (
                          <div key={hit} className="flex items-center gap-3">
                            <span className="w-20 text-xs font-medium text-slate-600">{PLATFORM_LABELS[hit] || hit}</span>
                            <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                              <div className="h-full rounded-full" style={{ width: `${Math.max(20, 100 - i * 15)}%`, backgroundColor: conf.hex }}></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400">
              Select a thread to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
