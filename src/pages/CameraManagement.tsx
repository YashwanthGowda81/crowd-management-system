import React, { useState, useRef } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { GlassCard } from '../components/GlassCard';
import { 
  Plus, 
  X, 
  Radio, 
  HardDrive, 
  RefreshCw, 
  Trash2, 
  Power, 
  ShieldAlert, 
  Camera as CameraIcon, 
  Film, 
  Video, 
  Pause, 
  Square, 
  RotateCcw,
  Activity
} from 'lucide-react';
import { motion } from 'framer-motion';

type AddCameraStep = 'SELECT_SOURCE' | 'RTSP_FORM' | 'WEBCAM_FORM' | 'VIDEO_FORM';

export const CameraManagement: React.FC = () => {
  const { 
    cameras, 
    events,
    selectedEventId,
    addCamera, 
    addWebcamCamera,
    uploadVideoCamera,
    analyzeCamera,
    controlCameraPlayback,
    removeCamera, 
    toggleCameraStatus, 
    toggleCameraEnabled 
  } = useCrowdSystem();

  const currentEventTitle = events.find(e => e.id === selectedEventId)?.title || 'Active Event';

  // Centralized Add Camera Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [modalStep, setModalStep] = useState<AddCameraStep>('SELECT_SOURCE');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State - RTSP
  const [name, setName] = useState('');
  const [rtspUrl, setRtspUrl] = useState('rtsp://192.168.10.');
  const [location, setLocation] = useState('Main Gate Entrance');
  const [capacity, setCapacity] = useState(200);

  // Form State - Webcam
  const [webcamName, setWebcamName] = useState('Workstation Web Camera 01');
  const [webcamLocation, setWebcamLocation] = useState('Control Desk');
  const [webcamCapacity, setWebcamCapacity] = useState(100);

  // Form State - Upload Video
  const [videoCamName, setVideoCamName] = useState('');
  const [videoLocation, setVideoLocation] = useState('Main Entrance Zone');
  const [videoCapacity, setVideoCapacity] = useState(200);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAddRtsp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !rtspUrl) return;

    setIsSubmitting(true);
    try {
      await addCamera({
        name,
        rtspUrl,
        location,
        status: 'ready',
        enabled: false,
        resolution: '1920x1080',
        fps: 30,
        capacity
      });

      setName('');
      setRtspUrl('rtsp://192.168.10.');
      setCapacity(200);
      setShowAddModal(false);
      setModalStep('SELECT_SOURCE');
    } catch (err) {
      console.error("Failed to persist camera to DB:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddWebcam = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await addWebcamCamera({
        name: webcamName,
        location: webcamLocation,
        capacity: webcamCapacity
      });
      setShowAddModal(false);
      setModalStep('SELECT_SOURCE');
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVideoFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!videoCamName) {
        setVideoCamName(`CCTV Footage (${file.name})`);
      }
      setModalStep('VIDEO_FORM');
    }
  };

  const handleCreateVideoCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !videoCamName.trim()) return;

    setIsSubmitting(true);
    try {
      await uploadVideoCamera(selectedFile, videoCamName, videoLocation, videoCapacity);
      setVideoCamName('');
      setSelectedFile(null);
      setShowAddModal(false);
      setModalStep('SELECT_SOURCE');
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const analyzingCount = cameras.filter(c => c.playbackStatus === 'analyzing' || c.playbackStatus === 'playing').length;

  return (
    <div className="space-y-6 pb-12 font-mono">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border pb-4">
        <div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            <CameraIcon className="w-6 h-6 text-cyan-400" />
            <span>Camera Access & Health Management</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Centralized registration hub for wired IP/RTSP cameras, live laptop webcams, and uploaded CCTV virtual camera feeds.
          </p>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Operation:</span>
            <span className="text-xs text-cyan-300 font-bold bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
              {currentEventTitle}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setModalStep('SELECT_SOURCE');
              setShowAddModal(true);
            }}
            disabled={isSubmitting}
            className="py-2.5 px-5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-extrabold text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-[0_0_16px_rgba(6,182,212,0.3)]"
          >
            <Plus className="w-4 h-4" />
            <span>{isSubmitting ? 'Processing...' : '+ Add Camera'}</span>
          </button>

          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleVideoFileSelect} 
            accept="video/mp4,video/avi,video/mov,video/mkv" 
            className="hidden" 
          />
        </div>
      </div>

      {/* Diagnostics Panel (Top Placement) */}
      <div className="cyber-glass p-5 rounded-xl border border-blue-500/10 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded bg-slate-950 border border-slate-900 text-cyan-400">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase text-slate-300">GPU Pipeline Load</h4>
            <p className="text-[10px] text-slate-500 mt-0.5">YOLO inference engine utilizes local GPU compute for active camera workers.</p>
          </div>
        </div>

        <div className="flex items-start gap-3 border-t md:border-t-0 md:border-l border-slate-900/60 pt-4 md:pt-0 md:pl-6">
          <div className="p-2 rounded bg-slate-950 border border-slate-900 text-cyan-400">
            <Radio className="w-5 h-5 animate-pulse text-cyan-400" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase text-slate-300">RTSP & Video Sockets Latency</h4>
            <p className="text-[10px] text-slate-500 mt-0.5">Bounded queue (maxsize=2) maintains ~33ms real-time processing latency.</p>
          </div>
        </div>

        <div className="flex items-start gap-3 border-t md:border-t-0 md:border-l border-slate-900/60 pt-4 md:pt-0 md:pl-6">
          <div className="p-2 rounded bg-slate-950 border border-slate-900 text-cyan-400">
            <RefreshCw className="w-5 h-5 animate-spin" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase text-slate-300">MySQL Database Storage</h4>
            <p className="text-[10px] text-slate-500 mt-0.5">Crowd analytics snapshots continuously saved to MySQL `crowd_analytics` table.</p>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="p-3.5 rounded-xl bg-cyan-950/40 border border-cyan-500/20 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-cyan-400">
          <ShieldAlert className="w-4 h-4" />
          <span>Active Pipeline: <strong>{analyzingCount}</strong> of <strong>{cameras.length}</strong> Camera Streams Currently Analyzing.</span>
        </div>
        <span className="text-[10px] text-slate-400">Click <strong>[ ANALYZE ]</strong> on any camera card to activate YOLO AI processing.</span>
      </div>

      {/* CENTRALIZED 3-OPTION ADD CAMERA MODAL */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-full max-w-lg cyber-glass p-6 border border-cyan-500/40 rounded-2xl space-y-6 shadow-[0_0_40px_rgba(6,182,212,0.2)]"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <CameraIcon className="w-5 h-5 text-cyan-400" />
                  <span>ADD CAMERA SOURCE</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Select input camera source for 30 FPS YOLO AI analysis pipeline.</p>
              </div>
              <button onClick={() => setShowAddModal(false)} className="text-slate-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* STEP 1: 3-SOURCE SELECTION OPTIONS */}
            {modalStep === 'SELECT_SOURCE' && (
              <div className="grid grid-cols-1 gap-4">
                <button
                  onClick={() => setModalStep('RTSP_FORM')}
                  className="p-4 rounded-xl bg-slate-950 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-500/50 text-left transition-all group flex items-start gap-4"
                >
                  <div className="p-3 rounded-lg bg-cyan-950 text-cyan-400 group-hover:scale-110 transition-transform">
                    <Radio className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white group-hover:text-cyan-400">📡 Wired / IP / RTSP Camera</h4>
                    <p className="text-xs text-slate-400 mt-1">Connect physical network surveillance cameras via RTSP stream URL.</p>
                  </div>
                </button>

                <button
                  onClick={() => setModalStep('WEBCAM_FORM')}
                  className="p-4 rounded-xl bg-slate-950 hover:bg-purple-950/40 border border-slate-800 hover:border-purple-500/50 text-left transition-all group flex items-start gap-4"
                >
                  <div className="p-3 rounded-lg bg-purple-950 text-purple-400 group-hover:scale-110 transition-transform">
                    <CameraIcon className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white group-hover:text-purple-400">📷 Web Camera / Record</h4>
                    <p className="text-xs text-slate-400 mt-1">Use laptop/PC live webcam stream for real-time crowd analysis.</p>
                  </div>
                </button>

                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-4 rounded-xl bg-slate-950 hover:bg-emerald-950/40 border border-slate-800 hover:border-emerald-500/50 text-left transition-all group flex items-start gap-4"
                >
                  <div className="p-3 rounded-lg bg-emerald-950 text-emerald-400 group-hover:scale-110 transition-transform">
                    <Film className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white group-hover:text-emerald-400">🎥 Upload Video</h4>
                    <p className="text-xs text-slate-400 mt-1">Upload MP4/AVI/MOV crowd footage to process as a virtual camera.</p>
                  </div>
                </button>
              </div>
            )}

            {/* STEP 2A: RTSP FORM */}
            {modalStep === 'RTSP_FORM' && (
              <form onSubmit={handleAddRtsp} className="space-y-4 text-xs">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Camera Name *</label>
                  <input 
                    type="text" required placeholder="e.g. Gate 04 Main Entrance"
                    value={name} onChange={e => setName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">RTSP Connection URL *</label>
                  <input 
                    type="text" required placeholder="rtsp://192.168.10.105/live"
                    value={rtspUrl} onChange={e => setRtspUrl(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none font-mono"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold uppercase text-slate-400 block">Location</label>
                    <input 
                      type="text" placeholder="Zone Gate A"
                      value={location} onChange={e => setLocation(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold uppercase text-slate-400 block">Max Safe Capacity</label>
                    <input 
                      type="number" value={capacity} onChange={e => setCapacity(parseInt(e.target.value))}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-4 border-t border-slate-900">
                  <button type="button" onClick={() => setModalStep('SELECT_SOURCE')} className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400">Back</button>
                  <button type="submit" disabled={isSubmitting} className="px-5 py-2 rounded-xl bg-cyan-600 text-white font-bold">Create Camera</button>
                </div>
              </form>
            )}

            {/* STEP 2B: WEBCAM FORM */}
            {modalStep === 'WEBCAM_FORM' && (
              <form onSubmit={handleAddWebcam} className="space-y-4 text-xs">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Webcam Name *</label>
                  <input 
                    type="text" required value={webcamName} onChange={e => setWebcamName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold uppercase text-slate-400 block">Location</label>
                    <input 
                      type="text" value={webcamLocation} onChange={e => setWebcamLocation(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold uppercase text-slate-400 block">Capacity</label>
                    <input 
                      type="number" value={webcamCapacity} onChange={e => setWebcamCapacity(parseInt(e.target.value))}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-4 border-t border-slate-900">
                  <button type="button" onClick={() => setModalStep('SELECT_SOURCE')} className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400">Back</button>
                  <button type="submit" disabled={isSubmitting} className="px-5 py-2 rounded-xl bg-purple-600 text-white font-bold">Create Camera</button>
                </div>
              </form>
            )}

            {/* STEP 2C: UPLOAD VIDEO FORM */}
            {modalStep === 'VIDEO_FORM' && (
              <form onSubmit={handleCreateVideoCamera} className="space-y-4 text-xs">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Camera Name * (Required)</label>
                  <input 
                    type="text" 
                    required 
                    placeholder="e.g. Main Gate CCTV Test"
                    value={videoCamName} 
                    onChange={e => setVideoCamName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none focus:border-cyan-500/40"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold uppercase text-slate-400 block">Location / Zone</label>
                    <input 
                      type="text" 
                      value={videoLocation} 
                      onChange={e => setVideoLocation(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold uppercase text-slate-400 block">Venue Capacity</label>
                    <input 
                      type="number" 
                      value={videoCapacity} 
                      onChange={e => setVideoCapacity(parseInt(e.target.value))}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Selected CCTV Video File</label>
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-slate-300">
                    <span className="truncate max-w-xs">{selectedFile ? selectedFile.name : 'No file selected'}</span>
                    <button 
                      type="button" 
                      onClick={() => fileInputRef.current?.click()}
                      className="text-xs text-cyan-400 underline font-bold"
                    >
                      Change Video
                    </button>
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-900">
                  <button type="button" onClick={() => setModalStep('SELECT_SOURCE')} className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400">Back</button>
                  <button 
                    type="submit" 
                    disabled={isSubmitting || !videoCamName.trim()} 
                    className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold"
                  >
                    {isSubmitting ? 'Creating Virtual Camera...' : 'Create Virtual Camera'}
                  </button>
                </div>
              </form>
            )}
          </motion.div>
        </div>
      )}

      {/* NO CAMERAS EMPTY STATE */}
      {cameras.length === 0 ? (
        <GlassCard className="p-12 text-center space-y-4 border border-dashed border-slate-800">
          <CameraIcon className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-white uppercase tracking-wider">No cameras configured for this event</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            There are currently zero cameras registered for <strong>{currentEventTitle}</strong>. Click <strong>"+ Add Camera"</strong> above to register an RTSP stream, local webcam, or upload video.
          </p>
          <button
            onClick={() => {
              setModalStep('SELECT_SOURCE');
              setShowAddModal(true);
            }}
            className="py-2.5 px-6 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Add First Camera Source
          </button>
        </GlassCard>
      ) : (
        /* ACTIVE CAMERA CARDS GRID */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cameras.map((cam) => {
            const isAnalyzing = cam.playbackStatus === 'analyzing' || cam.playbackStatus === 'playing';
            const isWebcam = cam.sourceType === 'webcam';
            const isVideo = cam.sourceType === 'video';

            return (
              <GlassCard key={cam.id} className="p-4 space-y-4 border border-cyber-border hover:border-cyan-500/40 transition-all">
                {/* Card Header */}
                <div className="flex items-start justify-between gap-2 border-b border-slate-900 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${isAnalyzing ? 'bg-green-400 animate-pulse' : 'bg-yellow-500'}`} />
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

                {/* Video Stream Preview Box */}
                <div className="relative aspect-video rounded-xl bg-slate-950 border border-slate-900 overflow-hidden flex items-center justify-center group">
                  {isAnalyzing ? (
                    <img 
                      src={`http://localhost:8000/api/cameras/${cam.id}/stream`} 
                      alt={cam.name} 
                      className="w-full h-full object-contain bg-black z-0"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  ) : null}

                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent z-10 pointer-events-none" />

                  {/* Grid Overlay */}
                  {!isAnalyzing && (
                    <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:2rem_2rem]" />
                  )}

                  {/* Standby State */}
                  {!isAnalyzing && (
                    <div className="z-0 text-center space-y-2">
                      <Video className="w-8 h-8 mx-auto text-slate-600" />
                      <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-bold">
                        No active video source
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
                    <span className="bg-black/80 backdrop-blur-md text-xs px-2.5 py-1 rounded-lg text-white font-extrabold border border-white/10 font-mono">
                      Detections: <span className="text-cyan-400">{isAnalyzing && cam.count ? `${cam.count} persons` : '0 detections'}</span>
                    </span>
                    <span className="bg-black/80 backdrop-blur-md text-xs px-2.5 py-1 rounded-lg text-white font-extrabold border border-white/10 font-mono">
                      Density: <span className="text-yellow-400">{isAnalyzing ? `${cam.density ?? 0}%` : '0%'}</span>
                    </span>
                  </div>

                  <div className="absolute bottom-2 right-2 z-20">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-extrabold uppercase border ${
                      !isAnalyzing ? 'bg-slate-900 border-slate-800 text-slate-400' :
                      cam.risk === 'critical' ? 'bg-red-950 border-red-500 text-red-400' :
                      cam.risk === 'high' ? 'bg-orange-950 border-orange-500 text-orange-400' :
                      cam.risk === 'medium' ? 'bg-yellow-950 border-yellow-500 text-yellow-400' :
                      'bg-green-950 border-green-500 text-green-400'
                    }`}>
                      {isAnalyzing ? cam.risk : 'No current risk assessment'}
                    </span>
                  </div>
                </div>

                {/* PROMINENT ANALYZE BUTTON WHEN CAMERA IS READY */}
                {!isAnalyzing ? (
                  <button
                    onClick={() => analyzeCamera(cam.id)}
                    className="w-full py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-[0_0_16px_rgba(6,182,212,0.3)]"
                  >
                    <Activity className="w-4 h-4" />
                    <span>ANALYZE</span>
                  </button>
                ) : (
                  /* PLAYBACK CONTROLS WHEN ANALYZING */
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => controlCameraPlayback(cam.id, 'pause')}
                      className="py-2 rounded-lg bg-yellow-950/60 hover:bg-yellow-900/60 border border-yellow-500/30 text-yellow-400 text-[10px] font-bold flex items-center justify-center gap-1"
                    >
                      <Pause className="w-3.5 h-3.5" />
                      <span>Pause</span>
                    </button>
                    <button
                      onClick={() => controlCameraPlayback(cam.id, 'stop')}
                      className="py-2 rounded-lg bg-red-950/60 hover:bg-red-900/60 border border-red-500/30 text-red-400 text-[10px] font-bold flex items-center justify-center gap-1"
                    >
                      <Square className="w-3.5 h-3.5" />
                      <span>Stop</span>
                    </button>
                    <button
                      onClick={() => controlCameraPlayback(cam.id, 'restart')}
                      className="py-2 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-400 text-[10px] font-bold flex items-center justify-center gap-1"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Restart</span>
                    </button>
                  </div>
                )}

                <div className="flex items-center justify-between border-t border-slate-900 pt-3 text-[10px]">
                  <button
                    onClick={() => toggleCameraEnabled(cam.id)}
                    className={`px-3 py-1 rounded font-bold uppercase border transition-colors flex items-center gap-1.5 ${
                      cam.enabled 
                        ? 'bg-cyan-950/60 border-cyan-500/30 text-cyan-400' 
                        : 'bg-slate-900 border-slate-800 text-slate-500'
                    }`}
                  >
                    <Power className="w-3 h-3" /> {cam.enabled ? 'Processing ON' : 'Disabled'}
                  </button>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => toggleCameraStatus(cam.id)}
                      className="p-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
                      title="Toggle Online/Offline Status"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => removeCamera(cam.id)}
                      className="p-1.5 rounded bg-slate-900 hover:bg-red-950 text-slate-400 hover:text-red-400"
                      title="Remove Camera from Database"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
      )}
    </div>
  );
};
