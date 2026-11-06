
import React, { useState, useEffect, useRef } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { GlassCard } from '../components/GlassCard';
import { apiService } from '../services/api';
import { 
  Flame, 
  MapPin, 
  Layers, 
  Camera, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  RefreshCw, 
  AlertCircle, 
  Info, 
  Sliders, 
  Upload, 
  ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface HeatmapPin {
  id: string;
  label: string;
  pin_type: string;
  x: number;
  y: number;
  camera_id?: string | null;
  count?: number;
  density?: number;
  risk?: string;
  profile?: string;
  is_active?: boolean;
  is_stale?: boolean;
  observation_timestamp?: string | null;
}

interface HeatmapZone {
  id: string;
  name: string;
  code: string;
  capacity: number;
  current_count: number;
  density: number;
  risk_level: string;
  zone_type: string;
  assigned_cameras_count: number;
  coordinates?: string | null;
}

interface HeatmapCamera {
  id: string;
  name: string;
  location: string;
  zone_id?: string | null;
  status: string;
  playback_status: string;
  count: number;
  capacity: number;
  density: number;
  risk: string;
  profile?: string;
  is_active: boolean;
  is_stale?: boolean;
  observation_timestamp?: string | null;
  pin_mapped: boolean;
  pin_x?: number | null;
  pin_y?: number | null;
}

interface VenueHeatmapData {
  event_id: string;
  event_title: string;
  venue_name: string;
  map_url?: string | null;
  total_occupancy: number;
  venue_capacity: number;
  overall_density_pct: number;
  overall_risk: string;
  overall_profile?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  active_cameras_count: number;
  total_cameras_count: number;
  spatial_mapping_mode: string;
  heatmap_overlay_base64?: string;
  pins: HeatmapPin[];
  zones: HeatmapZone[];
  cameras: HeatmapCamera[];
  last_updated: string;
  telemetry_mode?: 'LIVE' | 'STALE' | 'DEMO' | 'NO_DATA';
  demo_scenario?: string | null;
  status: 'live' | 'idle' | 'no_map' | 'no_event' | 'demo';
}

export const HeatmapPage: React.FC = () => {
  const { 
    events, 
    selectedEventId, 
    setSelectedEventId,
    uploadVenueMapFile
  } = useCrowdSystem();

  const [heatmapData, setHeatmapData] = useState<VenueHeatmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [demoScenario, setDemoScenario] = useState<string>('live');

  // Visualization Toggles & Customization
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showCameraPins, setShowCameraPins] = useState(true);
  const [showFacilityPins, setShowFacilityPins] = useState(true);
  const [heatmapOpacity, setHeatmapOpacity] = useState<number>(0.75);
  const [selectedPinCategory, setSelectedPinCategory] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<'zones' | 'cameras'>('zones');

  // Map Zoom & Pan State
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const mapContainerRef = useRef<HTMLDivElement>(null);

  // File upload state for no-map empty state
  const [isUploading, setIsUploading] = useState(false);

  const currentEvent = events.find(e => e.id === selectedEventId) || events[0];

  // Fetch venue heatmap overlay data
  const fetchHeatmap = async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    try {
      const data = await apiService.getVenueHeatmapOverlay(selectedEventId || undefined, demoScenario);
      setHeatmapData(data);
      setFetchError(null);
    } catch (err: any) {
      const isNetworkErr = !err.status && (
        err.message?.includes('Failed to fetch') || 
        err.message?.includes('NetworkError') || 
        err.name === 'TypeError'
      );
      const errorMsg = isNetworkErr
        ? 'Backend surveillance service unreachable (http://localhost:8000). Ensure the FastAPI server is running.'
        : (err.message || 'Failed to acquire live venue heatmap data');
      setFetchError(errorMsg);
    } finally {
      setLoading(false);
      if (isManualRefresh) setRefreshing(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    // Reset pan/zoom on event change
    setZoomLevel(1.0);
    setPanOffset({ x: 0, y: 0 });
    fetchHeatmap();

    // Auto-refresh interval (every 1.5 seconds)
    const interval = setInterval(() => {
      fetchHeatmap(false);
    }, 1500);

    return () => clearInterval(interval);
  }, [selectedEventId, demoScenario]);

  // Zoom & Pan Handlers
  const handleZoomIn = () => setZoomLevel(prev => Math.min(3.5, Number((prev + 0.25).toFixed(2))));
  const handleZoomOut = () => setZoomLevel(prev => Math.max(0.6, Number((prev - 0.25).toFixed(2))));
  const handleResetZoom = () => {
    setZoomLevel(1.0);
    setPanOffset({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPanOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  // File upload directly from empty state
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setIsUploading(true);
      try {
        await uploadVenueMapFile(file);
        await fetchHeatmap(true);
      } finally {
        setIsUploading(false);
      }
    }
  };

  // Helper for pin styling
  const getPinColor = (type: string, risk?: string) => {
    if (type === 'camera') {
      if (risk === 'critical') return 'bg-rose-600 text-white border-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.6)] animate-pulse';
      if (risk === 'high') return 'bg-orange-600 text-white border-orange-300 shadow-[0_0_12px_rgba(249,115,22,0.6)]';
      if (risk === 'medium') return 'bg-amber-600 text-white border-amber-300';
      return 'bg-cyan-600 text-white border-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.4)]';
    }
    if (type === 'gate_entry') return 'bg-emerald-600 text-white border-emerald-300';
    if (type === 'gate_exit') return 'bg-blue-600 text-white border-blue-300';
    if (type === 'emergency_exit') return 'bg-red-600 text-white border-red-300';
    if (type === 'security') return 'bg-purple-600 text-white border-purple-300';
    return 'bg-slate-700 text-white border-slate-400';
  };

  // Filter pins
  const displayedPins = (heatmapData?.pins || []).filter(p => {
    if (p.pin_type === 'camera' && !showCameraPins) return false;
    if (p.pin_type !== 'camera' && !showFacilityPins) return false;
    if (selectedPinCategory !== 'all') {
      if (selectedPinCategory === 'camera') return p.pin_type === 'camera';
      if (selectedPinCategory === 'gates') return p.pin_type === 'gate_entry' || p.pin_type === 'gate_exit';
      if (selectedPinCategory === 'emergency') return p.pin_type === 'emergency_exit';
      if (selectedPinCategory === 'security') return p.pin_type === 'security';
    }
    return true;
  });

  const overallRisk = heatmapData?.overall_risk || 'low';
  const riskColor = 
    overallRisk === 'critical' ? 'text-rose-400 bg-rose-950/60 border-rose-500/40' :
    overallRisk === 'high' ? 'text-orange-400 bg-orange-950/60 border-orange-500/40' :
    overallRisk === 'medium' ? 'text-amber-400 bg-amber-950/60 border-amber-500/40' :
    'text-emerald-400 bg-emerald-950/60 border-emerald-500/40';

  const isNoMap = heatmapData?.status === 'no_map' || !heatmapData?.map_url;

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
      {/* Page Header with Mode Indicator & Scenario Selector */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-900 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.3)]">
              <Flame className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl md:text-2xl font-black text-white uppercase tracking-wider">
                  Crowd Density Heatmap
                </h1>
                {/* Prominent Mode Indicator Badge */}
                {heatmapData?.telemetry_mode === 'DEMO' ? (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase font-mono bg-purple-950/90 text-purple-300 border border-purple-500/50 shadow-[0_0_10px_rgba(168,85,247,0.4)] flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                    DEMO BENCHMARK
                  </span>
                ) : heatmapData?.telemetry_mode === 'LIVE' ? (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase font-mono bg-emerald-950/90 text-emerald-300 border border-emerald-500/50 shadow-[0_0_10px_rgba(16,185,129,0.4)] flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                    LIVE SURVEILLANCE
                  </span>
                ) : heatmapData?.telemetry_mode === 'STALE' ? (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase font-mono bg-amber-950/90 text-amber-300 border border-amber-500/50 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    STALE TELEMETRY (Awaiting Frames)
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase font-mono bg-slate-900 text-slate-400 border border-slate-700 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                    NO SENSOR TELEMETRY
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Real-time spatial density gradients overlaid directly on the verified venue architectural blueprint
              </p>
            </div>
          </div>
        </div>

        {/* Mode & Event Selectors */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Demonstration Scenario Selector */}
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
            <span className="text-[10px] font-mono uppercase text-slate-500">Mode:</span>
            <select
              value={demoScenario}
              onChange={(e) => setDemoScenario(e.target.value)}
              className={`bg-transparent text-xs font-bold focus:outline-none cursor-pointer ${
                demoScenario === 'live' ? 'text-emerald-400' : 'text-purple-400'
              }`}
            >
              <option value="live" className="bg-slate-900 text-emerald-400 font-bold">
                ● Live Surveillance Telemetry (Real YOLO)
              </option>
              <option value="sparse" className="bg-slate-900 text-cyan-400">
                Demo A: Sparse Occupancy (&lt;45% Low / Blue-Cyan)
              </option>
              <option value="moderate" className="bg-slate-900 text-yellow-400">
                Demo B: Moderate Entrance (45-74% Med / Green-Yellow)
              </option>
              <option value="dense_hall" className="bg-slate-900 text-orange-400">
                Demo C: Dense Main Hall (75-89% High / Yellow-Orange)
              </option>
              <option value="critical_corridor" className="bg-slate-900 text-rose-400">
                Demo D: Critical Choke-Point (≥90% Crit / Red-Crimson)
              </option>
            </select>
          </div>

          {events.length > 0 && (
            <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono uppercase text-slate-500">Event:</span>
              <select
                value={selectedEventId}
                onChange={(e) => setSelectedEventId(e.target.value)}
                className="bg-transparent text-xs font-bold text-cyan-400 focus:outline-none cursor-pointer"
              >
                {events.map(ev => (
                  <option key={ev.id} value={ev.id} className="bg-slate-900 text-white">
                    {ev.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => fetchHeatmap(true)}
            disabled={refreshing}
            className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-bold text-xs flex items-center gap-1.5 border border-slate-800 hover:border-cyan-500/40 transition-all cursor-pointer"
            title="Refresh Heatmap Snapshot"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>

          <Link
            to="/venue-architecture"
            className="px-3.5 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all shadow-[0_0_12px_rgba(6,182,212,0.3)]"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Manage Blueprint & Pins</span>
          </Link>
        </div>
      </div>

      {/* 4-Profile Visual Calibration Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 text-xs font-mono">
        <div className={`p-2.5 rounded-xl border flex items-center gap-2.5 transition-all ${
          heatmapData?.overall_profile === 'LOW' 
            ? 'bg-blue-950/70 border-cyan-400/60 shadow-[0_0_10px_rgba(6,182,212,0.3)] ring-1 ring-cyan-400/40' 
            : 'bg-slate-950/50 border-slate-800/80 text-slate-400'
        }`}>
          <div className="w-4 h-4 rounded-md bg-gradient-to-r from-blue-600 to-cyan-400 shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] font-black uppercase tracking-wider text-cyan-300">Profile A: LOW (&lt;45%)</div>
            <div className="text-[9px] text-slate-400 truncate">Cool Blue / Cyan localized blooms</div>
          </div>
        </div>

        <div className={`p-2.5 rounded-xl border flex items-center gap-2.5 transition-all ${
          heatmapData?.overall_profile === 'MEDIUM' 
            ? 'bg-yellow-950/70 border-yellow-400/60 shadow-[0_0_10px_rgba(234,179,8,0.3)] ring-1 ring-yellow-400/40' 
            : 'bg-slate-950/50 border-slate-800/80 text-slate-400'
        }`}>
          <div className="w-4 h-4 rounded-md bg-gradient-to-r from-cyan-400 via-green-400 to-yellow-400 shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] font-black uppercase tracking-wider text-yellow-300">Profile B: MEDIUM (45-74%)</div>
            <div className="text-[9px] text-slate-400 truncate">Cyan / Green / Yellow hotspots</div>
          </div>
        </div>

        <div className={`p-2.5 rounded-xl border flex items-center gap-2.5 transition-all ${
          heatmapData?.overall_profile === 'HIGH' 
            ? 'bg-orange-950/70 border-orange-400/60 shadow-[0_0_10px_rgba(249,115,22,0.3)] ring-1 ring-orange-400/40' 
            : 'bg-slate-950/50 border-slate-800/80 text-slate-400'
        }`}>
          <div className="w-4 h-4 rounded-md bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500 shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] font-black uppercase tracking-wider text-orange-300">Profile C: HIGH (75-89%)</div>
            <div className="text-[9px] text-slate-400 truncate">Yellow / Orange / Red hotspots</div>
          </div>
        </div>

        <div className={`p-2.5 rounded-xl border flex items-center gap-2.5 transition-all ${
          heatmapData?.overall_profile === 'CRITICAL' 
            ? 'bg-rose-950/70 border-rose-400/60 shadow-[0_0_10px_rgba(244,63,94,0.3)] ring-1 ring-rose-400/40 animate-pulse' 
            : 'bg-slate-950/50 border-slate-800/80 text-slate-400'
        }`}>
          <div className="w-4 h-4 rounded-md bg-gradient-to-r from-orange-500 via-red-600 to-rose-700 shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] font-black uppercase tracking-wider text-rose-300">Profile D: CRITICAL (≥90%)</div>
            <div className="text-[9px] text-slate-400 truncate">Intense Red / Crimson surge</div>
          </div>
        </div>
      </div>

      {/* Spatial Mapping Integrity Notice */}
      <div className="p-3.5 rounded-xl bg-slate-900/70 border border-cyan-500/20 backdrop-blur-sm flex items-start sm:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-start sm:items-center gap-2.5">
          <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5 sm:mt-0" />
          <p className="text-slate-300 text-[11px] leading-relaxed">
            <strong className="text-cyan-400 uppercase tracking-wider">Spatial Methodology:</strong> Live YOLOv8n detections are aggregated via monitored operational zones and verified venue camera markers. Image pixel boxes are not artificially distorted across the map.
          </p>
        </div>
        <span className="hidden lg:inline text-[10px] bg-cyan-950 text-cyan-300 px-2.5 py-0.5 rounded-md border border-cyan-500/30 whitespace-nowrap">
          Event Scoped: {currentEvent?.title || 'Active Event'}
        </span>
      </div>

      {fetchError && (
        <div className="p-3.5 rounded-xl bg-rose-950/80 border border-rose-500/50 text-rose-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono shadow-[0_0_12px_rgba(244,63,94,0.2)]">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span><strong>Heatmap Telemetry Error:</strong> {fetchError}</span>
          </div>
          <button
            onClick={() => fetchHeatmap(true)}
            className="px-3 py-1 rounded-lg bg-rose-900/60 hover:bg-rose-800 border border-rose-400/40 text-rose-200 font-bold transition-all text-[11px] cursor-pointer whitespace-nowrap"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Top Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3.5">
        <GlassCard className="p-3.5 flex flex-col justify-between">
          <span className="text-[10px] text-slate-400 uppercase font-mono">Total Venue Occupancy</span>
          <div className="text-xl font-black text-cyan-400 mt-1 flex items-baseline gap-1.5">
            <span>{heatmapData?.total_occupancy ?? 0}</span>
            <span className="text-[10px] font-mono text-slate-500 font-normal">people</span>
          </div>
          <span className="text-[9px] text-slate-500 font-mono mt-0.5">Sum of real detector counts</span>
        </GlassCard>

        <GlassCard className="p-3.5 flex flex-col justify-between">
          <span className="text-[10px] text-slate-400 uppercase font-mono">Venue Crowd Density</span>
          <div className="text-xl font-black text-white mt-1">
            {heatmapData?.overall_density_pct ? `${heatmapData.overall_density_pct}%` : '0.0%'}
          </div>
          <span className="text-[9px] text-slate-500 font-mono mt-0.5">
            Capacity: {heatmapData?.venue_capacity ? heatmapData.venue_capacity.toLocaleString() : '1,000'}
          </span>
        </GlassCard>

        <GlassCard className="p-3.5 flex flex-col justify-between">
          <span className="text-[10px] text-slate-400 uppercase font-mono">Overall Spatial Risk</span>
          <div className="mt-1">
            <span className={`inline-block px-2.5 py-0.5 rounded text-xs font-black uppercase font-mono border ${riskColor}`}>
              {overallRisk} RISK
            </span>
          </div>
          <span className="text-[9px] text-slate-500 font-mono mt-0.5">
            {overallRisk === 'critical' ? 'Evacuation protocol threshold' : overallRisk === 'high' ? 'Capacity bottleneck' : 'Circulation safe'}
          </span>
        </GlassCard>

        <GlassCard className="p-3.5 flex flex-col justify-between">
          <span className="text-[10px] text-slate-400 uppercase font-mono">Active Surveillance Streams</span>
          <div className="text-xl font-black text-emerald-400 mt-1 flex items-baseline gap-1">
            <span>{heatmapData?.active_cameras_count ?? 0}</span>
            <span className="text-xs font-normal text-slate-500">/ {heatmapData?.total_cameras_count ?? 0} online</span>
          </div>
          <span className="text-[9px] text-slate-500 font-mono mt-0.5">Live video pipelines</span>
        </GlassCard>

        <GlassCard className="col-span-2 md:col-span-4 lg:col-span-1 p-3.5 flex flex-col justify-between">
          <span className="text-[10px] text-slate-400 uppercase font-mono">Telemetry Status</span>
          <div className="mt-1 flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${
              fetchError ? 'bg-rose-500 animate-pulse' :
              heatmapData?.telemetry_mode === 'LIVE' ? 'bg-emerald-400 animate-pulse' :
              heatmapData?.telemetry_mode === 'DEMO' ? 'bg-purple-400 animate-pulse' :
              heatmapData?.telemetry_mode === 'STALE' ? 'bg-amber-400' :
              isNoMap ? 'bg-amber-400' : 'bg-slate-500'
            }`} />
            <span className="text-xs font-bold text-white font-mono uppercase">
              {fetchError ? 'DISCONNECTED' :
               heatmapData?.telemetry_mode === 'DEMO' ? 'DEMO BENCHMARK' :
               heatmapData?.telemetry_mode === 'LIVE' ? 'LIVE STREAMING' :
               heatmapData?.telemetry_mode === 'STALE' ? 'STALE TELEMETRY' :
               isNoMap ? 'NO BLUEPRINT' : 'STANDBY / READY'}
            </span>
          </div>
          <span className="text-[9px] text-slate-500 font-mono mt-0.5">
            {fetchError ? 'Check port 8000' : (heatmapData?.last_updated ? new Date(heatmapData.last_updated).toLocaleTimeString() : 'Not available')}
          </span>
        </GlassCard>
      </div>

      {/* Main Heatmap Visualization Section */}
      <GlassCard className="p-4 md:p-6 space-y-4">
        {/* Toolbar: Layers, Zoom, Filters, Opacity */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono border-b border-slate-800 pb-3">
          {/* Left: Layer Toggles */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setShowHeatmap(!showHeatmap)}
              className={`px-3 py-1.5 rounded-lg border font-bold flex items-center gap-1.5 transition-all cursor-pointer
                ${showHeatmap 
                  ? 'bg-amber-950/70 border-amber-500/50 text-amber-300 shadow-[0_0_8px_rgba(245,158,11,0.2)]' 
                  : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300'}`}
              title="Toggle transparent crowd density heat gradient"
            >
              <Flame className="w-3.5 h-3.5" />
              <span>Heatmap Overlay</span>
            </button>

            <button
              onClick={() => setShowCameraPins(!showCameraPins)}
              className={`px-3 py-1.5 rounded-lg border font-bold flex items-center gap-1.5 transition-all cursor-pointer
                ${showCameraPins 
                  ? 'bg-cyan-950/70 border-cyan-500/50 text-cyan-300' 
                  : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300'}`}
              title="Toggle CCTV camera markers on blueprint"
            >
              <Camera className="w-3.5 h-3.5" />
              <span>Camera Pins ({heatmapData?.cameras?.length || 0})</span>
            </button>

            <button
              onClick={() => setShowFacilityPins(!showFacilityPins)}
              className={`px-3 py-1.5 rounded-lg border font-bold flex items-center gap-1.5 transition-all cursor-pointer
                ${showFacilityPins 
                  ? 'bg-purple-950/70 border-purple-500/50 text-purple-300' 
                  : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300'}`}
              title="Toggle Entry, Exit, and Security facility markers"
            >
              <MapPin className="w-3.5 h-3.5" />
              <span>Facility Pins</span>
            </button>

            {/* Pin Category Filter */}
            <div className="flex items-center gap-1.5 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500">Filter:</span>
              <select
                value={selectedPinCategory}
                onChange={(e) => setSelectedPinCategory(e.target.value)}
                className="bg-transparent text-[11px] font-bold text-slate-300 focus:outline-none cursor-pointer"
                title="Filter pins displayed on blueprint"
              >
                <option value="all" className="bg-slate-900 text-white">All Pins</option>
                <option value="camera" className="bg-slate-900 text-white">Cameras Only</option>
                <option value="gates" className="bg-slate-900 text-white">Access Gates</option>
                <option value="emergency" className="bg-slate-900 text-white">Emergency Exits</option>
                <option value="security" className="bg-slate-900 text-white">Security Posts</option>
              </select>
            </div>

            {/* Opacity Slider */}
            {showHeatmap && (
              <div className="flex items-center gap-2 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
                <Sliders className="w-3 h-3 text-slate-500" />
                <span className="text-[10px] text-slate-400">Opacity:</span>
                <input
                  type="range"
                  min="0.2"
                  max="1.0"
                  step="0.05"
                  value={heatmapOpacity}
                  onChange={(e) => setHeatmapOpacity(parseFloat(e.target.value))}
                  className="w-16 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
                <span className="text-[10px] text-cyan-400 font-bold w-7">
                  {Math.round(heatmapOpacity * 100)}%
                </span>
              </div>
            )}
          </div>

          {/* Right: Zoom & Pan Controls */}
          <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={handleZoomIn}
              disabled={zoomLevel >= 3.5}
              className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-cyan-400 font-bold text-xs flex items-center gap-1 transition-all cursor-pointer"
              title="Zoom In (+)"
            >
              <ZoomIn className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Zoom In</span>
            </button>
            <button
              onClick={handleZoomOut}
              disabled={zoomLevel <= 0.6}
              className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-cyan-400 font-bold text-xs flex items-center gap-1 transition-all cursor-pointer"
              title="Zoom Out (−)"
            >
              <ZoomOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Zoom Out</span>
            </button>
            <button
              onClick={handleResetZoom}
              className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 font-semibold text-xs flex items-center gap-1 transition-all cursor-pointer"
              title="Reset View (100%)"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset ({Math.round(zoomLevel * 100)}%)</span>
            </button>
          </div>
        </div>

        {/* Viewport for Venue Map & Heatmap Overlay */}
        {loading && !heatmapData ? (
          <div className="h-[520px] w-full rounded-xl bg-slate-950 border border-slate-800 flex flex-col items-center justify-center gap-3 text-slate-400 font-mono text-xs">
            <RefreshCw className="w-8 h-8 animate-spin text-cyan-400" />
            <p>Loading architectural venue blueprint & crowd telemetry...</p>
          </div>
        ) : isNoMap ? (
          /* EMPTY STATE: No Venue Map Uploaded for this event */
          <div className="p-12 text-center space-y-6 max-w-2xl mx-auto border-2 border-dashed border-cyan-500/30 rounded-2xl bg-slate-950/60 my-6">
            <div className="w-16 h-16 rounded-full bg-cyan-950/60 border border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.2)]">
              <Layers className="w-8 h-8" />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-black text-white uppercase tracking-wider">
                No Venue Map Configured for {currentEvent?.title || 'This Event'}
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed font-mono">
                To visualize spatial crowd density and camera heat gradients, upload an architectural floorplan, CAD layout, or venue diagram.
              </p>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
              <label className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all cursor-pointer inline-flex items-center gap-2 shadow-[0_0_15px_rgba(6,182,212,0.3)]">
                <Upload className="w-4 h-4" />
                <span>{isUploading ? 'Uploading...' : 'Upload Venue Map File'}</span>
                <input 
                  type="file" 
                  accept="image/png, image/jpeg, image/jpg, image/webp"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  className="hidden" 
                />
              </label>

              <Link
                to="/venue-architecture"
                className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 font-bold text-xs uppercase tracking-wider transition-all inline-flex items-center gap-2"
              >
                <span>Go to Venue Architecture</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        ) : (
          /* ACTUAL VENUE MAP CONTAINER (Main Focus) */
          <div className="relative w-full rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl">
            {/* Explanatory banner if event has map, but no active dynamic heatmap overlay */}
            {showHeatmap && !heatmapData?.heatmap_overlay_base64 && (
              <div className="p-3 bg-amber-950/70 border-b border-amber-500/30 text-amber-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs font-mono px-4">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>
                    <strong>Spatial Telemetry:</strong>{' '}
                    {(heatmapData?.cameras?.length || 0) === 0
                      ? 'No surveillance cameras configured for this event. Add cameras in Camera Setup to enable spatial density monitoring.'
                      : (heatmapData?.pins || []).filter(p => p.pin_type === 'camera').length === 0
                        ? 'Surveillance cameras exist, but no camera positions have been mapped on this blueprint. Place camera pins in Venue Architecture.'
                        : 'Mapped cameras report 0 active crowd detections. Heatmap overlay appears dynamically when crowd counts are detected.'}
                  </span>
                </div>
                {(heatmapData?.pins || []).filter(p => p.pin_type === 'camera').length === 0 && (
                  <Link
                    to="/venue-architecture"
                    className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/40 text-amber-200 font-bold whitespace-nowrap transition-colors text-[11px]"
                  >
                    Map Camera Pins &rarr;
                  </Link>
                )}
              </div>
            )}

            <div 
              ref={mapContainerRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={(e) => {
                e.preventDefault();
                if (e.deltaY < 0) handleZoomIn();
                else handleZoomOut();
              }}
              style={{ minHeight: '520px', maxHeight: '720px' }}
              className={`relative w-full overflow-hidden flex items-center justify-center select-none ${
                zoomLevel > 1 ? (isDragging ? 'cursor-grabbing' : 'cursor-grab') : 'cursor-default'
              }`}
            >
              {/* Scaled & Translated Map + Heatmap Layer (Locked in exact lockstep) */}
              <div
                style={{
                  transform: `scale(${zoomLevel}) translate(${panOffset.x / zoomLevel}px, ${panOffset.y / zoomLevel}px)`,
                  transformOrigin: 'center center',
                  transition: isDragging ? 'none' : 'transform 0.12s ease-out'
                }}
                className="relative inline-block max-w-full pointer-events-auto"
              >
                {/* 1. Underlying Verified Architectural Blueprint (Base layer: z-0) */}
                <img 
                  src={heatmapData?.map_url || ''} 
                  alt="Verified Venue Floorplan Blueprint" 
                  draggable={false}
                  className="w-full h-auto block object-contain filter contrast-105 pointer-events-none select-none z-0"
                />

                {/* 2. Precision Metric Coordinate Grid (z-0) */}
                <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.06)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none z-0" />

                {/* 3. Live Heatmap Gradient Overlay (Above floorplan, below pins: z-10) */}
                {showHeatmap && heatmapData?.heatmap_overlay_base64 && (
                  <img
                    src={heatmapData.heatmap_overlay_base64}
                    alt="Crowd Heat Overlay"
                    draggable={false}
                    style={{
                      opacity: heatmapOpacity,
                    }}
                    className="absolute inset-0 w-full h-full object-fill pointer-events-none select-none transition-opacity duration-200 z-10"
                  />
                )}

                {/* 4. Verified Map Pins & Camera Hotspots (Accurately Placed on Blueprint: z-20) */}
                {displayedPins.map((pin) => {
                  const isCamera = pin.pin_type === 'camera';
                  const pinColorClass = getPinColor(pin.pin_type, pin.risk);

                  return (
                    <div 
                      key={pin.id}
                      style={{ left: `${pin.x}%`, top: `${pin.y}%` }}
                      onClick={(e) => e.stopPropagation()}
                      className="absolute -translate-x-1/2 -translate-y-1/2 z-20 group/pin"
                    >
                      <div className={`px-2.5 py-1 rounded-full text-[10px] font-bold shadow-xl flex items-center gap-1.5 transition-transform group-hover/pin:scale-125 border ${pinColorClass} cursor-pointer`}>
                        {isCamera ? <Camera className="w-3 h-3 shrink-0" /> : <MapPin className="w-3 h-3 shrink-0" />}
                        <span className="font-mono whitespace-nowrap">{pin.label}</span>
                        {isCamera && pin.count !== undefined && (
                          <span className="bg-black/40 px-1.5 py-0.2 rounded font-black text-[9px]">
                            {pin.count}
                          </span>
                        )}
                      </div>

                      {/* Hover Telemetry Card */}
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/pin:flex flex-col gap-1 p-2.5 rounded-xl bg-slate-950/95 border border-cyan-500/40 text-[10px] font-mono text-white shadow-2xl z-30 min-w-[180px] pointer-events-none">
                        <div className="flex justify-between items-center border-b border-slate-800 pb-1">
                          <span className="font-bold text-cyan-400 truncate">{pin.label}</span>
                          <span className="text-[9px] uppercase text-slate-500">{pin.pin_type}</span>
                        </div>
                        {isCamera ? (
                          <>
                            <div className="flex justify-between text-slate-300">
                              <span>Detected:</span>
                              <span className="font-bold text-white">{pin.count ?? 0} people</span>
                            </div>
                            <div className="flex justify-between text-slate-300">
                              <span>Density:</span>
                              <span className="font-bold text-amber-400">{pin.density ?? 0}%</span>
                            </div>
                            <div className="flex justify-between text-slate-300">
                              <span>Profile / Risk:</span>
                              <span className={`font-bold uppercase ${
                                pin.risk === 'critical' ? 'text-rose-400' :
                                pin.risk === 'high' ? 'text-orange-400' :
                                pin.risk === 'medium' ? 'text-yellow-400' : 'text-cyan-400'
                              }`}>
                                {pin.profile || 'LOW'} ({pin.risk ?? 'low'})
                              </span>
                            </div>
                            {pin.observation_timestamp && (
                              <div className="flex justify-between text-slate-400 text-[9px] pt-0.5 border-t border-slate-800/80">
                                <span>Observed:</span>
                                <span>{new Date(pin.observation_timestamp).toLocaleTimeString()}</span>
                              </div>
                            )}
                          </>
                        ) : (
                          <div className="text-slate-400 text-[9px]">
                            Coordinates: {pin.x.toFixed(1)}%, {pin.y.toFixed(1)}%
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Heat Intensity Legend Overlay (Bottom Right) */}
              <div className="absolute bottom-4 right-4 z-20 p-3 rounded-xl bg-slate-950/90 border border-slate-800 backdrop-blur-md shadow-2xl text-[10px] font-mono select-none">
                <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                  Crowd Density Legend
                </span>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-2.5 rounded bg-blue-500 shadow-sm" />
                    <span className="text-slate-300">Low Density (&lt; 45%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-2.5 rounded bg-yellow-400 shadow-sm" />
                    <span className="text-slate-300">Medium Density (45% – 74%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-2.5 rounded bg-orange-500 shadow-sm" />
                    <span className="text-slate-300">High Density (75% – 89%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-2.5 rounded bg-rose-600 shadow-sm animate-pulse" />
                    <span className="text-slate-300 font-bold text-rose-300">Critical Surge (≥ 90%)</span>
                  </div>
                </div>
              </div>

              {/* Status indicator on top left of map */}
              <div className="absolute top-4 left-4 z-20 flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 backdrop-blur-md text-[10px] font-mono">
                <span className={`w-2 h-2 rounded-full ${heatmapData?.status === 'live' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
                <span className="text-slate-300">
                  {heatmapData?.status === 'live' ? 'Dynamic Heatmap Active' : 'Cameras Standby'}
                </span>
              </div>
            </div>
          </div>
        )}
      </GlassCard>

      {/* Monitored Zones & Camera Sensor Breakdown Tabs */}
      <GlassCard className="p-6 space-y-4 font-mono">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveTab('zones')}
              className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer
                ${activeTab === 'zones' 
                  ? 'bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 shadow-sm' 
                  : 'text-slate-400 hover:text-white'}`}
            >
              Operational Zones ({heatmapData?.zones?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('cameras')}
              className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer
                ${activeTab === 'cameras' 
                  ? 'bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 shadow-sm' 
                  : 'text-slate-400 hover:text-white'}`}
            >
              Camera Feeds ({heatmapData?.cameras?.length || 0})
            </button>
          </div>

          <span className="text-[10px] text-slate-500 hidden sm:inline">
            Aggregated by Event Architecture
          </span>
        </div>

        {activeTab === 'zones' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
            {(heatmapData?.zones || []).length === 0 ? (
              <p className="col-span-4 text-center py-6 text-slate-500 text-xs italic">
                No operational zones registered for this event.
              </p>
            ) : (
              (heatmapData?.zones || []).map((z) => {
                const zRiskColor = 
                  z.risk_level === 'critical' ? 'text-rose-400 bg-rose-950/60 border-rose-500/40' :
                  z.risk_level === 'high' ? 'text-orange-400 bg-orange-950/60 border-orange-500/40' :
                  z.risk_level === 'medium' ? 'text-amber-400 bg-amber-950/60 border-amber-500/40' :
                  'text-emerald-400 bg-emerald-950/60 border-emerald-500/40';

                return (
                  <div key={z.id} className="p-4 rounded-xl bg-slate-950/60 border border-slate-900 space-y-2.5">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="text-xs font-bold text-white tracking-wide">{z.name}</h4>
                        <span className="text-[9px] text-slate-500 font-mono">{z.code} · {z.zone_type}</span>
                      </div>
                      <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border ${zRiskColor}`}>
                        {z.risk_level}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px] text-slate-400">
                        <span>Occupancy:</span>
                        <span className="font-bold text-white">{z.current_count} / {z.capacity}</span>
                      </div>
                      {/* Density Progress Bar */}
                      <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div 
                          style={{ width: `${Math.min(100, z.density)}%` }}
                          className={`h-full transition-all duration-300 ${
                            z.density >= 90 ? 'bg-rose-500' :
                            z.density >= 75 ? 'bg-orange-500' :
                            z.density >= 45 ? 'bg-yellow-400' :
                            'bg-emerald-400'
                          }`}
                        />
                      </div>
                      <div className="flex justify-between text-[9px] text-slate-500">
                        <span>Density: {z.density}%</span>
                        <span>{z.assigned_cameras_count} camera(s)</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-900">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase text-[9px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Camera Name & ID</th>
                  <th className="py-2.5 px-3">Blueprint Pin Status</th>
                  <th className="py-2.5 px-3">Location</th>
                  <th className="py-2.5 px-3">Stream Status</th>
                  <th className="py-2.5 px-3">Live People Detected</th>
                  <th className="py-2.5 px-3">Local Density</th>
                  <th className="py-2.5 px-3">Risk Tier</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 bg-slate-950/40">
                {(heatmapData?.cameras || []).length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-slate-500 italic">
                      No cameras configured for this event.
                    </td>
                  </tr>
                ) : (
                  (heatmapData?.cameras || []).map((c) => (
                    <tr key={c.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-2 px-3 font-semibold text-white">
                        <div className="flex flex-col">
                          <span>{c.name}</span>
                          <span className="text-[9px] text-slate-500 font-mono">{c.id}</span>
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        {c.pin_mapped ? (
                          <span className="text-[9px] text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
                            Mapped ({c.pin_x?.toFixed(0)}%, {c.pin_y?.toFixed(0)}%)
                          </span>
                        ) : (
                          <span className="text-[9px] text-slate-500 bg-slate-900 px-2 py-0.5 rounded">
                            Unmapped
                          </span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-slate-300">{c.location}</td>
                      <td className="py-2 px-3">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase
                          ${c.is_active ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}`}
                        >
                          {c.playback_status || c.status}
                        </span>
                      </td>
                      <td className="py-2 px-3 font-bold text-cyan-400">{c.count}</td>
                      <td className="py-2 px-3 font-bold text-amber-400">{c.density}%</td>
                      <td className="py-2 px-3">
                        <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border
                          ${c.risk === 'critical' ? 'text-rose-400 bg-rose-950/60 border-rose-500/40' :
                            c.risk === 'high' ? 'text-orange-400 bg-orange-950/60 border-orange-500/40' :
                            c.risk === 'medium' ? 'text-amber-400 bg-amber-950/60 border-amber-500/40' :
                            'text-emerald-400 bg-emerald-950/60 border-emerald-500/40'}`}
                        >
                          {c.risk}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
};

export default HeatmapPage;
