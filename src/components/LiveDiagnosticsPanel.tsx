import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  ChevronDown, 
  ChevronUp, 
  Terminal, 
  CheckCircle2, 
  Layers, 
  Cpu, 
  RefreshCw, 
  AlertCircle,
  Copy,
  Check
} from 'lucide-react';
import { apiService } from '../services/api';
import { 
  isDiagnosticsEnabled, 
  setDiagnosticsEnabled, 
  processDiagnosticEvents, 
  initDiagnosticsConsole 
} from '../services/diagnosticsLogger';

interface DiagnosticSource {
  source_id: string;
  name: string;
  location: string;
  event_id?: string;
  status: string;
  is_active: boolean;
  captured_frames: number;
  submitted_frames: number;
  superseded_frames: number;
  completed_inferences: number;
  current_queue_depth: number;
  capture_fps: number;
  processing_fps: number;
  last_capture_timestamp?: string;
  last_inference_timestamp?: string;
  error?: string | null;
}

interface SchedulerSnapshot {
  state: string;
  batching_enabled: boolean;
  max_batch_size: number;
  active_sources_count: number;
  total_batches: number;
  total_inferences: number;
  current_batch_size: number;
  recent_batch_sizes: number[];
  last_batch_id?: number | null;
  last_batch_sources?: string[];
  last_batch_duration_ms?: number | null;
  avg_batch_duration_ms?: number | null;
  effective_aggregate_fps: number;
  last_inference_timestamp?: string | null;
  error?: string | null;
}

interface DiagnosticsData {
  timestamp: string;
  event_id?: string;
  scheduler: SchedulerSnapshot;
  sources: DiagnosticSource[];
  events: Array<{ id: number; formatted: string; type: string }>;
  concurrency_proof: {
    parallel_capture: string;
    batched_inference: string;
    concurrent_processing: string;
  };
}

interface LiveDiagnosticsPanelProps {
  eventId?: string;
}

