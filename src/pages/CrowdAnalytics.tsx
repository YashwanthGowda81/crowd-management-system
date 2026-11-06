import React, { useState, useEffect } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { apiService } from '../services/api';
import { 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  Legend, 
  AreaChart, 
  Area,
  BarChart,
  Bar
} from 'recharts';
import { TrendingUp, Calendar, AlertCircle, Camera as CameraIcon, Activity } from 'lucide-react';
import { GlassCard } from '../components/GlassCard';

export const CrowdAnalytics: React.FC = () => {
  const { cameras, activeCameraId, setActiveCameraId, selectedEventId } = useCrowdSystem();
  const [selectedCamId, setSelectedCamId] = useState<string>(activeCameraId || (cameras[0]?.id || ''));
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const selectedCam = cameras.find(c => c.id === (selectedCamId || activeCameraId)) || cameras[0];

  useEffect(() => {
    const targetId = selectedCamId || activeCameraId || cameras[0]?.id;
    if (!targetId) {
      setAnalyticsData(null);
      return;
    }

    setLoading(true);
    apiService.getCrowdAnalysis(targetId, selectedEventId)
      .then(res => {
        if (res) {
          setAnalyticsData(res);
        }
      })
      .catch(err => console.error("Error loading crowd analytics:", err))
      .finally(() => setLoading(false));
  }, [selectedCamId, activeCameraId, cameras.length, selectedEventId]);

  const trends = analyticsData?.hourly_trend || [];

  return (
    <div className="space-y-6 font-mono">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-cyber-border/40">
        <div>
          <h2 className="text-base font-extrabold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <CameraIcon className="w-5 h-5 text-cyan-400" />
            <span>Computer Vision Crowd Analytics (Database Log)</span>
          </h2>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Automated statistics derived exclusively from actual YOLO detections stored in MySQL <code className="text-cyan-400">crowd_analytics</code> table.
          </p>
        </div>

        {/* Camera Scoped Selection Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Select Camera:</span>
          <select
            value={selectedCamId || selectedCam?.id || ''}
            onChange={(e) => {
              setSelectedCamId(e.target.value);
              setActiveCameraId(e.target.value);
            }}
            className="px-3.5 py-2 rounded-lg bg-slate-950 border border-cyber-border text-xs text-white focus:outline-none focus:border-cyan-500 font-bold"
          >
            {cameras.length === 0 ? (
              <option value="">No cameras registered</option>
            ) : (
              cameras.map(c => (
                <option key={c.id} value={c.id}>
                  📹 {c.name} ({c.sourceType.toUpperCase()})
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Selected Camera Metrics Summary Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-xs font-mono">
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-900">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 block mb-1">Target Camera</span>
          <span className="text-sm font-bold text-white truncate block">{selectedCam ? selectedCam.name : 'No active video source'}</span>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-900">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 block mb-1">Detections</span>
          <span className="text-sm font-bold text-cyan-400">
            {selectedCam && selectedCam.playbackStatus === 'analyzing' && selectedCam.count ? `${selectedCam.count} persons` : '0 detections'}
          </span>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-900">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 block mb-1">Calculated Density</span>
          <span className="text-sm font-bold text-yellow-400">
            {selectedCam && selectedCam.playbackStatus === 'analyzing' ? `${selectedCam.density ?? 0}%` : '0%'}
          </span>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-900">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 block mb-1">Exit Rate Metric</span>
          <span className="text-xs font-bold text-slate-400 truncate block">
            {analyticsData?.exit_rate_per_min != null ? `${analyticsData.exit_rate_per_min} /min` : (analyticsData?.outflow_status || "No live telemetry")}
          </span>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-900">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 block mb-1">Camera Speed Metric</span>
          <span className="text-xs font-bold text-slate-400 truncate block">
            {analyticsData?.speed_status || "No live telemetry"}
          </span>
        </div>
      </div>

      {/* EMPTY DATA STATE */}
      {trends.length === 0 ? (
        <GlassCard className="p-12 text-center space-y-3 border border-slate-900 font-mono">
          <Activity className="w-10 h-10 mx-auto text-slate-600" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">No sufficient observations for trend analysis</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            {loading 
              ? 'Querying crowd_analytics database...' 
              : 'No live telemetry recorded yet. 0 detections. Click [ ANALYZE ] on your camera stream in Camera Access to continuously record real YOLO observations.'}
          </p>
        </GlassCard>
      ) : (
        /* REAL ANALYTICAL CHARTS DIRECTLY PLOTTING MYSQL RECORDS */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Chart 1: Real Crowd Count & Density Log over Time */}
          <div className="lg:col-span-8 cyber-glass p-5 rounded-xl border border-blue-500/10 flex flex-col justify-between min-h-[350px]">
            <div className="flex items-center justify-between mb-4 border-b border-slate-900 pb-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                  Actual Crowd Count & Density Timeline ({trends.length} DB Snapshots)
                </h3>
                <span className="text-[10px] text-slate-500">Real records queried from MySQL crowd_analytics</span>
              </div>
              <TrendingUp className="w-4 h-4 text-cyan-400" />
            </div>

            <div className="w-full h-64 font-mono text-xs">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                  <XAxis dataKey="timestamp" stroke="#475569" />
                  <YAxis stroke="#475569" />
                  <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: 'rgba(59,130,246,0.2)', color: '#fff' }} />
                  <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }} />
                  <Line type="monotone" dataKey="count" stroke="#06B6D4" strokeWidth={2} name="Person Count" activeDot={{ r: 6 }} />
                  <Line type="monotone" dataKey="density_pct" stroke="#F59E0B" strokeWidth={2} name="Density %" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Real Density Risk Bar Profile */}
          <div className="lg:col-span-4 cyber-glass p-5 rounded-xl border border-blue-500/10 flex flex-col justify-between min-h-[350px]">
            <div className="flex items-center justify-between mb-4 border-b border-slate-900 pb-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                  Logged Density Profile
                </h3>
                <span className="text-[10px] text-slate-500">Density % across recent frames</span>
              </div>
              <AlertCircle className="w-4 h-4 text-yellow-400" />
            </div>

            <div className="w-full h-56 font-mono text-xs">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trends.slice(-10)} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                  <XAxis dataKey="timestamp" stroke="#475569" />
                  <YAxis stroke="#475569" />
                  <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: 'rgba(59,130,246,0.2)', color: '#fff' }} />
                  <Bar dataKey="density_pct" fill="#06B6D4" radius={[4, 4, 0, 0]} name="Density %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 3: Real Flow Rate Timeline */}
          <div className="lg:col-span-12 cyber-glass p-5 rounded-xl border border-blue-500/10 flex flex-col justify-between min-h-[300px]">
            <div className="flex items-center justify-between mb-4 border-b border-slate-900 pb-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                  Optical Centroid Displacement Flow Rate (Persons / sec)
                </h3>
                <span className="text-[10px] text-slate-500">Real tracked centroid movement rate from video pipeline</span>
              </div>
              <Calendar className="w-4 h-4 text-cyan-400" />
            </div>

            <div className="w-full h-56 font-mono text-xs">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorFlow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                  <XAxis dataKey="timestamp" stroke="#475569" />
                  <YAxis stroke="#475569" />
                  <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: 'rgba(59,130,246,0.2)', color: '#fff' }} />
                  <Area type="monotone" dataKey="flow_rate" stroke="#10B981" fillOpacity={1} fill="url(#colorFlow)" strokeWidth={2} name="Flow Rate (persons/s)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
