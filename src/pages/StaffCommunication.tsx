import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { GlassCard } from '../components/GlassCard';
import { PersonnelDirectory } from '../components/PersonnelDirectory';
import { 
  Radio, 
  Send, 
  CheckCheck, 
  Mic, 
  Wifi, 
  WifiOff, 
  Battery, 
  Shield, 
  MessageSquare, 
  Zap, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Users, 
  Compass, 
  Video, 
  VideoOff, 
  ShieldCheck, 
  FileText, 
  RefreshCw 
} from 'lucide-react';

const GUIDANCE_PRESETS = [
  {
    title: 'Circulation Diversion',
    text: 'Crowd density building at central access. Direct arriving attendees toward the designated auxiliary open circulation corridor.'
  },
  {
    title: 'Turnstile Congestion',
    text: 'High ingress rate observed at entrance gate turnstiles. Request ground staff to monitor throughput and manage queuing lanes.'
  },
  {
    title: 'Corridor Pace Verification',
    text: 'Please verify pedestrian pace and physical clearance along the designated corridor. Report any bottlenecks immediately.'
  },
  {
    title: 'Emergency Exit Clearance',
    text: 'Ensure all emergency exit doors, push-bars, and egress pathways in this sector remain completely unobstructed.'
  },
  {
    title: 'Local Crowd Density Check',
    text: 'Request local manual crowd-density assessment and verification of gate capacity limits.'
  }
];