export const LiveDiagnosticsPanel: React.FC<LiveDiagnosticsPanelProps> = ({ eventId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState<DiagnosticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [consoleLoggingActive, setConsoleLoggingActive] = useState<boolean>(isDiagnosticsEnabled());
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const sinceIdRef = useRef<number>(0);

  // Initialize console logger listeners
  useEffect(() => {
    initDiagnosticsConsole();
  }, []);

  // Periodic polling for live diagnostics snapshot (1.2s interval)
  useEffect(() => {
    let isMounted = true;
    const fetchDiagnostics = async () => {
      try {
        const res = await apiService.getPipelineDiagnostics(eventId, sinceIdRef.current);
        if (!isMounted) return;
        setData(res);
        setLoading(false);
        setFetchError(null);

        // Feed new events to namespaced console logger if opt-in is enabled
        if (res.events && res.events.length > 0) {
          processDiagnosticEvents(res.events);
          const maxId = Math.max(...res.events.map((e: any) => e.id));
          if (maxId > sinceIdRef.current) {
            sinceIdRef.current = maxId;
          }
        }
      } catch (err: any) {
        if (!isMounted) return;
        setFetchError(err.message || 'Diagnostics connection unavailable');
        setLoading(false);
      }
    };

    fetchDiagnostics();
    const interval = setInterval(fetchDiagnostics, 1200);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [eventId]);

  const handleToggleConsoleLogging = () => {
    const newState = !consoleLoggingActive;
    setDiagnosticsEnabled(newState);
    setConsoleLoggingActive(newState);
  };

  const handleCopySnippet = () => {
    navigator.clipboard.writeText('localStorage.setItem("crowdAiDiagnostics", "true")');
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const scheduler = data?.scheduler;
  const sources = data?.sources || [];
  const activeSourcesCount = scheduler?.active_sources_count ?? 0;
  const isIdle = activeSourcesCount === 0;

  return (
    <div className="w-full bg-slate-900/90 border border-cyan-500/30 rounded-xl overflow-hidden backdrop-blur-md shadow-2xl transition-all duration-200">
      {/* Collapsed / Header Summary Bar */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2.5 flex items-center justify-between cursor-pointer hover:bg-slate-800/60 transition-colors select-none"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
            <Activity className={`w-4 h-4 ${!isIdle ? 'animate-pulse text-cyan-300' : 'text-slate-400'}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-white">
                Live Processing Diagnostics
              </span>
              <span className={`px-2 py-0.2 rounded-full text-[9px] font-mono font-bold uppercase border
                ${fetchError 
                  ? 'bg-rose-950/60 border-rose-500/40 text-rose-300' 
                  : isIdle 
                    ? 'bg-slate-800 border-slate-700 text-slate-400' 
                    : 'bg-emerald-950/70 border-emerald-500/40 text-emerald-300'}`}
              >
                {fetchError ? 'OFFLINE' : isIdle ? 'IDLE' : 'LIVE CONCURRENT'}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono">
              Verifiable proof of parallel video capture & batched YOLOv8n CPU inference
            </p>
          </div>
        </div>

        {/* Quick metrics in header */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-[10px] font-mono text-slate-300 bg-slate-950/60 px-3 py-1 rounded-lg border border-slate-800">
            <span className="text-slate-500">Active Feeds:</span>
            <span className="font-bold text-cyan-400">{activeSourcesCount}</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-500">YOLO Batch:</span>
            <span className="font-bold text-amber-400">
              {scheduler?.current_batch_size ? `${scheduler.current_batch_size}` : isIdle ? '0 (Idle)' : '1'}
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-500">Aggregate FPS:</span>
            <span className="font-bold text-emerald-400">
              {scheduler?.effective_aggregate_fps ? `${scheduler.effective_aggregate_fps} FPS` : 'Not available'}
            </span>
          </div>

          <button 
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleToggleConsoleLogging();
            }}
            className={`px-2 py-1 rounded text-[10px] font-mono font-bold border transition-all flex items-center gap-1.5
              ${consoleLoggingActive 
                ? 'bg-cyan-950 border-cyan-400 text-cyan-300 shadow-sm shadow-cyan-500/20' 
                : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-white'}`}
            title="Toggle namespaced DevTools browser console logging"
          >
            <Terminal className="w-3 h-3" />
            <span className="hidden md:inline">DevTools Diag:</span>
            <span>{consoleLoggingActive ? 'ON' : 'OFF'}</span>
          </button>

          <button 
            type="button"
            className="text-slate-400 hover:text-white transition-colors p-1"
          >
            {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Detailed Diagnostics Drawer */}
      {isOpen && (
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 space-y-4 text-xs font-mono">
          {fetchError ? (
            <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>Failed to load diagnostics from backend: {fetchError}</span>
            </div>
          ) : loading && !data ? (
            <div className="p-6 flex items-center justify-center gap-2 text-slate-400">
              <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
              <span>Acquiring live pipeline telemetry...</span>
            </div>
          ) : (
            <>
              {/* Top Aggregate Metric Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
                <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[10px] text-slate-400 uppercase">Active Video Feeds</span>
                  <div className="text-base font-bold text-cyan-400 mt-1">
                    {scheduler?.active_sources_count ?? 'Not available'}
                  </div>
                  <span className="text-[9px] text-slate-500 mt-0.5">Separate capture threads</span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[10px] text-slate-400 uppercase">YOLO Batch Size</span>
                  <div className="text-base font-bold text-amber-400 mt-1 flex items-baseline gap-1">
                    <span>{scheduler?.current_batch_size ?? (isIdle ? 0 : 1)}</span>
                    <span className="text-[10px] font-normal text-slate-400">/ {scheduler?.max_batch_size ?? 4} max</span>
                  </div>
                  <span className="text-[9px] text-slate-500 mt-0.5">Images in single forward pass</span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[10px] text-slate-400 uppercase">Aggregate YOLO FPS</span>
                  <div className="text-base font-bold text-emerald-400 mt-1">
                    {scheduler?.effective_aggregate_fps ? `${scheduler.effective_aggregate_fps} FPS` : isIdle ? '0.0 FPS' : 'Not available'}
                  </div>
                  <span className="text-[9px] text-slate-500 mt-0.5">Total detector throughput</span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[10px] text-slate-400 uppercase">Batch Inference Latency</span>
                  <div className="text-base font-bold text-purple-400 mt-1">
                    {scheduler?.last_batch_duration_ms ? `${scheduler.last_batch_duration_ms} ms` : 'Not available'}
                  </div>
                  <span className="text-[9px] text-slate-500 mt-0.5">
                    {scheduler?.avg_batch_duration_ms ? `Avg: ${scheduler.avg_batch_duration_ms} ms` : 'Monotonic timing'}
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[10px] text-slate-400 uppercase">Recent Batch Sizes</span>
                  <div className="text-xs font-bold text-slate-200 mt-1 truncate">
                    {scheduler?.recent_batch_sizes && scheduler.recent_batch_sizes.length > 0 
                      ? `[${scheduler.recent_batch_sizes.slice(-6).join(', ')}]` 
                      : 'Not available'}
                  </div>
                  <span className="text-[9px] text-slate-500 mt-0.5">History of real batches</span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[10px] text-slate-400 uppercase">Last Inference Time</span>
                  <div className="text-[11px] font-bold text-slate-300 mt-1 truncate">
                    {scheduler?.last_inference_timestamp 
                      ? new Date(scheduler.last_inference_timestamp).toLocaleTimeString() 
                      : 'Not available'}
                  </div>
                  <span className="text-[9px] text-slate-500 mt-0.5">
                    {scheduler?.total_batches ? `Batches: ${scheduler.total_batches}` : 'Scheduler idle'}
                  </span>
                </div>
              </div>

              {/* Per-Source Parallel Processing Table */}
              <div className="overflow-x-auto rounded-lg border border-slate-800">
                <table className="w-full text-left text-[11px]">
                  <thead className="bg-slate-900 text-slate-400 uppercase text-[9px] border-b border-slate-800">
                    <tr>
                      <th className="py-2 px-3">Camera Source Identity</th>
                      <th className="py-2 px-3">Status</th>
                      <th className="py-2 px-3">Frames Captured</th>
                      <th className="py-2 px-3">Submitted to YOLO</th>
                      <th className="py-2 px-3">Completed Inferences</th>
                      <th className="py-2 px-3">Superseded (Queue=1)</th>
                      <th className="py-2 px-3">Queue Depth</th>
                      <th className="py-2 px-3">Processing FPS</th>
                      <th className="py-2 px-3">Capture FPS</th>
                      <th className="py-2 px-3">Last Activity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                    {sources.length === 0 ? (
                      <tr>
                        <td colSpan={10} className="py-4 text-center text-slate-500 italic">
                          No active camera workers registered in scheduler. Start analyzing videos to observe real runtime metrics.
                        </td>
                      </tr>
                    ) : (
                      sources.map((src) => (
                        <tr key={src.source_id} className="hover:bg-slate-900/50 transition-colors">
                          <td className="py-2 px-3 font-semibold text-white">
                            <div className="flex flex-col">
                              <span>{src.name}</span>
                              <span className="text-[9px] text-slate-500 font-mono">
                                ID: {src.source_id} · {src.location}
                              </span>
                            </div>
                          </td>
                          <td className="py-2 px-3">
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase
                              ${src.status === 'capturing' || src.status === 'processing'
                                ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/30'
                                : src.status === 'inferring'
                                  ? 'bg-amber-950 text-amber-300 border border-amber-500/30'
                                  : src.status === 'error'
                                    ? 'bg-rose-950 text-rose-300 border border-rose-500/30'
                                    : 'bg-slate-800 text-slate-400'}`}
                            >
                              {src.status || 'READY'}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-bold text-cyan-400">
                            {src.captured_frames.toLocaleString()}
                          </td>
                          <td className="py-2 px-3 font-bold text-amber-400">
                            {src.submitted_frames.toLocaleString()}
                          </td>
                          <td className="py-2 px-3 font-bold text-emerald-400">
                            {src.completed_inferences.toLocaleString()}
                          </td>
                          <td className="py-2 px-3 text-slate-400">
                            {src.superseded_frames.toLocaleString()}
                          </td>
                          <td className="py-2 px-3 text-slate-300">
                            <span className={`px-1.5 py-0.2 rounded font-mono text-[10px]
                              ${src.current_queue_depth > 0 ? 'bg-amber-950/80 text-amber-400 font-bold' : 'text-slate-500'}`}
                            >
                              {src.current_queue_depth} / 1
                            </span>
                          </td>
                          <td className="py-2 px-3 font-bold text-cyan-300">
                            {src.processing_fps ? `${src.processing_fps} FPS` : 'Not available'}
                          </td>
                          <td className="py-2 px-3 text-slate-300">
                            {src.capture_fps ? `${src.capture_fps} FPS` : 'Not available'}
                          </td>
                          <td className="py-2 px-3 text-[10px] text-slate-500">
                            {src.last_inference_timestamp 
                              ? new Date(src.last_inference_timestamp).toLocaleTimeString() 
                              : src.last_capture_timestamp 
                                ? new Date(src.last_capture_timestamp).toLocaleTimeString() 
                                : 'Not available'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Concurrency & Batching Proof Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-1.5 text-cyan-400 font-bold mb-1">
                    <Layers className="w-3.5 h-3.5" />
                    <span className="text-[11px] uppercase">A. Parallel Capture</span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-relaxed">
                    Each active video feed runs an independent OS thread (<code className="text-cyan-300">Playback_&#123;id&#125;</code>) 
                    calling <code className="text-cyan-300">cv2.VideoCapture.read()</code> concurrently at its source FPS (24–30 FPS).
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-1.5 text-amber-400 font-bold mb-1">
                    <Cpu className="w-3.5 h-3.5" />
                    <span className="text-[11px] uppercase">B. Batched YOLOv8n</span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-relaxed">
                    The Dynamic Scheduler combines ready frames across active sources into a single <code className="text-amber-300">model.predict([f1, f2, ...])</code> call. 
                    Batch size equals the number of queued frames (up to 4) without coordinate mixing.
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-bold mb-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span className="text-[11px] uppercase">C. Concurrent Playback</span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-relaxed">
                    Per-camera kinematic trackers extrapolate bounding boxes continuously between detector arrivals, 
                    preventing bounding box glitches or stuttering while YOLO runs in the background scheduler.
                  </p>
                </div>
              </div>

              {/* DevTools Browser Console Opt-In Instructions */}
              <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-cyan-400 shrink-0" />
                  <div>
                    <span className="text-[11px] font-bold text-white">Browser DevTools Console Proof:</span>
                    <p className="text-[10px] text-slate-400">
                      Enable real-time namespaced logs in Console (<code className="text-cyan-300">[ CROWD-AI | PARALLEL-DIAG ]</code>).
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 w-full md:w-auto">
                  <code className="text-[10px] bg-slate-950 px-2 py-1 rounded border border-slate-800 text-cyan-300 font-mono">
                    localStorage.setItem("crowdAiDiagnostics", "true")
                  </code>
                  <button
                    type="button"
                    onClick={handleCopySnippet}
                    className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors shrink-0"
                    title="Copy command to clipboard"
                  >
                    {copiedSnippet ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    type="button"
                    onClick={handleToggleConsoleLogging}
                    className={`px-3 py-1 rounded text-[10px] font-bold transition-all shrink-0
                      ${consoleLoggingActive 
                        ? 'bg-rose-900/70 hover:bg-rose-800 text-rose-200 border border-rose-500/40' 
                        : 'bg-cyan-700 hover:bg-cyan-600 text-white'}`}
                  >
                    {consoleLoggingActive ? 'Disable Console Logs' : 'Enable Console Logs'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
