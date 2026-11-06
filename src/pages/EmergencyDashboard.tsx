import React, { useState } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { 
  ShieldAlert, 
  Flame, 
  Users, 
  Activity, 
  Clock,
  Radio,
  Ambulance,
  Shield,
  Siren,
  CheckCheck,
  CheckCircle,
  Building,
  UserCheck,
  AlertTriangle,
  X,
  Send,
  Loader2
} from 'lucide-react';
import { GlassCard } from '../components/GlassCard';

export const EmergencyDashboard: React.FC = () => {
  const { 
    activeEmergencyEvent, 
    activeEmergencyDispatches, 
    updateEmergencyEventStatus, 
    approveEmergencyDispatch,
    dispatchEmergencyService,
    triggerEmergency, 
    cameras, 
    activeCameraId 
  } = useCrowdSystem();

  const activeCam = cameras.find(c => c.id === (activeEmergencyEvent?.camera_id || activeCameraId)) || cameras[0];
  const camName = activeEmergencyEvent ? activeCam?.name : (activeCam?.name || 'Uploaded CCTV Video');
  const camLocation = activeEmergencyEvent ? activeEmergencyEvent.location : (activeCam?.location || 'Uploaded Video Source');

  const [simulating, setSimulating] = useState(false);

  // Dispatch Confirmation Modal State
  const [dispatchModal, setDispatchModal] = useState<{
    isOpen: boolean;
    serviceType: string;
    serviceLabel: string;
  } | null>(null);
  const [selectedStation, setSelectedStation] = useState('');
  const [dispatchNotes, setDispatchNotes] = useState('');
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchOutcome, setDispatchOutcome] = useState<{ success: boolean; message: string; data?: any } | null>(null);

  const handleOpenDispatchDialog = (serviceType: string, serviceLabel: string) => {
    let defaultStation = 'On-Site Rapid Response Team';
    if (serviceType === 'medical') defaultStation = 'Station 4 - City General EMS Unit (Nearest)';
    else if (serviceType === 'fire') defaultStation = 'Engine Company 12 - Metro Fire Command (Nearest)';
    else if (serviceType === 'police') defaultStation = 'Precinct 3 - Rapid Tactical Unit';
    else if (serviceType === 'security') defaultStation = 'Security Squad Charlie - Gate & Concourse Patrol';

    setSelectedStation(defaultStation);
    setDispatchNotes(`Precautionary rapid deployment to ${camLocation}.`);
    setDispatchOutcome(null);
    setDispatchModal({
      isOpen: true,
      serviceType,
      serviceLabel
    });
  };

  const handleConfirmDispatch = async () => {
    if (!dispatchModal) return;
    setIsDispatching(true);
    setDispatchOutcome(null);
    try {
      const res = await dispatchEmergencyService(
        dispatchModal.serviceType,
        selectedStation,
        dispatchNotes
      );
      setDispatchOutcome({
        success: true,
        message: res.message || `${dispatchModal.serviceLabel} dispatch transmitted and recorded in system audit logs.`,
        data: res
      });
    } catch (err: any) {
      setDispatchOutcome({
        success: false,
        message: err.message || 'Dispatch transmission failed. Please verify system connection and retry.'
      });
    } finally {
      setIsDispatching(false);
    }
  };

  const handleSimulate = async (type: string) => {
    setSimulating(true);
    await triggerEmergency(
      `[TEST / SIMULATION ONLY] ${type}`,
      camLocation,
      `[TEST / SIMULATION ONLY] Operator initiated manual panic simulation override for ${camLocation}.`
    );
    setTimeout(() => setSimulating(false), 500);
  };

  const getServiceDispatch = (stype: string) => {
    return activeEmergencyDispatches.find(d => d.service_type === stype);
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-2 border-b border-cyber-border/40">
        <div>
          <h2 className="text-base font-extrabold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Siren className="w-5 h-5 text-red-500 animate-pulse" />
            <span>AI Emergency Response & Dispatch Command Console</span>
          </h2>
          <p className="text-[10px] text-slate-500">
            Real-time emergency events derived exclusively from YOLO AI video analytics stored in MySQL <code className="text-cyan-400">emergency_events</code> table.
          </p>
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Active Crisis Monitor Console (Col 7) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Active Crisis Monitor Console
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">Real-Time AI Telemetry</span>
          </div>

          {activeEmergencyEvent ? (
            /* PROMINENT EMERGENCY CARD */
            <div className="cyber-glass-red p-6 rounded-xl border-2 border-red-500/60 shadow-[0_0_30px_rgba(239,68,68,0.2)] space-y-5">
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 bg-red-950 border border-red-500/50 text-red-400 font-extrabold text-[10px] px-3 py-1 rounded-full w-max animate-pulse">
                    <Clock className="w-3 h-3 text-red-400" /> DETECTED: {activeEmergencyEvent.detected_at}
                  </div>
                  <h4 className="text-xl font-extrabold text-white tracking-tight leading-snug flex items-center gap-2">
                    <span>🚨 CRITICAL EMERGENCY</span>
                  </h4>
                  <p className="text-xs text-red-200 font-semibold">{activeEmergencyEvent.incident_type}</p>
                </div>
                <div className="p-3 rounded-xl bg-red-500/20 text-red-400 border border-red-500/40">
                  <ShieldAlert className="w-8 h-8 animate-bounce" />
                </div>
              </div>

              {/* Real Camera Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono py-3 border-y border-red-950/60 bg-slate-950/40 p-3 rounded-lg">
                <div>
                  <span className="text-red-400/70 text-[9px] block uppercase font-bold">Camera Source</span>
                  <span className="font-bold text-white text-xs truncate block">{camName}</span>
                </div>
                <div>
                  <span className="text-red-400/70 text-[9px] block uppercase font-bold">Location / Zone</span>
                  <span className="font-bold text-white text-xs truncate block">{camLocation}</span>
                </div>
                <div>
                  <span className="text-red-400/70 text-[9px] block uppercase font-bold">Risk Assessment</span>
                  <span className="font-bold text-red-400 text-xs uppercase">{activeEmergencyEvent.severity}</span>
                </div>
                <div>
                  <span className="text-red-400/70 text-[9px] block uppercase font-bold">Live People Count</span>
                  <span className="font-bold text-cyan-400 text-sm">{activeEmergencyEvent.crowd_count} occupants</span>
                </div>
                <div>
                  <span className="text-red-400/70 text-[9px] block uppercase font-bold">Density Percentage</span>
                  <span className="font-bold text-yellow-400 text-sm">{activeEmergencyEvent.density_pct}%</span>
                </div>
                <div>
                  <span className="text-red-400/70 text-[9px] block uppercase font-bold">Current Event Status</span>
                  <span className="font-bold text-green-400 text-xs uppercase">{activeEmergencyEvent.status}</span>
                </div>
              </div>

              {/* AI Reason */}
              <div className="p-3 rounded-lg bg-red-950/50 border border-red-500/30 text-xs">
                <span className="text-[9px] text-red-400 font-bold uppercase block mb-1">AI Detection Reason</span>
                <p className="text-slate-200 text-xs leading-relaxed">{activeEmergencyEvent.reason}</p>
              </div>

              {/* Operator Decision & Dispatch Workflow Controls */}
              <div className="space-y-3 pt-2 border-t border-red-950/40">
                {activeEmergencyEvent.status === 'EMERGENCY_REVIEW_REQUIRED' && (
                  <div className="p-3 bg-red-950/80 border border-red-500/70 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-3">
                    <div>
                      <span className="text-[11px] font-extrabold text-red-300 block uppercase flex items-center gap-1.5">
                        <Siren className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                        EMERGENCY REVIEW REQUIRED — OPERATOR AUTHORIZATION NEEDED
                      </span>
                      <p className="text-[10px] text-slate-300">
                        Automatic dispatch is withheld. Authorized command operator review is required to approve external / field dispatch.
                      </p>
                    </div>
                    <button
                      onClick={() => approveEmergencyDispatch(activeEmergencyEvent.id)}
                      className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-extrabold text-xs uppercase tracking-wider shadow-[0_0_15px_rgba(239,68,68,0.5)] transition-all flex items-center gap-2 whitespace-nowrap cursor-pointer"
                    >
                      <ShieldAlert className="w-4 h-4" />
                      <span>Approve & Dispatch Units</span>
                    </button>
                  </div>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <button
                    onClick={() => updateEmergencyEventStatus(activeEmergencyEvent.id, 'ACKNOWLEDGED')}
                    className="py-2 px-3 rounded-lg bg-yellow-950/60 border border-yellow-500/40 hover:bg-yellow-900/60 text-yellow-300 text-xs font-bold uppercase transition-all"
                  >
                    Acknowledge
                  </button>
                  <button
                    onClick={() => approveEmergencyDispatch(activeEmergencyEvent.id)}
                    className="py-2 px-3 rounded-lg bg-blue-950/60 border border-blue-500/40 hover:bg-blue-900/60 text-blue-300 text-xs font-bold uppercase transition-all"
                  >
                    Authorize Dispatch
                  </button>
                  <button
                    onClick={() => updateEmergencyEventStatus(activeEmergencyEvent.id, 'ARRIVED')}
                    className="py-2 px-3 rounded-lg bg-purple-950/60 border border-purple-500/40 hover:bg-purple-900/60 text-purple-300 text-xs font-bold uppercase transition-all"
                  >
                    Mark Arrived
                  </button>
                  <button
                    onClick={() => updateEmergencyEventStatus(activeEmergencyEvent.id, 'RESOLVED')}
                    className="py-2 px-3 rounded-lg bg-green-950/60 border border-green-500/40 hover:bg-green-900/60 text-green-300 text-xs font-bold uppercase transition-all"
                  >
                    Resolve Event
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* NO ACTIVE EMERGENCY STATE */
            <GlassCard className="p-12 text-center space-y-4 border border-slate-900 flex flex-col items-center justify-center min-h-[300px]">
              <div className="w-14 h-14 rounded-full bg-green-950/60 border border-green-500/40 flex items-center justify-center text-green-400">
                <CheckCheck className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-white uppercase tracking-wider">NO ACTIVE EMERGENCY</h3>
                <p className="text-xs text-slate-400 mt-1">
                  System operating securely. YOLO AI crowd surveillance pipeline running on camera stream <code className="text-cyan-400">{activeCam?.name || 'Active Camera'}</code>.
                </p>
              </div>
            </GlassCard>
          )}

          {/* Emergency Response Timeline */}
          {activeEmergencyEvent && (
            <div className="cyber-glass p-5 rounded-xl border border-blue-500/10 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-slate-900 pb-2">
                Emergency Response Timeline (Real Timestamps)
              </h4>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex items-center gap-3 text-slate-400">
                  <span className="text-cyan-400 font-bold">{activeEmergencyEvent.detected_at}</span>
                  <span>AI detected critical crowd condition on camera <code className="text-slate-200">{activeEmergencyEvent.camera_id}</code></span>
                </div>
                <div className="flex items-center gap-3 text-slate-400">
                  <span className="text-cyan-400 font-bold">{activeEmergencyEvent.detected_at}</span>
                  <span>Emergency event created in MySQL <code className="text-slate-200">emergency_events</code> table</span>
                </div>
                <div className="flex items-center gap-3 text-slate-400">
                  <span className="text-cyan-400 font-bold">{activeEmergencyEvent.detected_at}</span>
                  <span>Emergency location identified: <strong className="text-white">{activeEmergencyEvent.location}</strong></span>
                </div>
                {activeEmergencyDispatches.map(d => (
                  <div key={d.id} className="flex items-center gap-3 text-slate-300">
                    <span className="text-green-400 font-bold">{d.timestamp}</span>
                    <span>
                      {d.service_type.toUpperCase()} dispatch signal transmitted ({d.staff_name || 'Duty Desk'})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Emergency Services Channels & Manual Simulators (Col 5) */}
        <div className="lg:col-span-5 space-y-4">
          
          {/* Emergency Response Channels */}
          <div className="cyber-glass p-5 rounded-xl border border-blue-500/10 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Radio className="w-4 h-4 text-cyan-400" /> Response Channels
              </h3>
              <span className="text-[9px] bg-blue-950 border border-blue-500/30 text-blue-300 px-2 py-0.5 rounded uppercase font-bold">
                SIMULATED / DEMO DISPATCH
              </span>
            </div>

            <div className="space-y-3">
              {/* Medical Response */}
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-900 flex justify-between items-center">
                <div className="flex items-center gap-2.5">
                  <Ambulance className="w-5 h-5 text-red-400" />
                  <div>
                    <span className="text-xs font-bold text-white block">🚑 Ambulance / Medical Response</span>
                    <span className="text-[10px] text-slate-500">Location: {camLocation}</span>
                  </div>
                </div>
                {getServiceDispatch('medical') ? (
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-green-950 text-green-400 border border-green-500/30 uppercase flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-green-400" /> DISPATCHED
                  </span>
                ) : (
                  <button
                    onClick={() => handleOpenDispatchDialog('medical', 'Ambulance / Medical Response')}
                    disabled={isDispatching}
                    className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-extrabold text-[10px] uppercase tracking-wider transition-all shadow-[0_0_12px_rgba(239,68,68,0.4)] flex items-center gap-1 cursor-pointer"
                  >
                    <span>READY → DISPATCH</span>
                  </button>
                )}
              </div>

              {/* Fire & Rescue */}
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-900 flex justify-between items-center">
                <div className="flex items-center gap-2.5">
                  <Flame className="w-5 h-5 text-orange-400" />
                  <div>
                    <span className="text-xs font-bold text-white block">🚒 Fire & Rescue</span>
                    <span className="text-[10px] text-slate-500">Location: {camLocation}</span>
                  </div>
                </div>
                {getServiceDispatch('fire') ? (
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-green-950 text-green-400 border border-green-500/30 uppercase flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-green-400" /> DISPATCHED
                  </span>
                ) : (
                  <button
                    onClick={() => handleOpenDispatchDialog('fire', 'Fire & Rescue Service')}
                    disabled={isDispatching}
                    className="px-3 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white font-extrabold text-[10px] uppercase tracking-wider transition-all shadow-[0_0_12px_rgba(249,115,22,0.4)] flex items-center gap-1 cursor-pointer"
                  >
                    <span>READY → DISPATCH</span>
                  </button>
                )}
              </div>

              {/* Police */}
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-900 flex justify-between items-center">
                <div className="flex items-center gap-2.5">
                  <Shield className="w-5 h-5 text-blue-400" />
                  <div>
                    <span className="text-xs font-bold text-white block">👮 Police Response</span>
                    <span className="text-[10px] text-slate-500">Location: {camLocation}</span>
                  </div>
                </div>
                {getServiceDispatch('police') ? (
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-green-950 text-green-400 border border-green-500/30 uppercase flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-green-400" /> DISPATCHED
                  </span>
                ) : (
                  <button
                    onClick={() => handleOpenDispatchDialog('police', 'Police Response Unit')}
                    disabled={isDispatching}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-extrabold text-[10px] uppercase tracking-wider transition-all shadow-[0_0_12px_rgba(59,130,246,0.4)] flex items-center gap-1 cursor-pointer"
                  >
                    <span>READY → DISPATCH</span>
                  </button>
                )}
              </div>

              {/* On-Site Security */}
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-900 flex justify-between items-center">
                <div className="flex items-center gap-2.5">
                  <UserCheck className="w-5 h-5 text-cyan-400" />
                  <div>
                    <span className="text-xs font-bold text-white block">🛡️ On-Site Security Squad</span>
                    <span className="text-[10px] text-slate-500">
                      Assigned: {getServiceDispatch('security')?.staff_name || 'On-Duty Security Dispatch'}
                    </span>
                  </div>
                </div>
                {getServiceDispatch('security') ? (
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-green-950 text-green-400 border border-green-500/30 uppercase flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-green-400" /> DISPATCHED
                  </span>
                ) : (
                  <button
                    onClick={() => handleOpenDispatchDialog('security', 'On-Site Security Squad')}
                    disabled={isDispatching}
                    className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-extrabold text-[10px] uppercase tracking-wider transition-all shadow-[0_0_12px_rgba(6,182,212,0.4)] flex items-center gap-1 cursor-pointer"
                  >
                    <span>READY → DISPATCH</span>
                  </button>
                )}
              </div>

              {/* Emergency Control Room */}
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-900 flex justify-between items-center">
                <div className="flex items-center gap-2.5">
                  <Building className="w-5 h-5 text-purple-400" />
                  <div>
                    <span className="text-xs font-bold text-white block">🚨 Emergency Control Room</span>
                    <span className="text-[10px] text-slate-500 font-mono">Central Oversight Desk</span>
                  </div>
                </div>
                <span className="text-[10px] font-bold px-2 py-1 rounded bg-green-950 text-green-400 border border-green-500/30 uppercase">
                  MONITORING
                </span>
              </div>
            </div>
          </div>

          {/* Manual Simulation Triggers */}
          <div className="cyber-glass p-5 rounded-xl border border-blue-500/10 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Manual Override Triggers
              </h3>
              <span className="text-[9px] text-yellow-400 font-bold uppercase">
                TEST / SIMULATION ONLY
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-normal">
              Simulate crisis scenarios for system demonstration. Explicitly tagged as <strong>TEST / SIMULATION ONLY</strong>.
            </p>

            <div className="flex flex-col gap-2 pt-1">
              <button
                onClick={() => handleSimulate('Stampede Risk')}
                disabled={simulating}
                className="w-full py-2 px-3 rounded-lg bg-red-950/40 border border-red-500/30 hover:bg-red-900/40 text-red-300 font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2"
              >
                <Users className="w-4 h-4 text-red-500" /> [TEST / SIMULATION ONLY] Stampede Risk
              </button>

              <button
                onClick={() => handleSimulate('Fire Outbreak')}
                disabled={simulating}
                className="w-full py-2 px-3 rounded-lg bg-red-950/40 border border-red-500/30 hover:bg-red-900/40 text-red-300 font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2"
              >
                <Flame className="w-4 h-4 text-red-500" /> [TEST / SIMULATION ONLY] Fire Outbreak
              </button>

              <button
                onClick={() => handleSimulate('Medical Emergency')}
                disabled={simulating}
                className="w-full py-2 px-3 rounded-lg bg-red-950/40 border border-red-500/30 hover:bg-red-900/40 text-red-300 font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2"
              >
                <Activity className="w-4 h-4 text-red-500" /> [TEST / SIMULATION ONLY] Medical / Crowd Crush
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Emergency Service Dispatch Authorization & Confirmation Modal */}
      {dispatchModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fade-in font-mono select-none">
          <div className="w-full max-w-lg cyber-glass p-6 border-2 border-red-500/50 rounded-2xl space-y-4 shadow-[0_0_40px_rgba(239,68,68,0.3)]">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-red-950/60 pb-3">
              <div className="flex items-center gap-2">
                <Siren className="w-5 h-5 text-red-500 animate-pulse" />
                <h3 className="text-sm uppercase tracking-wider font-extrabold text-white">
                  Confirm Emergency Unit Dispatch
                </h3>
              </div>
              <button 
                onClick={() => setDispatchModal(null)} 
                disabled={isDispatching}
                className="text-slate-400 hover:text-white p-1 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Incident & Dispatch Context Summary */}
            <div className="p-3.5 rounded-xl bg-slate-950/90 border border-slate-900 space-y-2 text-xs">
              <div className="flex justify-between items-center border-b border-slate-900 pb-2">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Selected Service:</span>
                <span className="text-white font-bold text-xs">{dispatchModal.serviceLabel}</span>
              </div>
              <div className="flex justify-between items-center border-b border-slate-900 pb-2">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Target Location / Sector:</span>
                <span className="text-cyan-400 font-bold text-xs">{camLocation}</span>
              </div>
              <div className="flex justify-between items-center border-b border-slate-900 pb-2">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Linked Camera Feeds:</span>
                <span className="text-slate-300 font-medium text-xs">{camName}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Current Alert Context:</span>
                <span className="text-yellow-400 font-bold text-xs truncate max-w-[240px]">
                  {activeEmergencyEvent ? activeEmergencyEvent.incident_type : 'Operator Precautionary Response'}
                </span>
              </div>
            </div>

            {/* Station Selection */}
            <div className="space-y-1 text-xs">
              <label className="text-[10px] text-slate-400 uppercase font-bold">
                Assigned Responding Station / Tactical Unit:
              </label>
              <select
                value={selectedStation}
                onChange={(e) => setSelectedStation(e.target.value)}
                disabled={isDispatching}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-cyber-border text-white text-xs focus:outline-none focus:border-cyan-500"
              >
                {dispatchModal.serviceType === 'medical' && (
                  <>
                    <option value="Station 4 - City General EMS Unit (Nearest)">Station 4 - City General EMS Unit (Nearest - 1.2 km)</option>
                    <option value="On-Site Medical Booth Alpha">On-Site Medical Booth Alpha (Venue Concourse)</option>
                    <option value="Metropolitan Trauma Dispatch Hub">Metropolitan Trauma Dispatch Hub</option>
                  </>
                )}
                {dispatchModal.serviceType === 'fire' && (
                  <>
                    <option value="Engine Company 12 - Metro Fire Command (Nearest)">Engine Company 12 - Metro Fire Command (Nearest - 2.0 km)</option>
                    <option value="Venue Internal Fire Suppression Unit">Venue Internal Fire Suppression Unit (Gate 2)</option>
                    <option value="District Hazmat & Ladder Battalion">District Hazmat & Ladder Battalion</option>
                  </>
                )}
                {dispatchModal.serviceType === 'police' && (
                  <>
                    <option value="Precinct 3 - Rapid Tactical Unit">Precinct 3 - Rapid Tactical Unit (Nearest - 0.8 km)</option>
                    <option value="Venue Law Enforcement Taskforce">Venue Law Enforcement Taskforce</option>
                    <option value="City Traffic & Perimeter Control">City Traffic & Perimeter Control</option>
                  </>
                )}
                {dispatchModal.serviceType === 'security' && (
                  <>
                    <option value="Security Squad Charlie - Gate & Concourse Patrol">Security Squad Charlie - Gate & Concourse Patrol</option>
                    <option value="VIP & Perimeter Squad Alpha">VIP & Perimeter Squad Alpha</option>
                    <option value="Central Control Room Response Unit">Central Control Room Response Unit</option>
                  </>
                )}
              </select>
            </div>

            {/* Dispatch Notes / Operator Message */}
            <div className="space-y-1 text-xs">
              <label className="text-[10px] text-slate-400 uppercase font-bold">
                Operator Dispatch Message / Routing Notes:
              </label>
              <input
                type="text"
                value={dispatchNotes}
                onChange={(e) => setDispatchNotes(e.target.value)}
                disabled={isDispatching}
                placeholder="e.g. Rapid deployment via North Gate access corridor."
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-cyber-border text-white text-xs focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Real-World Safety Audit Notice (Honest Disclosure) */}
            <div className="p-3 rounded-lg bg-yellow-950/40 border border-yellow-500/40 flex items-start gap-2.5 text-[11px] text-yellow-200/90 leading-relaxed">
              <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-yellow-400 font-bold block uppercase text-[10px]">REAL-WORLD SAFETY DISCLOSURE</strong>
                <span>
                  This action records an authenticated operational dispatch record in the internal surveillance database and notifies on-site personnel. No public carrier 911/PSAP line is dialed automatically. In life-threatening emergencies, call emergency services directly.
                </span>
              </div>
            </div>

            {/* Result Outcome Display */}
            {dispatchOutcome && (
              <div className={`p-3 rounded-lg border text-xs leading-relaxed flex items-center gap-2 ${
                dispatchOutcome.success 
                  ? 'bg-green-950/60 border-green-500/50 text-green-300' 
                  : 'bg-red-950/60 border-red-500/50 text-red-300'
              }`}>
                {dispatchOutcome.success ? (
                  <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                )}
                <div className="min-w-0 flex-1">
                  <span className="font-bold block uppercase text-[10px]">
                    {dispatchOutcome.success ? 'Dispatch Confirmed & Persisted' : 'Dispatch Failed'}
                  </span>
                  <span>{dispatchOutcome.message}</span>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2 border-t border-slate-900">
              {dispatchOutcome?.success ? (
                <button
                  type="button"
                  onClick={() => setDispatchModal(null)}
                  className="w-full py-2.5 rounded-lg bg-green-600 hover:bg-green-500 text-white font-bold text-xs uppercase tracking-wider transition-colors cursor-pointer"
                >
                  Done
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={handleConfirmDispatch}
                    disabled={isDispatching}
                    className="flex-1 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider transition-all shadow-[0_0_15px_rgba(239,68,68,0.4)] flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    {isDispatching ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Transmitting Dispatch...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span>Authorize & Transmit Dispatch</span>
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setDispatchModal(null)}
                    disabled={isDispatching}
                    className="py-2.5 px-4 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
};
