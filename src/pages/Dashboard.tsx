import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { apiService } from '../services/api';
import { StatCard } from '../components/StatCard';
import { CameraCard } from '../components/CameraCard';
import { 
  Video, 
  Users, 
  Percent, 
  Activity, 
  AlertTriangle, 
  Clock,
  FileCheck,
  Plus,
  Siren,
  Layers,
  ChevronRight
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { 
    cameras, 
    alerts, 
    activeEmergencyEvent, 
    zones,
    areaSummary,
    currentEvent,
    events,
    selectedEventId
  } = useCrowdSystem();

  const [historicalTrends, setHistoricalTrends] = useState<any[]>([]);

  useEffect(() => {
    let active = true;
    const fetchTrend = () => {
      apiService.getCrowdAnalysis(undefined, selectedEventId)
        .then(res => {
          if (active && res && Array.isArray(res.hourly_trend) && res.hourly_trend.length > 0) {
            setHistoricalTrends(res.hourly_trend);
          }
        })
        .catch(() => {});
    };
    fetchTrend();
    const interval = setInterval(fetchTrend, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [selectedEventId]);

  const currentEvtObj = events.find(e => e.id === selectedEventId) || (events.length > 0 ? events[0] : null);

  // Analyzing cameras selection
  const analyzingCams = cameras.filter(c => c.enabled && (c.playbackStatus === 'analyzing' || c.playbackStatus === 'playing'));
  const totalCams = cameras.length;
  const currentCount = areaSummary.totalCount > 0 ? areaSummary.totalCount : analyzingCams.reduce((sum, c) => sum + (c.count || 0), 0);
  const totalCapacity = (currentEvtObj?.capacity && currentEvtObj.capacity > 0)
    ? currentEvtObj.capacity
    : (areaSummary.totalCapacity > 0 ? areaSummary.totalCapacity : (analyzingCams.reduce((sum, c) => sum + (c.capacity || 200), 0) || 5000));
  const occupancyPercent = totalCapacity > 0 ? Math.min(100, Math.round((currentCount / totalCapacity) * 100)) : 0;

  // Authoritative aggregate risk derived directly from backend risk evaluation engine
  const aggRisk: 'low' | 'medium' | 'high' | 'critical' = areaSummary.overallRisk || 'low';

  const riskGlows = {
    low: 'green' as const,
    medium: 'orange' as const,
    high: 'red' as const,
    critical: 'red' as const
  };

  const monitoredZones = zones.filter(z => z.is_monitored !== false);
  const unmonitoredZones = zones.filter(z => z.is_monitored === false);
  const staleCams = analyzingCams.filter(c => c.isTelemetryValid === false);

  // Real-time observations trend derived from crowd_analytics table without artificial multipliers
  const trendData = historicalTrends.length > 0
    ? historicalTrends.slice(-12).map((r: any) => ({
        time: r.timestamp || 'Live',
        count: r.count || 0,
        limit: totalCapacity
      }))
    : analyzingCams.length > 0 && currentCount > 0
    ? [
        { time: 'Live', count: currentCount, limit: totalCapacity }
      ]
    : [];

  const distributionData = analyzingCams.map(c => ({ name: c.name, value: c.count || 0 }));
  const COLORS = ['#06B6D4', '#3B82F6', '#8B5CF6', '#10B981', '#F59E0B'];

  return (
    <div className="space-y-6 font-mono">
      {/* Area-Wide Operational Venue Overview Bar */}
      <div className="p-4 rounded-xl cyber-glass border border-cyan-500/20 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-gradient-to-r from-cyan-950/20 via-slate-900/40 to-slate-950/60">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-widest text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-500/30">
                ACTIVE OPERATION AREA
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                {currentEvtObj?.venueName || 'Main Arena Complex'}
              </span>
            </div>
            <h2 className="text-base font-bold text-white tracking-wide mt-0.5">
              {currentEvent}
            </h2>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
            <span className="text-[10px] text-slate-500 block uppercase">Monitored Zones</span>
            <span className="font-bold text-slate-200">
              {monitoredZones.length} / {zones.length} Active
            </span>
          </div>
          {unmonitoredZones.length > 0 && (
            <div className="px-3 py-1.5 rounded-lg bg-amber-950/50 border border-amber-500/30 text-xs">
              <span className="text-[10px] text-amber-400 block uppercase font-bold">Unmonitored</span>
              <span className="font-bold text-amber-300">
                {unmonitoredZones.length} Blindspots
              </span>
            </div>
          )}
          <div className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
            <span className="text-[10px] text-slate-500 block uppercase">High Risk Zones</span>
            <span className={`font-bold ${areaSummary.highRiskZonesCount > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {areaSummary.highRiskZonesCount} Critical
            </span>
          </div>
          <button
            onClick={() => navigate('/venue-architecture')}
            className="py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-cyber-border text-xs text-cyan-400 hover:text-cyan-300 font-bold uppercase tracking-wider flex items-center gap-1 transition-all"
          >
            <span>Venue Map & Architecture</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Emergency Crisis Alert Banner */}
      {activeEmergencyEvent && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/60 text-red-200 flex justify-between items-center animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.2)]">
          <div className="flex items-center gap-3">
            <Siren className="w-6 h-6 text-red-500 animate-bounce" />
            <div>
              <h4 className="font-extrabold text-sm uppercase tracking-wide text-white">🚨 CRITICAL EMERGENCY ACTIVE</h4>
              <p className="text-xs text-red-300 font-semibold">{activeEmergencyEvent.incident_type} at {activeEmergencyEvent.location} ({activeEmergencyEvent.zone}).</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/emergency')}
            className="py-1.5 px-3 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-xs uppercase tracking-wider transition-all"
          >
            Emergency Console →
          </button>
        </div>
      )}

      {/* Stale Telemetry Warning Banner */}
      {staleCams.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/50 text-amber-200 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0" />
            <div>
              <h4 className="font-extrabold text-sm uppercase tracking-wide text-amber-300">⚠️ CAMERA TELEMETRY STALE ({staleCams.length} Feeds)</h4>
              <p className="text-xs text-amber-400/90 font-medium">
                Frame heartbeats halted (&gt;15s) for: <strong>{staleCams.map(c => c.name).join(', ')}</strong>. Backend safeguards suspend automated plan approvals for destinations with stale telemetry.
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/cameras')}
            className="py-1.5 px-3 rounded-lg bg-amber-700 hover:bg-amber-600 text-white font-bold text-xs uppercase tracking-wider transition-all shrink-0"
          >
            Inspect Cameras →
          </button>
        </div>
      )}

      {/* No Analyzing Camera Notification Banner */}
      {analyzingCams.length === 0 && (
        <div className="p-4 rounded-xl bg-cyan-950/40 border border-cyan-500/30 text-cyan-300 flex justify-between items-center text-xs">
          <div>
            <h4 className="font-bold text-sm text-white">No active video source</h4>
            <p className="text-[11px] text-slate-400 mt-0.5">
              0 detections. Go to Camera Access to register your CCTV video or click <strong>[ ANALYZE ]</strong> to start live computer vision telemetry.
            </p>
          </div>
          <button
            onClick={() => navigate('/cameras')}
            className="py-2 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all shadow-[0_0_12px_rgba(6,182,212,0.2)]"
          >
            <Plus className="w-4 h-4" /> Camera Access
          </button>
        </div>
      )}

      {/* Grid of Real Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Analyzing Feeds"
          value={analyzingCams.length > 0 ? `${analyzingCams.length} / ${totalCams}` : "No active video source"}
          icon={Video}
          glowColor={analyzingCams.length > 0 ? 'cyan' : 'orange'}
          subtext={analyzingCams.length > 0 ? `${totalCams - analyzingCams.length} cameras idle` : '0 detections'}
        />
        <StatCard
          title="Sensor-Derived Count"
          value={analyzingCams.length > 0 ? currentCount : "No live telemetry"}
          icon={Users}
          glowColor={analyzingCams.length > 0 ? "cyan" : "blue"}
          subtext={analyzingCams.length > 0 ? `Aggregated across ${analyzingCams.length} feeds (overlap estimated)` : '0 detections'}
        />
        <StatCard
          title="Capacity Occupancy"
          value={`${occupancyPercent}%`}
          icon={Percent}
          glowColor={occupancyPercent > 80 ? 'red' : 'blue'}
          subtext={`Limit: ${totalCapacity} slots`}
        />
        <StatCard
          title="System Risk Level"
          value={analyzingCams.length > 0 || activeEmergencyEvent ? aggRisk.toUpperCase() : "No current risk assessment"}
          icon={Activity}
          glowColor={analyzingCams.length > 0 || activeEmergencyEvent ? riskGlows[aggRisk] : "blue"}
          subtext={analyzingCams.length > 0 ? 'Calculated from YOLO' : 'No active video source'}
        />
      </div>

      {/* Charts Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Real Crowd Trend Chart */}
        <div className="lg:col-span-8 cyber-glass p-5 rounded-xl border border-blue-500/10 flex flex-col justify-between min-h-[350px]">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-900/60">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                Empirical Crowd Flow Trend Analysis
              </h3>
              <span className="text-[10px] text-slate-500">Observation-derived accumulation trend vs venue safety limit</span>
            </div>
            <span className="text-[10px] font-semibold text-cyan-400 bg-cyan-950/20 px-2 py-0.5 rounded border border-cyan-500/20">
              Trend Analysis
            </span>
          </div>

          <div className="w-full h-64 font-mono text-xs flex items-center justify-center">
            {analyzingCams.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#06B6D4" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                  <XAxis dataKey="time" stroke="#475569" />
                  <YAxis stroke="#475569" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#090d16', borderColor: 'rgba(59,130,246,0.2)', color: '#fff' }}
                    labelClassName="font-bold text-cyan-400 text-xs"
                  />
                  <Area type="monotone" dataKey="count" stroke="#06B6D4" fillOpacity={1} fill="url(#colorCount)" strokeWidth={2} name="Current Count" />
                  <Area type="monotone" dataKey="limit" stroke="#EF4444" fillOpacity={0} strokeDasharray="5 5" name="Safety Limit" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center text-slate-500 text-xs space-y-1">
                <p className="font-bold text-slate-400">No sufficient observations for trend analysis</p>
                <p className="text-[10px] text-slate-600">0 detections · Connect & Analyze a camera in Camera Access to plot live trends.</p>
              </div>
            )}
          </div>
        </div>

        {/* Real Distribution Pie Chart */}
        <div className="lg:col-span-4 cyber-glass p-5 rounded-xl border border-blue-500/10 flex flex-col justify-between min-h-[350px]">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200 mb-1">
              Crowd Density Distribution
            </h3>
            <span className="text-[10px] text-slate-500">Distribution of people across active cameras</span>
          </div>

          <div className="w-full h-52 flex justify-center items-center">
            {distributionData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={distributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    fill="#8884d8"
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {distributionData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: 'rgba(59,130,246,0.2)', color: '#fff' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center text-slate-500 text-xs">
                No active camera streams
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2 justify-center text-[10px] text-slate-400 pt-3 border-t border-slate-900/60 font-mono">
            {distributionData.map((d, i) => (
              <span key={i} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                {d.name}: {d.value}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Mini CCTV grid & Real Security Log */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Active Feeds Grid */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
              Active Camera Stream Feeds
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">Real computer vision bounding boxes</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {analyzingCams.length > 0 ? (
              analyzingCams.slice(0, 2).map(cam => (
                <CameraCard key={cam.id} camera={cam} />
              ))
            ) : (
              <div className="col-span-2 p-8 text-center bg-slate-950/60 rounded-xl border border-slate-900 text-slate-500 text-xs space-y-1">
                <p className="font-bold text-slate-400">No active video source</p>
                <p className="text-[10px] text-slate-600">0 detections · Select or connect a camera stream in Camera Access.</p>
              </div>
            )}
          </div>
        </div>

        {/* Real Security Log */}
        <div className="lg:col-span-4 cyber-glass p-5 rounded-xl border border-blue-500/10 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-900/60 pb-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                AI Incident Security Log
              </h3>
              <AlertTriangle className="w-4 h-4 text-orange-400" />
            </div>

            <div className="space-y-3 max-h-[260px] overflow-y-auto pr-1">
              {alerts.length > 0 ? (
                alerts.slice(0, 5).map(alert => (
                  <div key={alert.id} className="p-3 bg-slate-950/40 rounded-lg border border-slate-900 flex gap-2 text-xs">
                    <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0
                      ${alert.level === 'critical' ? 'bg-red-500 animate-ping' : 'bg-orange-500'}`} 
                    />
                    <div className="space-y-1">
                      <p className="font-semibold text-white leading-tight">{alert.title}</p>
                      <p className="text-[10px] text-slate-400 leading-normal">{alert.description}</p>
                      <span className="text-[9px] text-slate-600 block font-mono">{alert.timestamp} · {alert.zone}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-slate-500 text-xs font-mono">
                  No active alerts
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-900/60 flex items-center justify-between text-[10px] text-slate-500 font-semibold">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-cyan-400" /> MySQL Sync
            </span>
            <span className="flex items-center gap-1">
              <FileCheck className="w-3.5 h-3.5 text-cyan-400" /> Audit Verified
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