export const StaffCommunication: React.FC = () => {
  const { 
    guards, 
    instructionLogs, 
    sendInstruction, 
    recommendations,
    events,
    selectedEventId,
    cameras,
    user,
    coordinationMessages,
    sendCoordinationMessage,
    acknowledgeCoordinationMessage,
    refreshCoordinationMessages
  } = useCrowdSystem();

  // Active Tab: 'coordination' | 'directory' | 'dispatch'
  const [activeTab, setActiveTab] = useState<'coordination' | 'directory' | 'dispatch'>('coordination');

  // Active Event Context
  const currentEvent = events.find(e => e.id === selectedEventId) || events[0];

  // Event Scoped Cameras
  const eventCameras = useMemo(() => {
    return cameras.filter(c => !selectedEventId || c.eventId === selectedEventId);
  }, [cameras, selectedEventId]);

  const [selectedCamId, setSelectedCamId] = useState<string>('');
  const [streamError, setStreamError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (eventCameras.length > 0 && (!selectedCamId || !eventCameras.some(c => c.id === selectedCamId))) {
      setSelectedCamId(eventCameras[0].id);
      setStreamError(false);
    }
  }, [eventCameras, selectedCamId]);

  const activeCam = useMemo(() => {
    return eventCameras.find(c => c.id === selectedCamId) || eventCameras[0] || null;
  }, [eventCameras, selectedCamId]);

  // Coordination Guidance Composer State
  const [selectedRecipientId, setSelectedRecipientId] = useState<string>('all');
  const [coordinationZone, setCoordinationZone] = useState<string>('North Main Gate');
  const [coordinationPriority, setCoordinationPriority] = useState<'normal' | 'high' | 'critical'>('normal');
  const [coordinationText, setCoordinationText] = useState<string>('');
  const [coordinationStatus, setCoordinationStatus] = useState<'Internally Sent' | 'Draft' | 'Queued'>('Internally Sent');
  const [isSubmittingCoordination, setIsSubmittingCoordination] = useState(false);
  const [coordinationError, setCoordinationError] = useState<string | null>(null);
  const [coordinationSuccessMsg, setCoordinationSuccessMsg] = useState<string | null>(null);
  const [coordinationHistoryFilter, setCoordinationHistoryFilter] = useState('all');

  // Auto-sync zone when camera selection changes
  useEffect(() => {
    if (activeCam) {
      const defaultZone = activeCam.location || activeCam.name || 'Main Zone';
      setCoordinationZone(defaultZone);
    }
  }, [activeCam]);

  // Dispatch / Audio State (Preserved)
  const [targetType, setTargetType] = useState<'individual' | 'group' | 'emergency'>('individual');
  const [selectedGuardId, setSelectedGuardId] = useState<string>(guards[0]?.id || '');
  const [priority, setPriority] = useState<'normal' | 'urgent' | 'emergency'>('normal');
  const [instructionText, setInstructionText] = useState('');
  const [isBroadcastingVoice, setIsBroadcastingVoice] = useState(false);

  // Filtered Guards (Event Scoped for Ground Coordination & Dispatch)
  const filteredGuards = useMemo(() => {
    return guards.filter(guard => {
      if (selectedEventId && guard.eventId && guard.eventId !== selectedEventId) {
        return false;
      }
      return true;
    });
  }, [guards, selectedEventId]);

  // Scoped Coordination Messages for History
  const filteredCoordinationMessages = useMemo(() => {
    return coordinationMessages.filter(msg => {
      if (selectedEventId && msg.eventId && msg.eventId !== selectedEventId) {
        return false;
      }
      if (coordinationHistoryFilter !== 'all' && msg.status !== coordinationHistoryFilter) {
        return false;
      }
      return true;
    });
  }, [coordinationMessages, selectedEventId, coordinationHistoryFilter]);

  const maskPhone = (phone: string) => {
    if (!phone || phone.length < 6) return '*******';
    return phone.slice(0, 3) + '••••••' + phone.slice(-3);
  };

  // Submit Officer Coordination Guidance Message
  const handleSendCoordination = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!coordinationText.trim()) {
      setCoordinationError('Please enter a guidance message.');
      return;
    }
    if (!coordinationZone.trim()) {
      setCoordinationError('Please specify the venue zone, gate, or corridor.');
      return;
    }
    if (isSubmittingCoordination) return;

    setCoordinationError(null);
    setIsSubmittingCoordination(true);

    const clientMutationId = `mut-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    
    let targetRecipientName = 'All Ground Staff (Internal Broadcast)';
    let targetRecipientRole = 'Broadcast';
    let targetRecipientId: string | undefined = undefined;

    if (selectedRecipientId && selectedRecipientId !== 'all') {
      const g = filteredGuards.find(guard => guard.id === selectedRecipientId);
      if (g) {
        targetRecipientName = g.name;
        targetRecipientRole = g.role || 'Security Guard';
        targetRecipientId = g.id;
      }
    }

    try {
      await sendCoordinationMessage({
        event_id: selectedEventId || (currentEvent ? currentEvent.id : 'global-event'),
        zone: coordinationZone.trim(),
        recipient: targetRecipientName,
        recipient_id: targetRecipientId,
        recipient_role: targetRecipientRole,
        camera_id: activeCam ? activeCam.id : undefined,
        priority: coordinationPriority,
        text: coordinationText.trim(),
        status: coordinationStatus,
        client_mutation_id: clientMutationId
      });
      setCoordinationText('');
      setCoordinationSuccessMsg(`Guidance directive sent to internal coordination system for ${targetRecipientName}.`);
      setTimeout(() => setCoordinationSuccessMsg(null), 4000);
    } catch (err: any) {
      setCoordinationError(err.message || 'Failed to record guidance directive.');
    } finally {
      setIsSubmittingCoordination(false);
    }
  };

  // Acknowledge Guidance Message
  const handleAcknowledge = async (msgId: string) => {
    try {
      await acknowledgeCoordinationMessage(msgId);
    } catch (err: any) {
      console.error('Failed to acknowledge coordination message:', err);
    }
  };

  // Existing Dispatch Handlers (Preserved)
  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!instructionText.trim()) return;

    let recipientName = 'All Security Staff (Broadcast)';
    if (targetType === 'individual') {
      const target = guards.find(g => g.id === selectedGuardId);
      recipientName = target ? `${target.name} (${target.zone})` : 'Individual Guard';
    } else if (targetType === 'group') {
      recipientName = 'On-Duty Rapid Response Squad';
    } else if (targetType === 'emergency') {
      recipientName = 'ALL SECURITY UNITS (EMERGENCY BROADCAST)';
    }

    sendInstruction({
      recipient: recipientName,
      type: targetType,
      priority,
      text: instructionText
    });

    setInstructionText('');
  };

  const useAiSuggestion = (recText: string) => {
    setInstructionText(`AI DIRECTIVE: ${recText}`);
  };

  return (
    <div className="space-y-6 pb-12 font-mono">
      {/* Top Header & Context */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs mb-1">
            <Shield className="w-4 h-4" />
            <span>SECURITY COMMAND · GROUND TEAM COORDINATION</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <span>Officer-to-Ground Coordination Workspace</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-3xl">
            Review live CCTV feeds and crowd metrics, formulate circulation directives, and coordinate with stationed ground security guards and event coordinators for active event:{' '}
            <span className="text-cyan-400 font-bold">{currentEvent ? currentEvent.title : 'Global Operations'}</span>.
          </p>
        </div>

        {/* Tab Switcher & Quick Add Action */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-slate-950 p-1 rounded-xl border border-cyber-border text-xs">
            <button
              onClick={() => setActiveTab('coordination')}
              className={`px-4 py-2 rounded-lg font-bold uppercase tracking-wider flex items-center gap-2 transition-all ${
                activeTab === 'coordination'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Ground Coordination</span>
            </button>
            <button
              onClick={() => setActiveTab('directory')}
              className={`px-4 py-2 rounded-lg font-bold uppercase tracking-wider flex items-center gap-2 transition-all ${
                activeTab === 'directory'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>Personnel Directory ({filteredGuards.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('dispatch')}
              className={`px-4 py-2 rounded-lg font-bold uppercase tracking-wider flex items-center gap-2 transition-all ${
                activeTab === 'dispatch'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              <span>Broadcast & Audio</span>
            </button>
          </div>



          {activeTab === 'coordination' && (
            <div className="px-3 py-2 rounded-xl bg-slate-950 border border-cyber-border flex items-center gap-2 text-xs">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-[10px] uppercase font-bold text-cyan-400">Officer:</span>
              <span className="text-white font-bold">{user?.name || user?.email || 'Command Officer'}</span>
            </div>
          )}
        </div>
      </div>

      {/* TAB 1: OFFICER-TO-GROUND-TEAM COORDINATION WORKSPACE */}
      {activeTab === 'coordination' && (
        <div className="space-y-6 animate-fade-in">
          {/* Operational Banner */}
          <div className="p-3.5 rounded-xl bg-cyan-950/40 border border-cyan-500/30 text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 text-cyan-200">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0" />
              <span>
                <strong>INTERNAL COORDINATION GATEWAY:</strong> Directives recorded here route through the surveillance command center. External SMS/Satellite transport is planned for future carrier integrations.
              </span>
            </div>
            <div className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest shrink-0">
              CHANNEL: INTERNAL-SECURE-V2.4
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* 1. Left Side: CCTV Live Review & Telemetry (Col 7) */}
            <div className="lg:col-span-7 space-y-6">
              <GlassCard className="p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Video className="w-4 h-4 text-cyan-400" />
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                      CCTV Live Observation & Telemetry
                    </h3>
                  </div>

                  {/* Camera Selector */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase text-slate-400 font-bold">Camera:</span>
                    <select
                      value={selectedCamId}
                      onChange={(e) => {
                        setSelectedCamId(e.target.value);
                        setStreamError(false);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-slate-950 border border-cyber-border text-xs text-white focus:outline-none focus:border-cyan-500"
                    >
                      {eventCameras.length > 0 ? (
                        eventCameras.map(cam => (
                          <option key={cam.id} value={cam.id}>
                            {cam.name} · {cam.location}
                          </option>
                        ))
                      ) : (
                        <option value="">No cameras registered</option>
                      )}
                    </select>
                  </div>
                </div>

                {/* CCTV Stream Container */}
                <div className="relative aspect-video rounded-xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center">
                  {activeCam ? (
                    streamError ? (
                      <div className="p-6 text-center space-y-3">
                        <VideoOff className="w-8 h-8 text-amber-500 mx-auto" />
                        <p className="text-xs font-bold text-slate-300">Live Stream Offline or Processing</p>
                        <button
                          type="button"
                          onClick={() => setStreamError(false)}
                          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-400 text-xs font-bold"
                        >
                          Retry Stream
                        </button>
                      </div>
                    ) : (
                      <img
                        ref={imgRef}
                        src={`http://localhost:8000/api/cameras/${activeCam.id}/stream`}
                        alt={activeCam.name}
                        onError={() => setStreamError(true)}
                        className="w-full h-full object-contain"
                      />
                    )
                  ) : (
                    <div className="text-center p-8 space-y-2">
                      <VideoOff className="w-8 h-8 text-slate-600 mx-auto" />
                      <p className="text-xs text-slate-400">No active CCTV cameras found for {currentEvent?.title || 'this event'}.</p>
                    </div>
                  )}

                  {/* Real-Time Telemetry HUD Overlay */}
                  {activeCam && (
                    <div className="absolute top-3 left-3 bg-slate-950/85 backdrop-blur-md p-3 rounded-lg border border-slate-800 text-[10px] space-y-1 text-white shadow-xl pointer-events-none">
                      <div className="flex items-center justify-between gap-4 border-b border-slate-800 pb-1">
                        <span className="font-bold text-cyan-400 uppercase tracking-wider">{activeCam.name}</span>
                        <span className="text-slate-400">{activeCam.location}</span>
                      </div>
                      <div className="flex items-center gap-3 pt-0.5">
                        <span>Count: <strong className="text-white font-mono text-xs">{activeCam.count}</strong></span>
                        <span>Density: <strong className="text-cyan-300 font-mono text-xs">{(activeCam.density || 0).toFixed(1)}%</strong></span>
                        <span>
                          Risk:{' '}
                          <strong className={
                            activeCam.risk === 'high' || activeCam.risk === 'critical' ? 'text-red-400 font-bold' :
                            activeCam.risk === 'medium' ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'
                          }>
                            {activeCam.risk ? activeCam.risk.toUpperCase() : 'LOW'}
                          </strong>
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Manual Assessment Notice */}
                  <div className="absolute bottom-2 right-2 bg-slate-950/90 backdrop-blur-sm px-2.5 py-1 rounded text-[9px] text-slate-400 border border-slate-800 pointer-events-none">
                    Officer Review Mode · AI Detection Verified
                  </div>
                </div>
              </GlassCard>

              {/* Guidance Message Composer */}
              <GlassCard className="p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-cyan-400" />
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                      Ground Team Guidance Composer
                    </h3>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">Internal Operational Directive</span>
                </div>

                {coordinationError && (
                  <div className="p-3 rounded-xl bg-red-950/80 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{coordinationError}</span>
                  </div>
                )}

                {coordinationSuccessMsg && (
                  <div className="p-3 rounded-xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>{coordinationSuccessMsg}</span>
                  </div>
                )}

                <form onSubmit={handleSendCoordination} className="space-y-4 text-xs">
                  {/* Recipient & Zone Selection */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[10px] uppercase font-bold text-slate-400 block">
                        Assigned Ground Recipient *
                      </label>
                      <select
                        value={selectedRecipientId}
                        onChange={(e) => {
                          setSelectedRecipientId(e.target.value);
                          if (e.target.value !== 'all') {
                            const g = filteredGuards.find(guard => guard.id === e.target.value);
                            if (g && g.zone) setCoordinationZone(g.zone);
                          }
                        }}
                        className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none focus:border-cyan-500"
                      >
                        <option value="all">Broadcast: All Ground Personnel</option>
                        {filteredGuards.map(g => (
                          <option key={g.id} value={g.id}>
                            {g.name} · {g.role || 'Security'} ({g.zone}) [{g.dutyStatus || 'On Duty'}]
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] uppercase font-bold text-slate-400 block">
                        Target Venue Zone / Sector *
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Turnstile Gate A / Passage 2"
                        value={coordinationZone}
                        onChange={(e) => setCoordinationZone(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  </div>

                  {/* Priority & Lifecycle Initial State */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[10px] uppercase font-bold text-slate-400 block">Directive Priority</label>
                      <div className="flex gap-2">
                        {[
                          { id: 'normal', label: 'Normal', color: 'border-blue-500/30 text-blue-400 bg-blue-950/30' },
                          { id: 'high', label: 'High', color: 'border-amber-500/30 text-amber-400 bg-amber-950/30' },
                          { id: 'critical', label: 'Critical', color: 'border-red-500/40 text-red-400 bg-red-950/40' }
                        ].map(p => (
                          <button
                            key={p.id}
                            type="button"
                            onClick={() => setCoordinationPriority(p.id as any)}
                            className={`flex-1 py-1.5 px-2 rounded-lg text-[10px] font-bold uppercase tracking-wider border transition-all ${
                              coordinationPriority === p.id ? `${p.color} ring-1 ring-cyan-400` : 'bg-slate-950 border-slate-800 text-slate-500'
                            }`}
                          >
                            {p.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] uppercase font-bold text-slate-400 block">Submission Lifecycle State</label>
                      <select
                        value={coordinationStatus}
                        onChange={(e) => setCoordinationStatus(e.target.value as any)}
                        className="w-full px-3 py-1.5 rounded-xl bg-slate-950 border border-cyber-border text-xs text-white focus:outline-none focus:border-cyan-500"
                      >
                        <option value="Internally Sent">Internally Sent (Command Center Active)</option>
                        <option value="Queued">Queued (Ready to Dispatch)</option>
                        <option value="Draft">Draft (Save Without Sending)</option>
                      </select>
                    </div>
                  </div>

                  {/* Operational Presets / Shortcuts */}
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block flex items-center gap-1">
                      <FileText className="w-3 h-3 text-cyan-400" /> Guidance Templates & Circulation Presets:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {GUIDANCE_PRESETS.map((preset, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setCoordinationText(preset.text)}
                          className="text-[10px] px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/30 transition-colors text-left"
                        >
                          + {preset.title}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Guidance Message Textarea */}
                  <div className="space-y-1">
                    <label className="text-[10px] uppercase font-bold text-slate-400 block">
                      Operational Guidance Message *
                    </label>
                    <textarea
                      rows={3}
                      required
                      placeholder="e.g. Turnstiles at Gate A experiencing heavy arrival burst. Redirect incoming flow along auxiliary walkway B..."
                      value={coordinationText}
                      onChange={(e) => setCoordinationText(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none focus:border-cyan-500/50 text-xs leading-relaxed"
                    />
                  </div>

                  {/* Action Button */}
                  <button
                    type="submit"
                    disabled={isSubmittingCoordination || !coordinationText.trim()}
                    className="w-full py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(6,182,212,0.2)] disabled:opacity-50"
                  >
                    {isSubmittingCoordination ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Recording Guidance Directive...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4 fill-white" />
                        <span>Record & Dispatch Internal Guidance</span>
                      </>
                    )}
                  </button>
                </form>
              </GlassCard>
            </div>

            {/* 2. Right Side: Coordination History & Audit Lifecycle (Col 5) */}
            <div className="lg:col-span-5 space-y-6">
              {/* Recipient Context Panel */}
              <GlassCard className="p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <Shield className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Ground Personnel Context</span>
                  </h4>
                  <span className="text-[10px] text-slate-400">
                    {filteredGuards.filter(g => (g.dutyStatus || 'On Duty') === 'On Duty').length} On Duty
                  </span>
                </div>

                {selectedRecipientId !== 'all' ? (
                  (() => {
                    const target = filteredGuards.find(g => g.id === selectedRecipientId);
                    if (!target) return null;
                    return (
                      <div className="flex items-center justify-between gap-3 text-xs p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
                        <div className="min-w-0 space-y-0.5">
                          <p className="font-bold text-white truncate">{target.name}</p>
                          <p className="text-[10px] text-cyan-400 truncate">{target.role || 'Security'} · Zone: {target.zone}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
                            target.dutyStatus === 'On Duty' ? 'bg-emerald-950 text-emerald-400 border-emerald-500/30' : 'bg-slate-900 text-slate-400 border-slate-800'
                          }`}>
                            {target.dutyStatus || 'On Duty'}
                          </span>
                          <p className="text-[9px] text-slate-500 font-mono mt-1">{maskPhone(target.phone)}</p>
                        </div>
                      </div>
                    );
                  })()
                ) : (
                  <div className="p-3 text-center rounded-xl bg-slate-950/40 border border-slate-900 text-slate-400 text-xs">
                    Target: Broadcast to all personnel assigned to <strong>{currentEvent?.title || 'active event'}</strong>.
                  </div>
                )}
              </GlassCard>

              {/* Coordination Audit History */}
              <GlassCard className="p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-cyan-400" />
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                      Guidance History & Audit Trail
                    </h3>
                  </div>

                  {/* Status Filter for History & Refresh */}
                  <div className="flex items-center gap-2">
                    <select
                      value={coordinationHistoryFilter}
                      onChange={(e) => setCoordinationHistoryFilter(e.target.value)}
                      className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500"
                    >
                      <option value="all">All Statuses ({filteredCoordinationMessages.length})</option>
                      <option value="Internally Sent">Internally Sent</option>
                      <option value="Acknowledged">Acknowledged</option>
                      <option value="Queued">Queued</option>
                      <option value="Draft">Draft</option>
                      <option value="Failed">Failed</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => refreshCoordinationMessages()}
                      title="Refresh guidance messages from server"
                      className="p-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-cyan-400 transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {filteredCoordinationMessages.length > 0 ? (
                  <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                    {filteredCoordinationMessages.map((msg) => {
                      const isAck = msg.status === 'Acknowledged';
                      const isFailed = msg.status === 'Failed';
                      const isSent = msg.status === 'Internally Sent';
                      const isQueued = msg.status === 'Queued';

                      return (
                        <div
                          key={msg.id}
                          className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs space-y-2 hover:border-cyan-500/30 transition-colors"
                        >
                          {/* Header: Author, Time, Recipient */}
                          <div className="flex items-start justify-between gap-2 text-[10px]">
                            <div className="space-y-0.5">
                              <span className="font-bold text-cyan-300">
                                BY: {msg.officerName || 'Command Officer'} ➔ TO: {msg.recipient}
                              </span>
                              <p className="text-slate-500 font-mono">
                                {msg.timestamp} · Zone: <span className="text-slate-300">{msg.zone || 'General'}</span>
                              </p>
                            </div>

                            {/* Priority Badge */}
                            <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border shrink-0 ${
                              msg.priority === 'critical' ? 'bg-red-950/80 border-red-500/30 text-red-400' :
                              msg.priority === 'high' ? 'bg-amber-950/80 border-amber-500/30 text-amber-400' :
                              'bg-blue-950/80 border-blue-500/30 text-blue-400'
                            }`}>
                              {msg.priority}
                            </span>
                          </div>

                          {/* Directive Content */}
                          <p className="text-slate-200 leading-relaxed font-sans text-xs bg-slate-900/50 p-2.5 rounded-lg border border-slate-800/80">
                            "{msg.text}"
                          </p>

                          {/* Footer: Lifecycle Status & Acknowledgement */}
                          <div className="flex items-center justify-between pt-1 text-[10px]">
                            <div className="flex items-center gap-1.5">
                              <span className={`px-2 py-0.5 rounded font-bold uppercase text-[9px] border flex items-center gap-1 ${
                                isAck ? 'bg-emerald-950/80 border-emerald-500/30 text-emerald-400' :
                                isSent ? 'bg-cyan-950/80 border-cyan-500/30 text-cyan-300' :
                                isQueued ? 'bg-indigo-950/80 border-indigo-500/30 text-indigo-300' :
                                isFailed ? 'bg-red-950/80 border-red-500/30 text-red-400' :
                                'bg-slate-900 border-slate-800 text-slate-400'
                              }`}>
                                {isAck && <CheckCheck className="w-3 h-3" />}
                                {msg.status}
                              </span>

                              {msg.acknowledgedAt && (
                                <span className="text-slate-400 font-mono text-[9px]">
                                  (Ack @ {msg.acknowledgedAt.split(' ')[1] || msg.acknowledgedAt})
                                </span>
                              )}
                            </div>

                            {/* Action to Acknowledge */}
                            {!isAck && (
                              <button
                                type="button"
                                onClick={() => handleAcknowledge(msg.id)}
                                className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-emerald-400 font-bold text-[9px] uppercase tracking-wider flex items-center gap-1 transition-colors"
                              >
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Acknowledge</span>
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-8 text-center bg-slate-950/40 rounded-xl border border-slate-900 text-slate-500 text-xs">
                    No guidance directives recorded for this event yet. Use the composer to transmit operational instructions.
                  </div>
                )}
              </GlassCard>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SECURITY PERSONNEL & EVENT COORDINATOR DIRECTORY */}
      {activeTab === 'directory' && (
        <div className="animate-fade-in">
          <PersonnelDirectory />
        </div>
      )}

      {/* TAB 3: LIVE BROADCAST & AUDIO CONSOLE (Preserved Functionality) */}
      {activeTab === 'dispatch' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-in">
          {/* Left: Dispatch Console (Col 7) */}
          <div className="lg:col-span-7 space-y-6">
            <GlassCard className="p-6 space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-cyan-400" />
                  <span>Instruction Transmission Console</span>
                </h3>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setIsBroadcastingVoice(!isBroadcastingVoice)}
                    className={`px-3 py-1.5 rounded-lg font-bold text-[10px] uppercase tracking-wider transition-all flex items-center gap-1.5 border ${
                      isBroadcastingVoice 
                        ? 'bg-red-600 border-red-500 text-white animate-pulse' 
                        : 'bg-slate-900 border-slate-800 text-slate-300 hover:text-white'
                    }`}
                  >
                    <Mic className="w-3 h-3 text-cyan-400" />
                    <span>{isBroadcastingVoice ? 'Live Audio Active' : 'Hold to Speak'}</span>
                  </button>
                  <span className="text-[10px] text-slate-500">Secure Channel Relay</span>
                </div>
              </div>

              <form onSubmit={handleSend} className="space-y-4 text-xs">
                {/* Broadcast Target Type */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Broadcast Mode</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'individual', label: 'Individual Staff' },
                      { id: 'group', label: 'Zone Group' },
                      { id: 'emergency', label: 'Emergency All' }
                    ].map(mode => (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() => setTargetType(mode.id as any)}
                        className={`py-2 px-3 rounded-xl font-bold uppercase tracking-wider border transition-all text-[10px] ${
                          targetType === mode.id
                            ? mode.id === 'emergency' 
                              ? 'bg-red-950/80 border-red-500 text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)]'
                              : 'bg-cyan-950/60 border-cyan-500 text-cyan-400'
                            : 'bg-slate-950 border-slate-900 text-slate-400 hover:text-white'
                        }`}
                      >
                        {mode.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Recipient Selection */}
                {targetType === 'individual' && guards.length > 0 && (
                  <div className="space-y-1 animate-fade-in">
                    <label className="text-[10px] font-bold uppercase text-slate-400 block">Target Security Officer</label>
                    <select
                      value={selectedGuardId}
                      onChange={(e) => setSelectedGuardId(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none focus:border-cyan-500/40"
                    >
                      {guards.map(g => (
                        <option key={g.id} value={g.id}>
                          {g.name} — {g.role || 'Guard'} (Zone: {g.zone})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Priority Level */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Priority Level</label>
                  <div className="flex gap-3">
                    {[
                      { id: 'normal', label: 'Normal', color: 'border-blue-500/30 text-blue-400' },
                      { id: 'urgent', label: 'Urgent', color: 'border-orange-500/30 text-orange-400' },
                      { id: 'emergency', label: 'CRITICAL EMERGENCY', color: 'border-red-500 text-red-400 font-extrabold' }
                    ].map(p => (
                      <label key={p.id} className="flex items-center gap-2 cursor-pointer text-slate-300">
                        <input 
                          type="radio" 
                          name="priority" 
                          value={p.id} 
                          checked={priority === p.id} 
                          onChange={() => setPriority(p.id as any)}
                          className="accent-cyan-500"
                        />
                        <span className={`text-[11px] px-2 py-0.5 rounded border ${p.color}`}>{p.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Instruction Textarea */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 block">Instruction Details</label>
                  <textarea
                    rows={3}
                    required
                    placeholder="e.g. Direct attendees toward designated open circulation route in Corridor B..."
                    value={instructionText}
                    onChange={(e) => setInstructionText(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none focus:border-cyan-500/40 text-xs leading-relaxed"
                  />
                </div>

                {/* AI Suggestions */}
                {recommendations.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block flex items-center gap-1">
                      <Zap className="w-3 h-3 text-cyan-400" /> AI Directives Quick Shortcut:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {recommendations.slice(0, 3).map(rec => (
                        <button
                          key={rec.id}
                          type="button"
                          onClick={() => useAiSuggestion(rec.title)}
                          className="text-[10px] px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/30 transition-colors text-left"
                        >
                          + {rec.title}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
                >
                  <Send className="w-4 h-4 fill-white" /> Transmit Instruction to Ground Team
                </button>
              </form>
            </GlassCard>

            {/* Transmission History Logs */}
            <GlassCard className="p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-400" />
                  <span>Instruction Transmission Logs</span>
                </h3>
                <span className="text-[10px] text-slate-500">{instructionLogs.length} Messages Recorded</span>
              </div>

              <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                {instructionLogs.map((log) => (
                  <div key={log.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 text-xs space-y-1">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-slate-400 font-bold">{log.timestamp} · TO: {log.recipient}</span>
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.2 rounded font-bold uppercase ${log.priority === 'emergency' ? 'bg-red-950 text-red-400 border border-red-500/20' : 'bg-slate-900 text-slate-400'}`}>
                          {log.priority}
                        </span>
                        <span className="text-green-400 flex items-center gap-0.5">
                          <CheckCheck className="w-3.5 h-3.5" /> {log.deliveryStatus}
                        </span>
                      </div>
                    </div>
                    <p className="text-slate-300 leading-normal">"{log.text}"</p>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>

          {/* Right: Security Staff Roster (Col 5) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Shield className="w-4 h-4 text-cyan-400" />
                <span>Stationed Personnel Status ({filteredGuards.length})</span>
              </h3>
            </div>

            <div className="space-y-3">
              {filteredGuards.length > 0 ? (
                filteredGuards.map((guard) => (
                  <GlassCard key={guard.id} className="p-4 flex items-center justify-between gap-4">
                    <div className="min-w-0 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full shrink-0 ${guard.isOnline ? 'bg-green-400' : 'bg-slate-600'}`} />
                        <h4 className="font-bold text-xs text-white truncate">{guard.name}</h4>
                      </div>
                      <p className="text-[10px] text-cyan-400 pl-4">{guard.role || 'Guard'} · Zone: {guard.zone}</p>
                      <p className="text-[9px] text-slate-500 truncate pl-4">{maskPhone(guard.phone)}</p>
                    </div>

                    <div className="flex flex-col items-end gap-1 text-[10px]">
                      <div className="flex items-center gap-1.5">
                        {guard.isOnline ? (
                          <span className="text-green-400 flex items-center gap-0.5"><Wifi className="w-3 h-3" /> Online</span>
                        ) : (
                          <span className="text-slate-500 flex items-center gap-0.5"><WifiOff className="w-3 h-3" /> Offline</span>
                        )}
                        <span className="text-slate-400 flex items-center gap-0.5">
                          <Battery className="w-3 h-3" /> {guard.battery}%
                        </span>
                      </div>

                      <span className={`px-2 py-0.5 rounded font-bold uppercase text-[9px] border ${
                        guard.status === 'dispatched' ? 'bg-red-950/60 border-red-500/20 text-red-400 animate-pulse' :
                        guard.status === 'alerted' ? 'bg-orange-950/60 border-orange-500/20 text-orange-400' :
                        'bg-slate-900 border-slate-800 text-slate-400'
                      }`}>
                        {guard.status}
                      </span>
                    </div>
                  </GlassCard>
                ))
              ) : (
                <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-900 text-slate-500 text-xs">
                  No security personnel connected for this event. Switch to the Personnel Directory tab to register ground personnel.
                </div>
              )}
            </div>
          </div>
        </div>
      )}


    </div>
  );
};
