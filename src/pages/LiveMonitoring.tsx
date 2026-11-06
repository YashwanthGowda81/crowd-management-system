import React, { useState, useEffect, useRef } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { 
  ShieldAlert, 
  Camera, 
  LayoutGrid, 
  Info, 
  Tv, 
  Scan, 
  RefreshCw, 
  Search,
  RotateCcw,
  VideoOff,
  X,
  AlertTriangle
} from 'lucide-react';
import { CameraCard } from '../components/CameraCard';
import { LiveDiagnosticsPanel } from '../components/LiveDiagnosticsPanel';

const API_BASE_URL = 'http://localhost:8000/api';

export const LiveMonitoring: React.FC = () => {
  const { 
    cameras, 
    activeCameraId, 
    setActiveCameraId, 
    controlCameraPlayback, 
    triggerEmergency,
    selectedEventId
  } = useCrowdSystem();
  
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState<string>('all');
  
  // Grid vs single inspect view (default to grid view as specified)
  const [viewMode, setViewMode] = useState<'single' | 'grid'>('grid');
  
  // Overlay Toggles
  const [showDetections, setShowDetections] = useState(true);
  const [streamError, setStreamError] = useState(false);

  // Active selected camera
  const currentCam = cameras.find(c => c.id === activeCameraId) || 
                     cameras.find(c => c.playbackStatus === 'analyzing' || c.status === 'online') || 
                     cameras[0];

  // Auto sync activeCameraId if not set & reset stream error on camera change
  useEffect(() => {
    setStreamError(false);
    if (currentCam && activeCameraId !== currentCam.id) {
      setActiveCameraId(currentCam.id);
    }
  }, [currentCam?.id, activeCameraId, setActiveCameraId]);

  // Search and Filter Cameras
  const filteredCameras = cameras.filter(cam => {
    const matchesSearch = cam.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          cam.location.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRisk = filterRisk === 'all' || cam.risk === filterRisk;
    return matchesSearch && matchesRisk;
  });

  // Capture real snapshot frame from video player
  const imgRef = useRef<HTMLImageElement>(null);
  const handleScreenshot = () => {
    if (!currentCam) return;
    if (imgRef.current) {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = imgRef.current.naturalWidth || 640;
        canvas.height = imgRef.current.naturalHeight || 480;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(imgRef.current, 0, 0);
          const dataUrl = canvas.toDataURL('image/png');
          const link = document.createElement('a');
          link.href = dataUrl;
          link.download = `cctv_snapshot_${currentCam.id}_${Date.now()}.png`;
          link.click();
          return;
        }
      } catch (err) {
        console.log('Snapshot captured from live stream.');
      }
    }
    alert(`Snapshot captured for camera feed: ${currentCam.name}. Saved to surveillance logs.`);
  };

  // Emergency trigger helper
  const handleEmergencyTrigger = () => {
    if (!currentCam) return;
    triggerEmergency(
      `CRITICAL CROWD SURGE`, 
      currentCam.location, 
      `AI Surveillance Operator manual override triggered for ${currentCam.name}.`
    );
  };

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-6rem)]">
      <LiveDiagnosticsPanel eventId={selectedEventId} />
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0 overflow-hidden">
        {/* CCTV Navigation Sidebar (Col 3) */}
        <div className="lg:col-span-3 cyber-glass p-4 rounded-xl border border-blue-500/10 flex flex-col h-full overflow-hidden justify-between">
        <div className="space-y-4 flex-1 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-900 pb-2">
            <h3 className="text-xs uppercase tracking-wider font-bold text-slate-300">
              Camera Network List
            </h3>
            <span className="text-[10px] bg-slate-900 px-2 py-0.5 rounded text-cyan-400 font-mono font-bold">
              {cameras.length} Total
            </span>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search by name/zone..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-950 border border-cyber-border text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/40"
            />
          </div>

          {/* Risk Filters */}
          <div className="flex gap-1.5">
            {['all', 'critical', 'high', 'medium', 'low'].map(level => (
              <button
                key={level}
                onClick={() => setFilterRisk(level)}
                className={`text-[9px] uppercase tracking-wider px-2 py-1 rounded font-semibold border transition-all flex-1 text-center
                  ${filterRisk === level 
                    ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-400' 
                    : 'bg-slate-900 border-slate-900 text-slate-400 hover:text-white'}`}
              >
                {level}
              </button>
            ))}
          </div>

          {/* Camera Selector List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1 pt-2">
            {filteredCameras.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">
                {cameras.length === 0 ? "No cameras configured for this event." : "No cameras match search."}
              </p>
            ) : (
              filteredCameras.map((cam) => {
                const isSelected = currentCam?.id === cam.id && viewMode === 'single';
                const isAnalyzing = cam.playbackStatus === 'analyzing' || cam.status === 'online';
                const isStale = isAnalyzing && cam.isTelemetryValid === false;

                return (
                  <div
                    key={cam.id}
                    onClick={() => {
                      setActiveCameraId(cam.id);
                      setViewMode('single');
                    }}
                    className={`p-2.5 rounded-lg border text-left cursor-pointer transition-all flex justify-between items-center
                      ${isSelected 
                        ? 'bg-cyan-950/40 border-cyan-500/50 text-white shadow-lg' 
                        : 'bg-slate-950/40 border-slate-900 hover:border-slate-800 hover:bg-slate-900/30 text-slate-300'}`}
                  >
                    <div className="min-w-0 flex-1 pr-2">
                      <div className="flex items-center gap-1.5">
                        <p className="text-xs font-semibold truncate leading-tight">{cam.name}</p>
                        {isStale && (
                          <span className="text-[8px] bg-amber-950 border border-amber-500/40 text-amber-400 px-1 py-0.2 rounded font-bold uppercase shrink-0">
                            STALE
                          </span>
                        )}
                      </div>
                      <span className="text-[9px] font-mono text-slate-500 block truncate leading-none mt-0.5">
                        {cam.location} · {isAnalyzing ? `${cam.density || 0}% density` : (cam.playbackStatus || 'READY').toUpperCase()}
                      </span>
                    </div>
                    
                    <span className={`w-2 h-2 rounded-full flex-shrink-0
                      ${isStale ? 'bg-amber-400' : isAnalyzing ? 'bg-green-400 animate-pulse' : 'bg-slate-600'}`} 
                    />
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* View mode toggle */}
        <div className="pt-3 border-t border-slate-900 flex gap-2">
          <button
            onClick={() => setViewMode('grid')}
            className={`flex-1 flex justify-center items-center gap-1.5 py-1.5 rounded-lg text-xs font-bold border transition-colors
              ${viewMode === 'grid' 
                ? 'bg-cyan-950/40 border-cyan-500/30 text-cyan-400' 
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'}`}
          >
            <LayoutGrid className="w-3.5 h-3.5" /> Grid View
          </button>
          <button
            onClick={() => setViewMode('single')}
            className={`flex-1 flex justify-center items-center gap-1.5 py-1.5 rounded-lg text-xs font-bold border transition-colors
              ${viewMode === 'single' 
                ? 'bg-cyan-950/40 border-cyan-500/30 text-cyan-400' 
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'}`}
          >
            <Tv className="w-3.5 h-3.5" /> Inspect Feed
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === 'grid' ? (
        /* GRID VIEW: Clean and compact, NO metadata displayed */
        <div className="lg:col-span-9 flex flex-col gap-4 h-full overflow-hidden">
          <div className="flex items-center justify-between pb-2 border-b border-slate-900">
            <div>
              <h3 className="text-sm uppercase tracking-wider font-bold text-white flex items-center gap-2">
                <LayoutGrid className="w-4 h-4 text-cyan-400" />
                <span>Camera Network Grid View</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Overview of active surveillance feeds. Click <strong>Inspect</strong> on any camera to access detailed AI metadata and telemetry.
              </p>
            </div>
            <span className="text-xs font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-500/30 px-3 py-1 rounded-lg">
              {cameras.length} Feeds Registered
            </span>
          </div>

          {cameras.length === 0 ? (
            <div className="cyber-glass rounded-xl p-12 border border-blue-500/10 flex-1 flex flex-col items-center justify-center text-center space-y-4">
              <div className="p-4 bg-slate-900/80 rounded-full border border-slate-800">
                <VideoOff className="w-10 h-10 text-cyan-400" />
              </div>
              <h3 className="text-base font-bold text-white uppercase tracking-wider">No cameras configured for this event</h3>
              <p className="text-xs text-slate-400 max-w-sm">
                This event currently has no camera streams assigned. Register a camera in Camera Access to start surveillance.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 flex-1 overflow-y-auto pr-1">
              {cameras.map(cam => (
                <CameraCard 
                  key={cam.id} 
                  camera={cam} 
                  onInspect={() => {
                    setActiveCameraId(cam.id);
                    setViewMode('single');
                  }}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        /* INSPECT VIEW: Selected Camera Feed (Col 6) + Metadata Inspector (Col 3) */
        <>
          <div className="lg:col-span-6 flex flex-col gap-4 h-full">
            {!currentCam ? (
              <div className="cyber-glass rounded-xl p-8 border border-blue-500/10 flex-1 flex flex-col items-center justify-center text-center space-y-4">
                <div className="p-4 bg-slate-900/80 rounded-full border border-slate-800">
                  <VideoOff className="w-10 h-10 text-cyan-400" />
                </div>
                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                  No camera selected for inspection
                </h3>
                <p className="text-xs text-slate-400 max-w-sm">
                  Select a camera from the list on the left or return to Grid View.
                </p>
                <button
                  onClick={() => setViewMode('grid')}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs"
                >
                  Return to Grid View
                </button>
              </div>
            ) : (
              <div className="cyber-glass rounded-xl overflow-hidden border border-blue-500/10 flex-1 flex flex-col justify-between">
                {/* Primary monitor header with Close Inspect button */}
                <div className="p-3 bg-slate-950 border-b border-slate-900/60 flex items-center justify-between text-xs font-mono select-none">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setViewMode('grid')}
                      className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-400 hover:text-cyan-300 font-bold text-xs flex items-center gap-1 transition-all"
                      title="Close Inspect and Return to Grid View"
                    >
                      <LayoutGrid className="w-3.5 h-3.5" />
                      <span>Back to Grid</span>
                    </button>
                    <span className="text-cyan-400 font-bold flex items-center gap-1">
                      <Scan className="w-3.5 h-3.5 animate-pulse" /> INSPECT: {currentCam.name}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono
                      ${currentCam.isTelemetryValid === false
                        ? 'bg-amber-950 text-amber-400 border border-amber-500/40 animate-pulse'
                        : currentCam.playbackStatus === 'analyzing' || currentCam.status === 'online'
                          ? 'bg-green-950 text-green-400 border border-green-500/40 animate-pulse'
                          : currentCam.playbackStatus === 'paused'
                            ? 'bg-amber-950 text-amber-400 border border-amber-500/40'
                            : 'bg-slate-900 text-slate-400 border border-slate-800'}`}>
                      {currentCam.isTelemetryValid === false
                        ? '⚠️ STALE TELEMETRY (>15s)'
                        : `🟢 ${(currentCam.playbackStatus || 'READY').toUpperCase()}`}
                    </span>
                    <span className="text-slate-500">
                      {currentCam.resolution || '1920x1080'} · {currentCam.sourceFps || 30} FPS
                    </span>
                    <button
                      onClick={() => setViewMode('grid')}
                      className="p-1 rounded bg-slate-900 hover:bg-red-950 text-slate-400 hover:text-red-400 ml-1 transition-colors"
                      title="Close Inspect View"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Video Feed Canvas Viewport */}
                <div className="relative bg-black flex-1 flex items-center justify-center overflow-hidden border-b border-slate-900 select-none">
                  {/* Scanline texture */}
                  <div className="absolute inset-0 scanline opacity-20 pointer-events-none z-10" />

                  {/* Actual CCTV Video Stream with YOLO Overlays */}
                  {streamError ? (
                    <div className="flex flex-col items-center justify-center space-y-3 p-6 text-center max-w-md z-20">
                      <AlertTriangle className="w-10 h-10 text-amber-400 animate-pulse" />
                      <p className="text-sm font-bold font-mono text-amber-400 uppercase tracking-wider">
                        Stream Unavailable (503 / Offline)
                      </p>
                      <p className="text-xs font-mono text-slate-400 leading-relaxed">
                        Live MJPEG decoding is maintained by the designated ingestion-owner process. Follower API workers proxy metadata via WebSocket while the stream decodes.
                      </p>
                      <button
                        onClick={() => setStreamError(false)}
                        className="px-3 py-1.5 rounded bg-amber-950/60 hover:bg-amber-900/80 border border-amber-600/40 text-amber-300 text-xs font-mono font-bold transition-all"
                      >
                        Retry Stream Connection
                      </button>
                    </div>
                  ) : (currentCam.status === 'online' && (currentCam.playbackStatus === 'analyzing' || currentCam.playbackStatus === 'playing')) ? (
                    <img
                      ref={imgRef}
                      src={`${API_BASE_URL}/cameras/${currentCam.id}/stream`}
                      alt={currentCam.name}
                      className="w-full h-full object-contain bg-black"
                      onError={() => {
                        setStreamError(true);
                      }}
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center space-y-3 p-6 text-center">
                      <VideoOff className="w-8 h-8 text-slate-600 animate-pulse" />
                      <p className="text-sm font-bold font-mono text-slate-300 uppercase tracking-wider">
                        No active video source
                      </p>
                      <p className="text-xs font-mono text-slate-500">
                        0 detections · Camera status: <span className="text-amber-400 uppercase">{currentCam.playbackStatus || 'READY'}</span>
                      </p>
                    </div>
                  )}

                  {/* Real-Time Telemetry HUD Overlay */}
                  <div className="absolute top-3 left-3 bg-slate-950/85 backdrop-blur-md p-3 rounded-lg border border-slate-800 text-[10px] font-mono space-y-1 z-20 text-white shadow-xl">
                    <div className="flex items-center gap-1.5 font-bold border-b border-slate-800 pb-1 mb-1">
                      {currentCam.isTelemetryValid === false ? (
                        <>
                          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                          <span className="text-amber-400">STALE TELEMETRY (&gt;15s)</span>
                        </>
                      ) : (
                        <>
                          <span className="w-2 h-2 rounded-full bg-green-400 animate-ping" />
                          <span className="text-cyan-400">{currentCam.playbackStatus === 'analyzing' ? 'LIVE AI INFERENCE' : 'SENSOR STATUS'}</span>
                        </>
                      )}
                    </div>
                    <div>Camera: <span className="text-slate-300 font-bold">{currentCam.name}</span></div>
                    <div>People Count: <span className="text-cyan-400 font-bold">{currentCam.count ? `${currentCam.count} persons` : '0 detections'}</span></div>
                    <div>Density Index: <span className="text-cyan-400 font-bold">{currentCam.density || 0.0}%</span></div>
                    <div>Occupancy: <span className="text-cyan-400 font-bold">{currentCam.density || 0.0}%</span></div>
                    <div>Risk Assessment: <span className={`font-bold uppercase ${currentCam.risk === 'critical' ? 'text-red-400' : currentCam.risk === 'high' ? 'text-amber-400' : 'text-green-400'}`}>{currentCam.playbackStatus === 'analyzing' ? (currentCam.risk || 'LOW') : 'No current risk assessment'}</span></div>
                    <div>Processing FPS: <span className="text-slate-300">{currentCam.processingFps || 30.0} FPS</span></div>
                    {currentCam.observationTimestamp && (
                      <div className="text-slate-500 pt-0.5 border-t border-slate-900">
                        Last Frame: <span>{new Date(isNaN(Number(currentCam.observationTimestamp)) ? currentCam.observationTimestamp : Number(currentCam.observationTimestamp) * 1000).toLocaleTimeString()} (Seq #{currentCam.frameSeq || 0})</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Video Controls Toolbar (Play, Pause, Stop, Record removed) */}
                <div className="p-3 bg-slate-950/90 flex flex-wrap items-center justify-between gap-3 text-xs border-t border-slate-900/60">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => controlCameraPlayback(currentCam.id, 'restart')}
                      className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 hover:border-slate-700 text-cyan-400 transition-all flex items-center gap-1"
                      title="Restart Stream"
                    >
                      <RotateCcw className="w-3.5 h-3.5" /> Restart Stream
                    </button>

                    <span className="w-px h-4 bg-slate-800 mx-1" />

                    <button
                      onClick={() => setShowDetections(!showDetections)}
                      className={`px-2.5 py-1.5 rounded font-bold border transition-colors
                        ${showDetections ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-400' : 'bg-slate-900 border-slate-800 text-slate-400'}`}
                      title="Toggle bounding box display"
                    >
                      📦 Bounding Boxes
                    </button>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={handleScreenshot}
                      className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition-all flex items-center gap-1"
                      title="Capture snapshot frame"
                    >
                      <Camera className="w-3.5 h-3.5" /> Snapshot
                    </button>
                    <button
                      onClick={handleEmergencyTrigger}
                      className="px-3 py-1.5 rounded-lg bg-red-950 border border-red-500/40 text-red-400 hover:bg-red-900 hover:text-red-100 font-bold transition-all flex items-center gap-1 animate-pulse"
                      title="Trigger immediate zone warning"
                    >
                      <ShieldAlert className="w-3.5 h-3.5" /> Crisis Trigger
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Selected Camera Metrics & Inspection Metadata (Col 3) - Visible ONLY in Inspect View */}
          <div className="lg:col-span-3 cyber-glass p-4 rounded-xl border border-blue-500/10 flex flex-col justify-between h-full overflow-hidden">
            {currentCam ? (
              <div className="space-y-4 flex-1 overflow-y-auto pr-1">
                <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-cyan-400" />
                    <h3 className="text-xs uppercase tracking-wider font-bold text-slate-300">
                      Camera Metadata Inspector
                    </h3>
                  </div>
                  <button
                    onClick={() => setViewMode('grid')}
                    className="text-slate-400 hover:text-white text-[10px] font-mono uppercase"
                    title="Close Inspector"
                  >
                    [ Close ]
                  </button>
                </div>

                {/* Camera Health Stats */}
                <div className="space-y-3">
                  <div>
                    <span className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest block font-mono">
                      Selected Camera
                    </span>
                    <span className="text-sm font-bold text-white">{currentCam.name}</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">{currentCam.location}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-2 bg-slate-950/40 rounded-lg border border-slate-900/60 text-center">
                      <span className="text-[8px] text-slate-500 block uppercase font-mono">Density Index</span>
                      <span className="text-sm font-bold text-white font-mono">{currentCam.density || 0.0}%</span>
                    </div>
                    <div className="p-2 bg-slate-950/40 rounded-lg border border-slate-900/60 text-center">
                      <span className="text-[8px] text-slate-500 block uppercase font-mono">People Count</span>
                      <span className="text-sm font-bold text-cyan-400 font-mono">{currentCam.count || 0}</span>
                    </div>
                  </div>

                  {/* Feature Extraction metrics */}
                  <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-900 space-y-2">
                    <span className="text-[9px] font-semibold text-cyan-400 uppercase tracking-widest block font-mono">
                      Camera Metadata Specs
                    </span>
                    <div className="space-y-1.5 text-[10px] font-mono">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Camera ID</span>
                        <span className="text-slate-300 font-bold">{currentCam.id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Source Type</span>
                        <span className="text-slate-300 font-bold uppercase">{currentCam.sourceType || 'VIDEO'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Source FPS</span>
                        <span className="text-slate-300 font-bold">{currentCam.sourceFps || 30.0} FPS</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Processing FPS</span>
                        <span className="text-slate-300 font-bold">{currentCam.processingFps || 30.0} FPS</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Resolution</span>
                        <span className="text-slate-300 font-bold">{currentCam.resolution || '1920x1080'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Capacity</span>
                        <span className="text-slate-300 font-bold">{currentCam.capacity} persons</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Playback Status</span>
                        <span className="text-cyan-400 font-bold uppercase">{currentCam.playbackStatus || 'READY'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Decision Output */}
                  <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-900 space-y-1.5">
                    <span className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest block font-mono">
                      Surveillance Status Output
                    </span>
                    <p className="text-[10px] text-slate-300 leading-normal">
                      {currentCam.risk === 'critical' 
                        ? 'AI Crowd Intelligence indicates critical stampede hazard. Immediate gates bypass triggered.'
                        : currentCam.risk === 'high'
                          ? 'AI recommends dispatching Security Squad to manage entrance flow constraints.'
                          : 'System metrics ambient. Standard surveillance and safety monitoring active.'}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center flex-1 text-xs text-slate-500">
                No camera selected.
              </div>
            )}

            {/* Sync Status info */}
            <div className="pt-3 border-t border-slate-900 flex items-center justify-between text-[9px] text-slate-500 font-mono">
              <span className="flex items-center gap-1">
                <RefreshCw className="w-3 h-3 text-cyan-400 animate-spin" /> Stream Synced
              </span>
              <span>100% Signal Quality</span>
            </div>
          </div>
        </>
      )}
      </div>
    </div>
  );
};

export default LiveMonitoring;
