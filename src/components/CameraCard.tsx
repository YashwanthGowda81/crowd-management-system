import React from 'react';
import type { Camera } from '../context/CrowdSystemContext';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { VideoOff, Eye } from 'lucide-react';
import { NavLink } from 'react-router-dom';

interface CameraCardProps {
  camera: Camera;
  onInspect?: () => void;
}

export const CameraCard: React.FC<CameraCardProps> = ({ camera, onInspect }) => {
  const { toggleCameraStatus, removeCamera } = useCrowdSystem();
  const [streamError, setStreamError] = React.useState(false);

  const isOnline = camera.status === 'online';
  const isAnalyzing = (camera.playbackStatus === 'analyzing' || camera.playbackStatus === 'playing') && isOnline;
  const isTelemetryStale = isAnalyzing && camera.isTelemetryValid === false;

  React.useEffect(() => {
    setStreamError(false);
  }, [camera.id, camera.playbackStatus]);

  const riskColors = {
    low: 'text-green-400 border-green-500/20 bg-green-950/20',
    medium: 'text-amber-400 border-amber-500/20 bg-amber-950/20',
    high: 'text-orange-400 border-orange-500/20 bg-orange-950/20',
    critical: 'text-red-400 border-red-500/20 bg-red-950/20 animate-pulse',
  };

  return (
    <div className={`cyber-glass rounded-xl overflow-hidden border transition-all duration-300 group
      ${isOnline 
        ? 'border-blue-500/10 hover:border-cyan-500/30' 
        : 'border-slate-800 bg-slate-950/30 opacity-70 hover:opacity-100'}`}
    >
      {/* CCTV Feed Viewport */}
      <div className="relative aspect-video bg-slate-950 overflow-hidden select-none border-b border-slate-900/60 flex items-center justify-center">
        {isAnalyzing && !streamError ? (
          <>
            <img 
              src={`http://localhost:8000/api/cameras/${camera.id}/stream`} 
              alt={camera.name} 
              className="w-full h-full object-contain bg-black"
              onError={() => {
                setStreamError(true);
              }}
            />

            {/* Live / Stale Indicator */}
            <div className={`absolute top-2 right-2 flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[9px] font-bold z-20 ${
              isTelemetryStale
                ? 'bg-amber-950/90 border-amber-500/40 text-amber-300'
                : 'bg-slate-950/80 border-green-500/20 text-green-400'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                isTelemetryStale ? 'bg-amber-400' : 'bg-green-400 animate-pulse'
              }`} />
              <span>{isTelemetryStale ? 'STALE TELEMETRY' : 'LIVE'}</span>
            </div>
          </>
        ) : streamError ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 gap-1.5 p-4 text-center bg-slate-950/90">
            <VideoOff className="w-7 h-7 text-amber-500" />
            <span className="text-[11px] uppercase tracking-wider font-bold text-amber-400 font-mono">
              Stream Unavailable (503 / Offline)
            </span>
            <span className="text-[9px] text-slate-500 font-mono max-w-[220px]">
              Preview served by ingestion owner process.
            </span>
          </div>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 gap-2 p-4 text-center">
            <VideoOff className="w-8 h-8 text-slate-600" />
            <span className="text-xs uppercase tracking-wider font-bold text-slate-400 font-mono">
              No active video source
            </span>
            <span className="text-[10px] text-slate-600 font-mono">
              0 detections
            </span>
          </div>
        )}
        
        {/* Location Tag */}
        <div className="absolute top-2 left-2 bg-slate-950/80 px-2 py-0.5 rounded text-[9px] font-bold border border-slate-800 text-slate-300 uppercase tracking-wider font-mono z-20">
          {camera.location}
        </div>
      </div>

      {/* Camera Info */}
      <div className="p-4 space-y-3">
        <div>
          <h4 className="text-sm font-semibold truncate text-white">{camera.name}</h4>
        </div>

        {isAnalyzing ? (
          <div className="grid grid-cols-2 gap-3 text-xs border-t border-slate-900 pt-3">
            <div>
              <span className="text-slate-500 text-[10px] block">CROWD COUNT</span>
              <span className="font-bold text-base font-mono">{camera.count > 0 ? camera.count : '0 detections'}</span>
              <span className="text-[9px] text-slate-400"> / {camera.capacity} max</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">DENSITY</span>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-base font-mono">{camera.density}%</span>
                <span className={`text-[8px] font-bold px-1 py-0.2 rounded border uppercase ${riskColors[camera.risk]}`}>
                  {camera.risk}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-3 text-center text-xs text-slate-500 border-t border-slate-900 space-y-0.5 font-mono">
            <div className="text-slate-400 font-semibold">0 detections</div>
            <div className="text-[10px] text-slate-600">No active video source</div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2 border-t border-slate-900/60">
          <button
            onClick={() => toggleCameraStatus(camera.id)}
            className={`flex-1 text-center py-1.5 rounded-lg text-xs font-semibold border transition-all
              ${isOnline 
                ? 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-white' 
                : 'bg-blue-950/20 border-blue-500/20 text-cyan-400 hover:bg-blue-950/40 hover:border-cyan-500/40'}`}
          >
            {isOnline ? 'Disconnect' : 'Connect RTSP'}
          </button>
          
          {onInspect ? (
            <button
              onClick={onInspect}
              className="px-3 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-400 hover:text-cyan-300 text-xs font-bold transition-all flex items-center gap-1"
              title="Inspect Selected Camera"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Inspect</span>
            </button>
          ) : (
            <NavLink
              to="/live"
              className="px-3 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-400 hover:text-cyan-300 text-xs font-bold transition-all flex items-center gap-1"
              title="Inspect Stream"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Inspect</span>
            </NavLink>
          )}

          <button
            onClick={() => removeCamera(camera.id)}
            className="p-1.5 rounded-lg bg-red-950/20 hover:bg-red-950/40 border border-red-950 text-red-400 hover:text-red-300 transition-colors"
            title="Delete Camera"
          >
            🗑️
          </button>
        </div>
      </div>
    </div>
  );
};
