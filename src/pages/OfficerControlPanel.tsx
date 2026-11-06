import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { GlassCard } from '../components/GlassCard';
import { 
  Sliders, 
  Play, 
  Camera as CameraIcon, 
  XCircle, 
  Activity,
  Video,
  Pause,
  Square,
  RotateCcw,
  Settings,
  PhoneCall,
  Radio,
  Users,
  Compass
} from 'lucide-react';
import { motion } from 'framer-motion';

export const OfficerControlPanel: React.FC = () => {
  const navigate = useNavigate();
  const { 
    aiModules, 
    toggleAIModule, 
    cameras, 
    events,
    selectedEventId,
    controlCameraPlayback,
    addEvent,
    guards,
    instructionLogs
  } = useCrowdSystem();

  // Create Event Modal State
  const [showEventModal, setShowEventModal] = useState(false);
  const [newEventTitle, setNewEventTitle] = useState('');
  const [newEventCapacity, setNewEventCapacity] = useState(1500);
  const [newEventStaff, setNewEventStaff] = useState(30);
  const [newEventRisk, setNewEventRisk] = useState<'low' | 'medium' | 'high'>('medium');

  const handleCreateEvent = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEventTitle.trim()) return;
    addEvent({
      title: newEventTitle,
      capacity: newEventCapacity,
      staff: newEventStaff,
      risk: newEventRisk,
      start: 'Now Active',
      end: '22:00 PM',
      limits: Math.round(newEventCapacity * 0.85),
      assignedCameras: cameras.map(c => c.id)
    });
    setNewEventTitle('');
    setShowEventModal(false);
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Top Banner & Quick Action */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
            <Sliders className="w-4 h-4" />
            <span>CENTRAL COMMAND INTERFACE</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Officer Control Panel
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Monitor active surveillance streams, adjust live AI inference module toggles, and manage venue events.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Active Event Display */}
          <div className="flex items-center gap-2 bg-slate-900 px-3 py-2.5 rounded-xl border border-cyan-500/30">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider font-mono">Operation:</span>
            <span className="text-cyan-300 font-bold text-xs max-w-[200px] truncate">
              {events.find(e => e.id === selectedEventId)?.title || (events.length > 0 ? events[0].title : 'Active Operation')}
            </span>
          </div>

          <button
            onClick={() => navigate('/staff-communication')}
            className="px-4 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-cyber-border text-cyan-400 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <Compass className="w-4 h-4 text-cyan-400" />
            <span>Ground Coordination ➔</span>
          </button>

          <button
            onClick={() => navigate('/cameras')}
            className="px-4 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-cyber-border text-cyan-400 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            <span>Manage Cameras ➔</span>
          </button>
          
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.3)] active:scale-98"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>Start Live Surveillance ➔</span>
          </button>
        </div>
      </div>

      {/* CAMERA MONITORING DISPLAY SECTION */}
      <GlassCard className="p-6 space-y-4 border-cyan-500/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-extrabold text-white flex items-center gap-2">
              <CameraIcon className="w-5 h-5 text-cyan-400" />
              <span>Camera Section & Active Stream Telemetry</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Live multi-camera processing powered by 30 FPS YOLO AI analysis. Camera registration is managed in Camera Access.
            </p>
          </div>

          <button
            onClick={() => navigate('/cameras')}
            className="py-2.5 px-5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/40 text-cyan-400 font-extrabold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            <span>+ Add Camera in Camera Access</span>
          </button>
        </div>

        {/* ACTIVE CAMERA CARDS GRID */}
        {cameras.length === 0 ? (
          <div className="text-center py-12 px-4 rounded-xl border border-dashed border-slate-800 bg-slate-950/40">
            <CameraIcon className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-300">No cameras configured for this event.</p>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              This event currently has no camera streams assigned. You can register RTSP streams, local webcams, or offline videos in Camera Access.
            </p>
            <button
              onClick={() => navigate('/cameras')}
              className="mt-4 px-4 py-2 rounded-lg bg-cyan-950 hover:bg-cyan-900 text-cyan-400 border border-cyan-500/30 text-xs font-semibold"
            >
              Configure Cameras for this Event ➔
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-2">
          {cameras.map((cam) => {
            const isAnalyzing = cam.enabled && cam.status === 'online';
            const isWebcam = cam.sourceType === 'webcam';
            const isVideo = cam.sourceType === 'video';

            return (
              <GlassCard key={cam.id} className="p-4 space-y-4 border border-cyber-border hover:border-cyan-500/40 transition-all font-mono">
                {/* Card Header */}
                <div className="flex items-start justify-between gap-2 border-b border-slate-900 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${isAnalyzing ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`} />
                      <h3 className="font-bold text-sm text-white truncate max-w-[180px]">{cam.name}</h3>
                    </div>
                    <span className="text-[10px] text-slate-500 block mt-0.5">{cam.location}</span>
                  </div>

                  <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
                    isWebcam ? 'bg-purple-950/60 border-purple-500/30 text-purple-400' :
                    isVideo ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-400' :
                    'bg-cyan-950/60 border-cyan-500/30 text-cyan-400'
                  }`}>
                    {isWebcam ? '📷 Web Camera' : isVideo ? '🎥 Video' : '📡 RTSP'}
                  </span>
                </div>

                {/* Video Stream Box */}
                <div className="relative aspect-video rounded-xl bg-slate-950 border border-slate-900 overflow-hidden flex items-center justify-center group">
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent z-10 pointer-events-none" />

                  {/* Grid Lines */}
                  <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:2rem_2rem] pointer-events-none" />

                  {isAnalyzing ? (
                    <img
                      src={`http://localhost:8000/api/cameras/${cam.id}/stream`}
                      alt={cam.name}
                      className="w-full h-full object-contain bg-black z-0"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className="z-0 text-center space-y-2">
                      <Video className="w-8 h-8 mx-auto text-slate-600" />
                      <span className="text-[10px] text-slate-500 block uppercase tracking-wider font-bold">
                        PAUSED / OFF
                      </span>
                    </div>
                  )}

                  {/* FPS Overlay */}
                  <div className="absolute top-2 left-2 z-20 flex items-center gap-2">
                    <span className="bg-black/70 backdrop-blur-sm text-[9px] px-2 py-0.5 rounded text-cyan-400 border border-cyan-500/30 font-bold">
                      FPS: {cam.sourceFps || 30}
                    </span>
                    <span className="bg-black/70 backdrop-blur-sm text-[9px] px-2 py-0.5 rounded text-green-400 border border-green-500/30 font-bold">
                      Proc FPS: {cam.processingFps || 30}
                    </span>
                  </div>

                  {/* Count Overlay */}
                  <div className="absolute bottom-2 left-2 z-20 flex items-center gap-2">
                    <span className="bg-black/80 backdrop-blur-md text-xs px-2.5 py-1 rounded-lg text-white font-extrabold border border-white/10">
                      People: <span className="text-cyan-400">{cam.count ?? 0}</span>
                    </span>
                    <span className="bg-black/80 backdrop-blur-md text-xs px-2.5 py-1 rounded-lg text-white font-extrabold border border-white/10">
                      Density: <span className="text-yellow-400">{cam.density ?? 0}%</span>
                    </span>
                  </div>

                  <div className="absolute bottom-2 right-2 z-20">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-extrabold uppercase border ${
                      cam.risk === 'critical' ? 'bg-red-950 border-red-500 text-red-400' :
                      cam.risk === 'high' ? 'bg-orange-950 border-orange-500 text-orange-400' :
                      cam.risk === 'medium' ? 'bg-yellow-950 border-yellow-500 text-yellow-400' :
                      'bg-green-950 border-green-500 text-green-400'
                    }`}>
                      {cam.risk}
                    </span>
                  </div>
                </div>

                {/* Playback Controls */}
                <div className="grid grid-cols-4 gap-1.5 pt-1">
                  <button
                    onClick={() => controlCameraPlayback(cam.id, 'play')}
                    className="py-1.5 rounded-lg bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold flex items-center justify-center gap-1"
                  >
                    <Play className="w-3 h-3 fill-emerald-400" />
                    <span>Play</span>
                  </button>
                  <button
                    onClick={() => controlCameraPlayback(cam.id, 'pause')}
                    className="py-1.5 rounded-lg bg-yellow-950/60 hover:bg-yellow-900/60 border border-yellow-500/30 text-yellow-400 text-[10px] font-bold flex items-center justify-center gap-1"
                  >
                    <Pause className="w-3 h-3" />
                    <span>Pause</span>
                  </button>
                  <button
                    onClick={() => controlCameraPlayback(cam.id, 'stop')}
                    className="py-1.5 rounded-lg bg-red-950/60 hover:bg-red-900/60 border border-red-500/30 text-red-400 text-[10px] font-bold flex items-center justify-center gap-1"
                  >
                    <Square className="w-3 h-3" />
                    <span>Stop</span>
                  </button>
                  <button
                    onClick={() => controlCameraPlayback(cam.id, 'restart')}
                    className="py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-400 text-[10px] font-bold flex items-center justify-center gap-1"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Restart</span>
                  </button>
                </div>
              </GlassCard>
            );
          })}
        </div>
        )}
      </GlassCard>

      {/* AI Inference Modules Control Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-900 pb-2">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              <span>AI Inference Modules Control</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Enable or disable core Computer Vision detection modules in real-time.
            </p>
          </div>
          <span className="text-xs font-mono text-cyan-400 bg-cyan-950/50 border border-cyan-500/20 px-2.5 py-1 rounded-lg">
            {aiModules.filter(m => m.enabled).length} / {aiModules.length} Modules Active
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {aiModules.map((module) => {
            const isGreen = module.health === 'green';
            const isYellow = module.health === 'yellow';
            
            return (
              <GlassCard key={module.id} className={`p-5 transition-all relative overflow-hidden border ${module.enabled ? 'border-cyber-border hover:border-cyan-500/40' : 'border-slate-900 opacity-60'}`}>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${isGreen ? 'bg-green-400 shadow-[0_0_8px_#4ade80]' : isYellow ? 'bg-yellow-400 shadow-[0_0_8px_#facc15]' : 'bg-red-500'}`} />
                    <h4 className="font-bold text-sm text-white">{module.name}</h4>
                  </div>

                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={module.enabled} 
                      onChange={() => toggleAIModule(module.id)} 
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-slate-900 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-600 peer-checked:after:bg-white" />
                  </label>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed mb-4 min-h-[36px]">
                  {module.description}
                </p>

                <div className="flex items-center justify-between pt-3 border-t border-slate-900 text-[10px] font-mono">
                  <div className="flex items-center gap-1">
                    <span className="text-slate-500">Status:</span>
                    <span className={`font-bold uppercase px-1.5 py-0.2 rounded border ${module.enabled ? 'bg-green-950/40 border-green-500/20 text-green-400' : 'bg-slate-900 border-slate-800 text-slate-500'}`}>
                      {module.status}
                    </span>
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
      </div>

      {/* TACTICAL STAFF ROSTER & DISPATCH DIRECTIVES SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* On-Duty Security Personnel (Col 7) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-900 pb-2">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-cyan-400" />
                <span>On-Duty Security Personnel & Radio Fleet</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Active security guards deployed across event sectors with live radio telemetry.
              </p>
            </div>
            <button
              onClick={() => navigate('/staff-communication')}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-mono font-bold flex items-center gap-1"
            >
              <span>Manage Staff ➔</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {guards.length === 0 ? (
              <div className="col-span-2 text-center py-8 rounded-xl bg-slate-950/40 border border-slate-900 text-slate-500 text-xs">
                No security personnel registered. Deploy staff in Security Staff Dispatch.
              </div>
            ) : (
              guards.slice(0, 6).map((guard) => (
                <GlassCard key={guard.id} className="p-3.5 space-y-2 border-slate-900 hover:border-cyan-500/30 transition-all font-mono text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-cyan-950/80 border border-cyan-500/30 flex items-center justify-center font-bold text-cyan-400 text-[10px]">
                        {guard.name.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-bold text-white leading-tight">{guard.name}</p>
                        <p className="text-[10px] text-slate-400">{guard.zone}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
                      guard.status === 'dispatched' ? 'bg-amber-950/60 border-amber-500/30 text-amber-300' :
                      guard.status === 'alerted' ? 'bg-red-950/60 border-red-500/30 text-red-300' :
                      'bg-emerald-950/60 border-emerald-500/30 text-emerald-300'
                    }`}>
                      {guard.status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-slate-900/80 text-[10px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <Radio className="w-3 h-3 text-cyan-400" />
                      <span>{guard.mobileStatus}</span>
                    </span>
                    <span>Battery: {guard.battery}%</span>
                  </div>
                </GlassCard>
              ))
            )}
          </div>
        </div>

        {/* Command Directives & Dispatch Logs (Col 5) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-900 pb-2">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <PhoneCall className="w-5 h-5 text-cyan-400" />
                <span>Command Directives Queue</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time incident response transmissions sent to field personnel.
              </p>
            </div>
            <span className="text-[10px] font-mono font-bold text-cyan-400 bg-cyan-950/50 border border-cyan-500/20 px-2 py-0.5 rounded">
              {instructionLogs.length} Logged
            </span>
          </div>

          <GlassCard className="p-4 space-y-3 max-h-[300px] overflow-y-auto">
            {instructionLogs.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-xs">
                No active directives transmitted. Control room communications on standby.
              </div>
            ) : (
              instructionLogs.slice(0, 5).map((log) => (
                <div key={log.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 text-xs space-y-1 font-mono">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-cyan-300">{log.recipient}</span>
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase border ${
                      log.priority === 'emergency' ? 'bg-red-950 border-red-500/40 text-red-300' :
                      log.priority === 'urgent' ? 'bg-amber-950 border-amber-500/40 text-amber-300' :
                      'bg-slate-900 border-slate-800 text-slate-400'
                    }`}>
                      {log.priority}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 font-sans">{log.text}</p>
                  <div className="flex justify-between items-center text-[9px] text-slate-500 pt-1">
                    <span>{log.timestamp}</span>
                    <span className="text-emerald-400 font-bold">{log.deliveryStatus}</span>
                  </div>
                </div>
              ))
            )}
          </GlassCard>
        </div>
      </div>

      {/* CREATE EVENT MODAL */}
      {showEventModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-full max-w-lg cyber-glass p-6 border border-cyan-500/30 rounded-2xl space-y-5"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Create New Event Profile</h3>
              <button onClick={() => setShowEventModal(false)} className="text-slate-500 hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateEvent} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 block">Event Title</label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. World Cricket Championship Semi-Final"
                  value={newEventTitle}
                  onChange={(e) => setNewEventTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none focus:border-cyan-500/40"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Max Capacity</label>
                  <input 
                    type="number" 
                    value={newEventCapacity}
                    onChange={(e) => setNewEventCapacity(parseInt(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Security Personnel</label>
                  <input 
                    type="number" 
                    value={newEventStaff}
                    onChange={(e) => setNewEventStaff(parseInt(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 block">Risk Profile</label>
                <select 
                  value={newEventRisk}
                  onChange={(e) => setNewEventRisk(e.target.value as any)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                >
                  <option value="low">Low Risk</option>
                  <option value="medium">Medium Risk</option>
                  <option value="high">High Risk</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-900">
                <button
                  type="button"
                  onClick={() => setShowEventModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold"
                >
                  Save Event
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
};
