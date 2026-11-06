import React, { useState } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { Search, ShieldAlert, Check, RefreshCw, Clock } from 'lucide-react';

export const AlertsPage: React.FC = () => {
  const { alerts, resolveAlert } = useCrowdSystem();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'critical' | 'warning' | 'resolved'>('all');

  const filteredAlerts = alerts.filter(alert => {
    const matchesSearch = alert.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          alert.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          alert.zone.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (filterType === 'all') return matchesSearch;
    if (filterType === 'resolved') return matchesSearch && alert.resolved;
    if (filterType === 'critical') return matchesSearch && alert.level === 'critical' && !alert.resolved;
    if (filterType === 'warning') return matchesSearch && alert.level === 'warning' && !alert.resolved;
    return matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-2 border-b border-cyber-border/40">
        <div>
          <h2 className="text-base font-bold uppercase tracking-wider text-slate-200">
            System Alerts & Warning Logs
          </h2>
          <p className="text-[10px] text-slate-500">
            Real-time tracking of safety hazards, perimeter breaches, and crowd structural density alerts.
          </p>
        </div>
        <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
          <Clock className="w-3.5 h-3.5 text-cyan-400" /> Session active: 1h 42m
        </span>
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-slate-950/40 rounded-xl border border-slate-900">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search by title, description, or zone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-950 border border-cyber-border text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/40"
          />
        </div>

        {/* Filter Buttons */}
        <div className="flex gap-2">
          {[
            { id: 'all', label: 'All Logs' },
            { id: 'critical', label: 'Active Critical' },
            { id: 'warning', label: 'Active Warning' },
            { id: 'resolved', label: 'Resolved History' }
          ].map(btn => (
            <button
              key={btn.id}
              onClick={() => setFilterType(btn.id as any)}
              className={`text-xs px-3 py-1.5 rounded-lg border font-bold transition-all
                ${filterType === btn.id 
                  ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.1)]' 
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'}`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Alert List Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Logs Timeline (Col 8) */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
              Surveillance Incident Logs
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">
              Displaying {filteredAlerts.length} entries
            </span>
          </div>

          <div className="space-y-3">
            {filteredAlerts.length === 0 ? (
              <div className="cyber-glass p-12 text-center text-slate-500 text-xs font-mono">
                No active alerts for this event.
              </div>
            ) : (
              filteredAlerts.map((alert) => (
                <div 
                  key={alert.id} 
                  className={`p-4 rounded-xl border flex justify-between gap-4 transition-all duration-300 hover:scale-[1.005]
                    ${alert.resolved 
                      ? 'bg-slate-950/20 border-slate-900 opacity-60 hover:opacity-90' 
                      : alert.level === 'critical'
                        ? 'cyber-glass-red border-red-500/30' 
                        : 'cyber-glass border-amber-500/20'}`}
                >
                  <div className="flex gap-3">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 flex-shrink-0 w-max h-max">
                      <ShieldAlert className={`w-5 h-5
                        ${alert.resolved ? 'text-slate-500' : alert.level === 'critical' ? 'text-red-500 animate-pulse' : 'text-amber-500'}`} 
                      />
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase border
                          ${alert.resolved 
                            ? 'bg-slate-900 border-slate-800 text-slate-400' 
                            : alert.level === 'critical'
                              ? 'bg-red-950 border-red-500/20 text-red-400'
                              : 'bg-amber-950 border-amber-500/20 text-amber-400'}`}
                        >
                          {alert.resolved ? 'Resolved' : alert.level}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          {alert.timestamp} · Source: {alert.camera}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-white leading-snug">{alert.title}</h4>
                      <p className="text-xs text-slate-400 leading-normal max-w-xl">{alert.description}</p>
                      
                      <div className="pt-2 text-[10px] text-slate-500 font-mono">
                        Zone: <strong className="text-slate-300">{alert.zone}</strong>
                      </div>
                    </div>
                  </div>

                  {!alert.resolved && (
                    <button
                      onClick={() => resolveAlert(alert.id)}
                      className="p-1.5 h-max rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-green-400 border border-slate-800 transition-colors"
                      title="Clear / Resolve this alert"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Info Box Sidebar (Col 4) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
              Severity Matrix
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">Operations</span>
          </div>

          <div className="cyber-glass p-5 rounded-xl border border-blue-500/10 space-y-4">
            <div className="space-y-3.5 text-xs text-slate-400 leading-relaxed">
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider block">Critical (Red Alerts)</span>
                <p>Triggered automatically when camera density exceeds 90% or when the panic vector algorithm detects running anomalies. Dispatchers must action these within 30 seconds.</p>
              </div>

              <div className="space-y-1.5 pt-2 border-t border-slate-900/60">
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider block">Warning (Orange Alerts)</span>
                <p>Triggered when separation parameters exceed normal rules (e.g. child alone, restricted area breach). Renders local recommendation cards.</p>
              </div>

              <div className="space-y-1.5 pt-2 border-t border-slate-900/60">
                <span className="text-[10px] font-bold text-green-400 uppercase tracking-wider block">Resolved (Green Archive)</span>
                <p>Logged actions completed by dispatchers. Kept in session cache for compliance reports.</p>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-900 flex items-center justify-between text-[9px] text-slate-500 font-mono">
              <span className="flex items-center gap-1">
                <RefreshCw className="w-3.5 h-3.5 text-cyan-400" /> Database Live Sync
              </span>
              <span>100% Audit Clean</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
