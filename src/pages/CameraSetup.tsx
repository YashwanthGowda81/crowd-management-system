import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { 
  Camera as CameraIcon, 
  Upload, 
  Radio, 
  Film, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowRight, 
  Play, 
  Check, 
  Server, 
  MapPin, 
  Users, 
  RefreshCw,
  Trash2
} from 'lucide-react';
import { motion } from 'framer-motion';

export const CameraSetup: React.FC = () => {
  const navigate = useNavigate();
  const { 
    selectedEventId, 
    events, 
    cameras, 
    fetchCameras, 
    addCamera, 
    uploadVideoCamera, 
    analyzeCamera, 
    removeCamera,
    onboardingStatus,
    checkOnboardingStatus 
  } = useCrowdSystem();

  const [activeTab, setActiveTab] = useState<'RTSP' | 'UPLOAD'>('RTSP');

  // RTSP Camera Form State
  const [rtspName, setRtspName] = useState('');
  const [rtspUrl, setRtspUrl] = useState('rtsp://192.168.10.50:554/live/stream');
  const [rtspLocation, setRtspLocation] = useState('North Gate Entrance');
  const [rtspCapacity, setRtspCapacity] = useState(250);
  const [isSubmittingRtsp, setIsSubmittingRtsp] = useState(false);
  const [rtspFeedback, setRtspFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  // Video Upload Form State
  const [videoName, setVideoName] = useState('');
  const [videoLocation, setVideoLocation] = useState('Main Concourse Hall');
  const [videoCapacity, setVideoCapacity] = useState(300);
  const [selectedVideoFile, setSelectedVideoFile] = useState<File | null>(null);
  const [isUploadingVideo, setIsUploadingVideo] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeEvent = events.find(e => e.id === selectedEventId) || onboardingStatus?.event;

  // Refresh cameras for active event on mount
  useEffect(() => {
    if (selectedEventId) {
      fetchCameras(selectedEventId);
    }
  }, [selectedEventId]);

  // Handle RTSP Registration
  const handleRegisterRtsp = async (e: React.FormEvent) => {
    e.preventDefault();
    setRtspFeedback(null);

    if (!rtspName.trim()) {
      setRtspFeedback({ type: 'error', msg: 'Please provide a camera name.' });
      return;
    }
    if (!rtspUrl.trim() || !rtspUrl.toLowerCase().startsWith('rtsp://')) {
      setRtspFeedback({ type: 'error', msg: 'A valid RTSP URL starting with rtsp:// is required.' });
      return;
    }

    setIsSubmittingRtsp(true);
    try {
      // Never expose credentials in logs
      const registered = await addCamera({
        name: rtspName.trim(),
        rtspUrl: rtspUrl.trim(),
        location: rtspLocation.trim() || 'Perimeter Gate',
        capacity: Number(rtspCapacity) || 200,
        status: 'ready',
        enabled: true,
        resolution: '1920x1080',
        fps: 30,
        event_id: selectedEventId
      });

      if (registered && registered.id) {
        setRtspFeedback({ 
          type: 'success', 
          msg: `Camera "${registered.name}" registered successfully in READY status.` 
        });
        setRtspName('');
        await fetchCameras(selectedEventId);
        await checkOnboardingStatus(selectedEventId);
      } else {
        throw new Error('Backend failed to return confirmed camera registration.');
      }
    } catch (err: any) {
      setRtspFeedback({ 
        type: 'error', 
        msg: err.message || 'Failed to register RTSP camera with surveillance backend.' 
      });
    } finally {
      setIsSubmittingRtsp(false);
    }
  };

  // Handle Video File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadFeedback(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const validExtensions = ['.mp4', '.avi', '.mov', '.mkv'];
      const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

      if (!validExtensions.includes(fileExt)) {
        setUploadFeedback({ 
          type: 'error', 
          msg: 'Unsupported video format. The AI engine accepts MP4, AVI, MOV, and MKV files.' 
        });
        setSelectedVideoFile(null);
        return;
      }

      setSelectedVideoFile(file);
      if (!videoName) {
        setVideoName(`CCTV Footage (${file.name})`);
      }
    }
  };

  // Handle Video Upload
  const handleUploadVideo = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadFeedback(null);

    if (!selectedVideoFile) {
      setUploadFeedback({ type: 'error', msg: 'Please select a CCTV video file to upload.' });
      return;
    }
    if (!videoName.trim()) {
      setUploadFeedback({ type: 'error', msg: 'Please enter a camera name for this video feed.' });
      return;
    }

    setIsUploadingVideo(true);
    try {
      const uploadedCam = await uploadVideoCamera(
        selectedVideoFile,
        videoName.trim(),
        videoLocation.trim() || 'Uploaded CCTV Area',
        Number(videoCapacity) || 200,
        undefined,
        selectedEventId
      );

      if (uploadedCam && uploadedCam.id) {
        setUploadFeedback({
          type: 'success',
          msg: `Video "${selectedVideoFile.name}" uploaded & configured as virtual camera "${uploadedCam.name}".`
        });
        setSelectedVideoFile(null);
        setVideoName('');
        if (fileInputRef.current) fileInputRef.current.value = '';
        await fetchCameras(selectedEventId);
        await checkOnboardingStatus(selectedEventId);
      } else {
        throw new Error('Video upload could not be completed by backend.');
      }
    } catch (err: any) {
      setUploadFeedback({
        type: 'error',
        msg: err.message || 'Failed to upload video file. Please check file size and format.'
      });
    } finally {
      setIsUploadingVideo(false);
    }
  };

  // Filter cameras belonging to the active event
  const currentEventCameras = cameras.filter(c => !selectedEventId || c.eventId === selectedEventId);
  const hasConfiguredSource = currentEventCameras.length > 0;

  return (
    <div className="max-w-5xl mx-auto py-6 space-y-6">
      {/* Onboarding Workflow Steps Indicator */}
      <div className="flex items-center justify-between px-6 py-4 rounded-2xl bg-slate-900/80 border border-cyber-border/40 select-none">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-green-500/20 text-green-400 border border-green-500/40 flex items-center justify-center font-bold text-xs">
            <Check className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs font-bold text-green-400 uppercase tracking-wider">Step 1: Event Configured</p>
            <p className="text-[10px] text-slate-300 truncate max-w-[180px]">
              {activeEvent?.title || 'Active Operation'}
            </p>
          </div>
        </div>

        <div className="h-0.5 w-12 bg-cyan-500/50 hidden sm:block" />

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 flex items-center justify-center font-bold text-xs">
            2
          </div>
          <div>
            <p className="text-xs font-bold text-cyan-400 uppercase tracking-wider">Step 2: Camera Setup</p>
            <p className="text-[10px] text-slate-400">RTSP Stream or CCTV Video</p>
          </div>
        </div>

        <div className="h-0.5 w-12 bg-slate-800 hidden sm:block" />

        <div className="flex items-center gap-3 opacity-50">
          <div className="w-8 h-8 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center font-bold text-xs">
            3
          </div>
          <div className="hidden sm:block">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Step 3: Dashboard</p>
            <p className="text-[10px] text-slate-500">Live AI crowd monitoring</p>
          </div>
        </div>
      </div>

      {/* Header Banner */}
      <div className="p-6 rounded-2xl cyber-glass border border-cyan-500/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono uppercase tracking-wider mb-1">
            <Radio className="w-4 h-4 animate-pulse" />
            <span>VIDEO SOURCE PROVISIONING</span>
          </div>
          <h1 className="text-xl md:text-2xl font-extrabold text-white tracking-tight">
            Configure Surveillance Cameras & Feeds
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Register your active surveillance video inputs. Connect directly to wireless network CCTV cameras via <strong>RTSP</strong>, or upload <strong>pre-recorded CCTV footage</strong> for YOLOv8 crowd analytics.
          </p>
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-300">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Active Event:</span>
            <span className="bg-cyan-950/80 px-2.5 py-0.5 rounded-lg border border-cyan-500/30 text-cyan-300 font-bold">
              {activeEvent?.title || 'Main Security Operation'}
            </span>
            <span className="text-slate-500">·</span>
            <span className="text-slate-400">{activeEvent?.venueName || 'Main Arena'}</span>
          </div>
        </div>

        {hasConfiguredSource && (
          <div className="flex flex-col items-end gap-2 flex-shrink-0">
            <span className="text-[11px] text-green-400 font-semibold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>{currentEventCameras.length} Source(s) Configured</span>
            </span>
            <button
              onClick={() => navigate('/dashboard')}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-extrabold text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-[0_0_16px_rgba(6,182,212,0.4)]"
            >
              <span>Launch Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Two Clearly Separated Options Selector */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Tab 1: Option A - RTSP */}
        <button
          type="button"
          onClick={() => setActiveTab('RTSP')}
          className={`p-5 rounded-2xl border text-left transition-all relative overflow-hidden select-none ${
            activeTab === 'RTSP'
              ? 'bg-slate-900 border-cyan-500/60 shadow-[0_0_20px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/40'
              : 'bg-slate-950/60 border-cyber-border/40 hover:border-slate-700 opacity-80 hover:opacity-100'
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-xl border ${
                activeTab === 'RTSP'
                  ? 'bg-cyan-950/80 border-cyan-500/40 text-cyan-400'
                  : 'bg-slate-900 border-slate-800 text-slate-400'
              }`}>
                <Radio className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest font-mono">OPTION A</span>
                <h3 className="text-base font-extrabold text-white">Connect CCTV Camera (RTSP)</h3>
              </div>
            </div>
            <span className={`w-5 h-5 rounded-full border flex items-center justify-center ${
              activeTab === 'RTSP' ? 'border-cyan-400 bg-cyan-500/20 text-cyan-400' : 'border-slate-700'
            }`}>
              {activeTab === 'RTSP' && <div className="w-2 h-2 rounded-full bg-cyan-400" />}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-3 leading-relaxed">
            Link a live wireless IP/network surveillance camera using an RTSP streaming URI. Supports standard H.264/H.265 streams.
          </p>
        </button>

        {/* Tab 2: Option B - Video Upload */}
        <button
          type="button"
          onClick={() => setActiveTab('UPLOAD')}
          className={`p-5 rounded-2xl border text-left transition-all relative overflow-hidden select-none ${
            activeTab === 'UPLOAD'
              ? 'bg-slate-900 border-cyan-500/60 shadow-[0_0_20px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/40'
              : 'bg-slate-950/60 border-cyber-border/40 hover:border-slate-700 opacity-80 hover:opacity-100'
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-xl border ${
                activeTab === 'UPLOAD'
                  ? 'bg-cyan-950/80 border-cyan-500/40 text-cyan-400'
                  : 'bg-slate-900 border-slate-800 text-slate-400'
              }`}>
                <Upload className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest font-mono">OPTION B</span>
                <h3 className="text-base font-extrabold text-white">Upload CCTV Video</h3>
              </div>
            </div>
            <span className={`w-5 h-5 rounded-full border flex items-center justify-center ${
              activeTab === 'UPLOAD' ? 'border-cyan-400 bg-cyan-500/20 text-cyan-400' : 'border-slate-700'
            }`}>
              {activeTab === 'UPLOAD' && <div className="w-2 h-2 rounded-full bg-cyan-400" />}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-3 leading-relaxed">
            Upload pre-recorded CCTV footage (.mp4, .avi, .mov, .mkv) for virtual camera inference, crowd counting, and heatmapping.
          </p>
        </button>
      </div>

      {/* Active Option Form Card */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="cyber-glass p-8 rounded-2xl border border-cyan-500/30 space-y-6"
      >
        {activeTab === 'RTSP' ? (
          /* OPTION A FORM: RTSP */
          <form onSubmit={handleRegisterRtsp} className="space-y-5 text-xs">
            <div className="border-b border-cyber-border/40 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Radio className="w-4 h-4 text-cyan-400" />
                  <span>Register Wireless / IP Camera (RTSP)</span>
                </h3>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  Stream processing will decode video frames and run real-time YOLOv8 person detection.
                </p>
              </div>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
                Protocol: RTSP / H.264
              </span>
            </div>

            {rtspFeedback && (
              <div className={`p-3.5 rounded-xl border text-xs font-medium flex items-center gap-2 ${
                rtspFeedback.type === 'success'
                  ? 'bg-green-950/60 border-green-500/40 text-green-200'
                  : 'bg-red-950/60 border-red-500/40 text-red-200'
              }`}>
                {rtspFeedback.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                )}
                <span>{rtspFeedback.msg}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                  Camera Identification Name <span className="text-cyan-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CAM-01 - North Turnstiles"
                  value={rtspName}
                  onChange={(e) => setRtspName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 transition-colors text-xs"
                />
              </div>

              <div className="space-y-1.5 md:col-span-2">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                  RTSP Stream URL <span className="text-cyan-400">*</span>
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Radio className="w-4 h-4" />
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="rtsp://admin:password@192.168.1.100:554/ch0"
                    value={rtspUrl}
                    onChange={(e) => setRtspUrl(e.target.value)}
                    className="w-full pl-10 pr-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 transition-colors text-xs font-mono"
                  />
                </div>
                <span className="text-[10px] text-slate-500">
                  Note: Sensitive credentials embedded in stream URLs are strictly masked and never exposed publicly.
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                  Physical Location
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <MapPin className="w-4 h-4" />
                  </span>
                  <input
                    type="text"
                    placeholder="e.g. North Gate Entry Concourse"
                    value={rtspLocation}
                    onChange={(e) => setRtspLocation(e.target.value)}
                    className="w-full pl-10 pr-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                  Field of View Capacity Threshold
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Users className="w-4 h-4" />
                  </span>
                  <input
                    type="number"
                    min="10"
                    max="10000"
                    value={rtspCapacity}
                    onChange={(e) => setRtspCapacity(Number(e.target.value))}
                    className="w-full pl-10 pr-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs font-mono"
                  />
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-cyber-border/40 flex items-center justify-between">
              <span className="text-[10px] text-slate-400">
                Camera will be bound to: <strong className="text-cyan-400">{activeEvent?.title}</strong>
              </span>

              <button
                type="submit"
                disabled={isSubmittingRtsp}
                className="px-6 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-[0_0_12px_rgba(6,182,212,0.25)] disabled:opacity-50"
              >
                <CameraIcon className="w-4 h-4" />
                <span>{isSubmittingRtsp ? 'Registering Camera...' : 'Register CCTV Camera'}</span>
              </button>
            </div>
          </form>
        ) : (
          /* OPTION B FORM: UPLOAD VIDEO */
          <form onSubmit={handleUploadVideo} className="space-y-5 text-xs">
            <div className="border-b border-cyber-border/40 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Upload className="w-4 h-4 text-cyan-400" />
                  <span>Upload CCTV Video File</span>
                </h3>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  Processed locally through the OpenCV & YOLOv8 detector pipeline as a virtual CCTV camera feed.
                </p>
              </div>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
                Formats: MP4, AVI, MOV, MKV
              </span>
            </div>

            {uploadFeedback && (
              <div className={`p-3.5 rounded-xl border text-xs font-medium flex items-center gap-2 ${
                uploadFeedback.type === 'success'
                  ? 'bg-green-950/60 border-green-500/40 text-green-200'
                  : 'bg-red-950/60 border-red-500/40 text-red-200'
              }`}>
                {uploadFeedback.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                )}
                <span>{uploadFeedback.msg}</span>
              </div>
            )}

            {/* Drag & Drop File Zone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className={`p-8 rounded-2xl border-2 border-dashed text-center cursor-pointer transition-all select-none ${
                selectedVideoFile
                  ? 'border-cyan-500/60 bg-cyan-950/30'
                  : 'border-slate-800 hover:border-cyan-500/40 bg-slate-950/50 hover:bg-slate-900/50'
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="video/mp4,video/avi,video/mov,video/mkv,.mp4,.avi,.mov,.mkv"
                className="hidden"
              />

              <div className="flex flex-col items-center justify-center space-y-2">
                <div className={`p-3.5 rounded-2xl border ${
                  selectedVideoFile
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                    : 'bg-slate-900 text-slate-400 border-slate-800'
                }`}>
                  <Film className="w-8 h-8" />
                </div>

                {selectedVideoFile ? (
                  <div className="space-y-1">
                    <p className="text-sm font-bold text-cyan-300">{selectedVideoFile.name}</p>
                    <p className="text-[10px] text-slate-400">
                      File Size: {(selectedVideoFile.size / (1024 * 1024)).toFixed(2)} MB · Click to change file
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-slate-200">
                      Click to choose video file or drag and drop here
                    </p>
                    <p className="text-[10px] text-slate-500">
                      Supports CCTV footage in MP4, AVI, MOV, or MKV formats
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                  Feed Display Name <span className="text-cyan-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CCTV Footage (Concourse)"
                  value={videoName}
                  onChange={(e) => setVideoName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 transition-colors text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                  Physical Location
                </label>
                <input
                  type="text"
                  placeholder="e.g. Main Hall Entry"
                  value={videoLocation}
                  onChange={(e) => setVideoLocation(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                  Zone Capacity Threshold
                </label>
                <input
                  type="number"
                  min="10"
                  max="10000"
                  value={videoCapacity}
                  onChange={(e) => setVideoCapacity(Number(e.target.value))}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs font-mono"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-cyber-border/40 flex items-center justify-between">
              <span className="text-[10px] text-slate-400">
                Uploaded footage will be bound to: <strong className="text-cyan-400">{activeEvent?.title}</strong>
              </span>

              <button
                type="submit"
                disabled={isUploadingVideo || !selectedVideoFile}
                className="px-6 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-[0_0_12px_rgba(6,182,212,0.25)] disabled:opacity-50"
              >
                <Upload className="w-4 h-4" />
                <span>{isUploadingVideo ? 'Uploading & Processing Video...' : 'Upload & Create Virtual Camera'}</span>
              </button>
            </div>
          </form>
        )}
      </motion.div>

      {/* Configured Sources for this Event Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-cyber-border/40 pb-2">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-white">
              Configured Sources for Active Operation ({currentEventCameras.length})
            </h2>
          </div>

          <button
            onClick={() => {
              if (selectedEventId) fetchCameras(selectedEventId);
            }}
            className="text-[11px] text-slate-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {currentEventCameras.length === 0 ? (
          <div className="p-8 rounded-2xl bg-slate-950/60 border border-dashed border-slate-800 text-center space-y-2">
            <CameraIcon className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs font-semibold text-slate-300">No cameras or video sources configured yet.</p>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
              Choose either <strong>Connect CCTV Camera (RTSP)</strong> or <strong>Upload Video</strong> above to establish surveillance feeds for this operation.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {currentEventCameras.map((cam) => {
              const isAnalyzing = cam.playbackStatus === 'analyzing' || cam.playbackStatus === 'playing';
              const isVideo = cam.sourceType === 'video';

              return (
                <div
                  key={cam.id}
                  className="p-4 rounded-xl cyber-glass border border-cyber-border/40 space-y-3 relative group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`p-2 rounded-lg border ${
                        isVideo 
                          ? 'bg-amber-950/40 border-amber-500/30 text-amber-400' 
                          : 'bg-cyan-950/40 border-cyan-500/30 text-cyan-400'
                      }`}>
                        {isVideo ? <Film className="w-4 h-4" /> : <Radio className="w-4 h-4" />}
                      </span>
                      <div className="min-w-0">
                        <h4 className="text-xs font-bold text-white truncate max-w-[170px]" title={cam.name}>
                          {cam.name}
                        </h4>
                        <span className="text-[10px] text-slate-400 block truncate">{cam.location}</span>
                      </div>
                    </div>

                    <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                      isAnalyzing
                        ? 'bg-green-950/60 border-green-500/40 text-green-300'
                        : 'bg-cyan-950/60 border-cyan-500/40 text-cyan-300'
                    }`}>
                      {isAnalyzing ? '● Analyzing' : 'Ready'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-400 border-t border-b border-cyber-border/20 py-2">
                    <div>
                      <span className="text-slate-500 block">TYPE:</span>
                      <strong className="text-slate-200 uppercase">{cam.sourceType}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">CAPACITY:</span>
                      <strong className="text-slate-200">{cam.capacity} max</strong>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    {!isAnalyzing ? (
                      <button
                        onClick={async () => {
                          await analyzeCamera(cam.id);
                          await fetchCameras(selectedEventId);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/40 text-cyan-300 font-bold text-[10px] flex items-center gap-1.5 transition-colors"
                      >
                        <Play className="w-3 h-3 text-cyan-400" />
                        <span>Start Analysis</span>
                      </button>
                    ) : (
                      <span className="text-[10px] text-green-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Inference Active</span>
                      </span>
                    )}

                    <button
                      onClick={async () => {
                        await removeCamera(cam.id);
                        await fetchCameras(selectedEventId);
                        await checkOnboardingStatus(selectedEventId);
                      }}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-950/20 transition-colors"
                      title="Remove camera"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Bottom Continue Action */}
        <div className="pt-6 border-t border-cyber-border/40 flex items-center justify-between">
          <p className="text-[11px] text-slate-400">
            {hasConfiguredSource
              ? 'Required camera/source setup is confirmed. You can now launch the real-time AI dashboard.'
              : 'Add at least one RTSP camera or uploaded video source above to proceed to dashboard monitoring.'}
          </p>

          <button
            onClick={() => navigate('/dashboard')}
            disabled={!hasConfiguredSource}
            className="px-8 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-extrabold text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.35)] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>Continue to Main Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
