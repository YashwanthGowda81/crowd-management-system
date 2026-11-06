import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { 
  Cpu, 
  ShieldCheck, 
  XCircle, 
  User, 
  MapPin, 
  AlertTriangle, 
  CheckCircle2,
  ArrowRight,
  Activity,
  Compass,
  RotateCcw,
  ExternalLink,
  ShieldAlert
} from 'lucide-react';
import { motion } from 'framer-motion';

export const DecisionSupport: React.FC = () => {
  const navigate = useNavigate();
  const { 
    cameras,
    zones,
    recommendations,
    reservations,
    fetchReservations,
    approveRecommendation, 
    rejectRecommendation,
    startDiversionInTransit,
    completeDiversion,
    cancelDiversion,
    reconcileCancellation,
    recommendationError,
    clearRecommendationError,
    selectedEventId
  } = useCrowdSystem();

  // Override Modal State
  const [overrideModalRecId, setOverrideModalRecId] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState('');

  // Reconcile Modal State
  const [reconcileModalRecId, setReconcileModalRecId] = useState<string | null>(null);
  const [reconcileAction, setReconcileAction] = useState<'halted' | 'redirected' | 'dispersed'>('halted');
  const [reconcileNotes, setReconcileNotes] = useState('');

  const analyzingCams = cameras.filter(c => c.enabled && (c.playbackStatus === 'analyzing' || c.playbackStatus === 'playing'));
  
  // Authoritative operational directives: pending approval, approved, in transit, or cancellation pending
  const operationalRecs = recommendations.filter(r => 
    ['pending', 'approved', 'in_transit', 'cancellation_pending'].includes(r.status)
  );
  const activePendingRecs = recommendations.filter(r => r.status === 'pending');
  const actionedRecs = recommendations.filter(r => 
    ['completed', 'rejected', 'dismissed', 'cancelled'].includes(r.status)
  );

  const selectedRec = recommendations.find(r => r.id === overrideModalRecId);
  const selectedReconcileRec = recommendations.find(r => r.id === reconcileModalRecId);

  useEffect(() => {
    fetchReservations(selectedEventId || undefined);
    const interval = setInterval(() => {
      fetchReservations(selectedEventId || undefined);
    }, 10000);
    return () => clearInterval(interval);
  }, [selectedEventId]);

  const handleRejectWithReason = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideModalRecId || !overrideReason.trim()) return;
    const res = await rejectRecommendation(overrideModalRecId, overrideReason);
    if (res.success) {
      setOverrideModalRecId(null);
      setOverrideReason('');
    }
  };

  const handleReconcileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reconcileModalRecId || !reconcileNotes.trim()) return;
    const res = await reconcileCancellation(reconcileModalRecId, {
      resolution_action: reconcileAction,
      reconciliation_notes: reconcileNotes.trim()
    });
    if (res.success) {
      setReconcileModalRecId(null);
      setReconcileNotes('');
    }
  };

  const priorityColors: Record<string, string> = {
    critical: 'text-red-400 border-red-500/40 bg-red-950/40 font-extrabold animate-pulse',
    high: 'text-red-400 border-red-500/20 bg-red-950/20',
    medium: 'text-orange-400 border-orange-500/20 bg-orange-950/20',
    low: 'text-cyan-400 border-cyan-500/20 bg-cyan-950/20',
  };

  // Helper to resolve authoritative zone monitoring health from backend zones
  const getZoneMonitoringInfo = (zoneName?: string) => {
    if (!zoneName) {
      return {
        label: 'Destination Unallocated',
        status: 'unallocated',
        isMonitored: false,
        badgeClass: 'bg-slate-900 border-slate-800 text-slate-400'
      };
    }
    const z = zones.find(
      zone => zone.name.toLowerCase() === zoneName.toLowerCase() || 
              zone.id === zoneName || 
              zone.code?.toLowerCase() === zoneName.toLowerCase()
    );
    if (!z) {
      return {
        label: 'Zone Coverage Unverified',
        status: 'unverified',
        isMonitored: false,
        badgeClass: 'bg-amber-950/60 border-amber-500/30 text-amber-300'
      };
    }
    const camCount = z.assigned_cameras_count || 0;
    if (!z.is_monitored || camCount === 0) {
      return {
        label: 'Unmonitored Zone (0 Cameras)',
        status: 'unmonitored',
        isMonitored: false,
        badgeClass: 'bg-red-950/60 border-red-500/40 text-red-300'
      };
    }
    if (z.monitoring_status === 'stale') {
      return {
        label: `Stale Telemetry (${camCount} Cam${camCount > 1 ? 's' : ''})`,
        status: 'stale',
        isMonitored: false,
        badgeClass: 'bg-amber-950/60 border-amber-500/30 text-amber-300'
      };
    }
    return {
      label: `Monitored (${camCount} Healthy Cam${camCount > 1 ? 's' : ''})`,
      status: 'healthy',
      isMonitored: true,
      badgeClass: 'bg-emerald-950/60 border-emerald-500/30 text-emerald-300'
    };
  };

  return (
    <div className="space-y-6 pb-12 font-mono">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border pb-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs mb-1">
            <Cpu className="w-4 h-4" />
            <span>OPERATIONAL DECISION SUPPORT & DIRECTIVES</span>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            Crowd Incident Decision Support
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Authoritative crowd risk directives, destination capacity verification, directed diversion management, 
            and human-authorized dispatch lifecycle.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="text-slate-500">Active Streams: </span>
            <span className="text-cyan-400 font-extrabold text-sm ml-1">{analyzingCams.length}</span>
          </div>
        </div>
      </div>

      {/* OPERATIONAL DIRECTIVES MAIN VIEW */}
      <div className="space-y-6">
        {/* Recommendation Error Alert Banner */}
        {recommendationError && (
          <div className="p-4 rounded-xl bg-red-950/60 border border-red-500/60 text-red-200 flex items-center justify-between gap-3 text-xs shadow-lg animate-pulse">
            <div className="flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-red-400 shrink-0" />
              <div>
                <span className="font-bold uppercase tracking-wider block text-red-300">Safety & Validation Alert</span>
                <p className="text-[11px] text-red-200 mt-0.5">{recommendationError}</p>
              </div>
            </div>
            <button
              onClick={clearRecommendationError}
              className="px-3 py-1.5 rounded-lg bg-red-900/80 hover:bg-red-800 text-white font-mono text-[10px] uppercase font-bold shrink-0 transition-colors"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Operational Safety & Invariants Banner */}
        <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-900/40 text-blue-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-bold text-white">Operational Safety Safeguards</h4>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {analyzingCams.length > 0
                  ? `Automated crowd safety evaluation active across ${analyzingCams.length} streams. ${activePendingRecs.length} pending authorization, ${operationalRecs.filter(r => r.status === 'in_transit').length} in transit.`
                  : 'Decision support engine operating in standby. Live cameras or stored telemetry active.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[10px]">
            <span className="text-slate-500">Human Authorization Safeguard:</span>
            <span className="text-emerald-400 font-bold bg-emerald-950/60 border border-emerald-500/20 px-2 py-0.5 rounded">
              ENFORCED (NO AUTO-DISPATCH)
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Active Operational Directives List (Col 8) */}
          <div className="lg:col-span-8 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Actionable Directives & Divert Corridors
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-[10px] px-2 py-0.5 bg-cyan-950 text-cyan-400 border border-cyan-500/20 rounded font-bold">
                  {operationalRecs.length} Active Directives
                </span>
              </div>
            </div>

            <div className="space-y-4">
              {operationalRecs.length === 0 ? (
                <div className="cyber-glass p-8 text-center text-slate-500 text-xs">
                  No active operational directives. All monitored crowd zones are currently within acceptable safety parameters.
                </div>
              ) : (
                operationalRecs.map((rec) => {
                  const destMonitoring = getZoneMonitoringInfo(rec.destination_zone);
                  const sourceMonitoring = getZoneMonitoringInfo(rec.zone);

                  return (
                    <div 
                      key={rec.id} 
                      className={`cyber-glass p-5 rounded-xl border flex flex-col justify-between gap-4 transition-all duration-300 ${
                        rec.status === 'cancellation_pending'
                          ? 'border-amber-500/50 bg-amber-950/10'
                          : rec.status === 'in_transit'
                            ? 'border-blue-500/40 bg-blue-950/10'
                            : rec.status === 'approved'
                              ? 'border-emerald-500/30'
                              : 'border-blue-500/10 hover:border-cyan-500/30'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            {/* Authoritative Risk / Priority */}
                            <span className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase ${priorityColors[rec.priority]}`}>
                              {rec.priority} Priority
                            </span>
                            {/* Authoritative Confidence */}
                            <span className="text-xs text-cyan-400 font-bold">
                              Confidence: {rec.confidence}%
                            </span>
                            {/* Operational Status Tag */}
                            <span className={`text-[9px] font-bold px-2 py-0.5 rounded uppercase border font-mono ${
                              rec.status === 'pending'
                                ? 'bg-amber-950/60 border-amber-500/30 text-amber-300'
                                : rec.status === 'approved'
                                  ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-300'
                                  : rec.status === 'in_transit'
                                    ? 'bg-blue-950/80 border-blue-500/40 text-blue-300 animate-pulse'
                                    : 'bg-red-950/80 border-red-500/50 text-red-300 animate-pulse'
                            }`}>
                              {rec.status === 'pending' && 'Awaiting Approval'}
                              {rec.status === 'approved' && 'Authorized & Reserved'}
                              {rec.status === 'in_transit' && 'Diversion In Transit'}
                              {rec.status === 'cancellation_pending' && '⚠️ Cancellation Pending Reconciliation'}
                            </span>
                          </div>
                          {/* Title */}
                          <h4 className="text-base font-bold text-white transition-colors">
                            {rec.title}
                          </h4>
                        </div>

                        <div className="p-2 rounded bg-slate-900 border border-slate-800 text-cyan-400 shrink-0">
                          <Cpu className="w-4 h-4" />
                        </div>
                      </div>

                      {/* Source & Destination Zones with Camera Monitoring Health */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs p-3.5 bg-slate-950/80 rounded-lg border border-slate-900">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 text-slate-300">
                            <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                            <span className="text-slate-500">Source Zone:</span>
                            <strong className="text-white font-bold">{rec.zone}</strong>
                          </div>
                          <div className="text-[10px] flex items-center gap-1">
                            <span className="text-slate-500">Camera Health:</span>
                            <span className={`px-1.5 py-0.5 rounded font-bold border ${sourceMonitoring.badgeClass}`}>
                              {sourceMonitoring.label}
                            </span>
                          </div>
                        </div>

                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 text-slate-300">
                            <Compass className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            <span className="text-slate-500">Primary Destination:</span>
                            <strong className="text-emerald-300 font-bold">
                              {rec.destination_zone || 'Destination Corridor Pending Allocation'}
                            </strong>
                          </div>
                          <div className="text-[10px] flex items-center gap-1">
                            <span className="text-slate-500">Destination Status:</span>
                            <span className={`px-1.5 py-0.5 rounded font-bold border ${destMonitoring.badgeClass}`}>
                              {destMonitoring.label}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Capacity Verification Status & Diversion Headroom */}
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        {rec.is_capacity_verified ? (
                          <span className="px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-[10px] font-bold flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            Capacity Verified (+{rec.mitigation_capacity ?? 100} Available Headroom)
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded bg-amber-950/60 border border-amber-500/30 text-amber-300 text-[10px] font-bold flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                            Capacity Unverified (No Headroom Formally Verified)
                          </span>
                        )}

                        {rec.diversion_volume != null ? (
                          <span className="px-2.5 py-1 rounded bg-blue-950/60 border border-blue-500/30 text-cyan-300 text-[10px] font-bold">
                            Diversion Volume: {rec.diversion_volume} persons
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400 text-[10px]">
                            Diversion Volume: Unspecified / Unverified
                          </span>
                        )}

                        {rec.officer && (
                          <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400 text-[10px] flex items-center gap-1">
                            <User className="w-3 h-3 text-cyan-400" /> Assigned Unit: {rec.officer}
                          </span>
                        )}
                      </div>

                      {/* Plain-Language Operational Rationale */}
                      <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-900 text-[11px] text-slate-300 leading-relaxed">
                        <span className="text-[9px] text-cyan-500 font-semibold block uppercase tracking-wider mb-0.5">
                          Operational Reason & Assessment:
                        </span>
                        {rec.reason}
                      </div>

                      {/* Backend Safety Warning */}
                      {rec.suggestedAction && rec.suggestedAction.toLowerCase().includes('warning') && (
                        <div className="p-2.5 rounded bg-amber-950/30 border border-amber-500/30 text-[10px] text-amber-300 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                          <span>{rec.suggestedAction}</span>
                        </div>
                      )}

                      {/* Authoritative Lifecycle Action Controls */}
                      <div className="pt-2 border-t border-slate-900/60">
                        {rec.status === 'pending' && (
                          <div className="flex flex-wrap gap-3">
                            <button
                              onClick={() => approveRecommendation(rec.id)}
                              className="flex-1 py-2 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(6,182,212,0.2)]"
                            >
                              <CheckCircle2 className="w-4 h-4" /> Authorize & Reserve Capacity
                            </button>
                            
                            <button
                              onClick={() => setOverrideModalRecId(rec.id)}
                              className="py-2 px-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-red-500/40 text-slate-300 hover:text-red-400 text-xs font-bold transition-colors flex items-center gap-1.5"
                            >
                              <XCircle className="w-4 h-4" /> Reject (Officer Override)
                            </button>
                          </div>
                        )}

                        {rec.status === 'approved' && (
                          <div className="flex flex-wrap gap-3">
                            <button
                              onClick={() => startDiversionInTransit(rec.id)}
                              className="flex-1 py-2 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(16,185,129,0.2)]"
                            >
                              <ArrowRight className="w-4 h-4" /> Confirm In-Transit Diversion
                            </button>
                            
                            <button
                              onClick={() => cancelDiversion(rec.id, { reason: "Cancelled by officer before physical crowd movement" })}
                              className="py-2 px-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-amber-500/40 text-slate-300 hover:text-amber-400 text-xs font-bold transition-colors flex items-center gap-1.5"
                            >
                              <XCircle className="w-4 h-4" /> Cancel Operation
                            </button>
                          </div>
                        )}

                        {rec.status === 'in_transit' && (
                          <div className="space-y-2">
                            <div className="p-2.5 rounded bg-blue-950/40 border border-blue-500/30 text-[10px] text-blue-300 flex items-center gap-2">
                              <Activity className="w-3.5 h-3.5 text-blue-400 animate-pulse shrink-0" />
                              <span>Crowd diversion is physically underway. Destination headroom remains active at <strong>{rec.destination_zone}</strong>.</span>
                            </div>
                            <div className="flex flex-wrap gap-3">
                              <button
                                onClick={() => completeDiversion(rec.id)}
                                className="flex-1 py-2 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(6,182,212,0.2)]"
                              >
                                <CheckCircle2 className="w-4 h-4" /> Mark Diversion Completed
                              </button>
                              
                              <button
                                onClick={() => cancelDiversion(rec.id, { reason: "Aborted while in transit" })}
                                className="py-2 px-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-red-500/40 text-slate-300 hover:text-red-400 text-xs font-bold transition-colors flex items-center gap-1.5"
                              >
                                <XCircle className="w-4 h-4" /> Cancel In-Transit
                              </button>
                            </div>
                          </div>
                        )}

                        {rec.status === 'cancellation_pending' && (
                          <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/40 space-y-2.5">
                            <div className="flex items-start gap-2 text-xs text-amber-300">
                              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                              <div className="space-y-0.5">
                                <strong className="block text-amber-200">Cancellation Requires Physical Ground Reconciliation</strong>
                                <p className="text-[10px] text-amber-300/80 leading-relaxed">
                                  Diversion was halted while crowds were moving. Capacity reservation remains held at destination zone <strong>{rec.destination_zone}</strong> until an authorized officer submits physical verification findings.
                                </p>
                              </div>
                            </div>
                            <button
                              onClick={() => {
                                setReconcileModalRecId(rec.id);
                                setReconcileAction('halted');
                                setReconcileNotes('');
                              }}
                              className="w-full py-2.5 px-4 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(245,158,11,0.2)]"
                            >
                              <ShieldCheck className="w-4 h-4" /> Reconcile Cancellation & Release Headroom
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Authoritative Destination Capacity Reservations Panel */}
            <div className="cyber-glass p-5 rounded-xl border border-cyan-500/20 space-y-3 mt-6">
              <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                <div className="flex items-center gap-2">
                  <Compass className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Authoritative Destination Capacity Reservations ({reservations.length})
                  </h3>
                </div>
                <button
                  onClick={() => fetchReservations(selectedEventId || undefined)}
                  className="text-[10px] text-cyan-400 hover:text-cyan-300 font-bold uppercase flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" /> Refresh
                </button>
              </div>

              {reservations.length === 0 ? (
                <div className="p-4 text-center text-slate-500 text-xs italic">
                  No active or historical destination capacity reservations recorded.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-500 text-[10px] uppercase">
                        <th className="py-1 px-2">Source</th>
                        <th className="py-1 px-2">Destination</th>
                        <th className="py-1 px-2 text-center">Volume</th>
                        <th className="py-1 px-2 text-center">Reservation Status</th>
                        <th className="py-1 px-2">Officer</th>
                        <th className="py-1 px-2">Reconciliation Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40 text-[11px]">
                      {reservations.map(res => (
                        <tr key={res.id} className="hover:bg-slate-900/40">
                          <td className="py-1.5 px-2 font-bold text-slate-300">{res.source_zone}</td>
                          <td className="py-1.5 px-2 font-bold text-emerald-300">{res.destination_zone}</td>
                          <td className="py-1.5 px-2 text-center font-mono font-bold text-white">
                            {res.diversion_volume}
                          </td>
                          <td className="py-1.5 px-2 text-center font-mono">
                            <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
                              res.status === 'reserved'
                                ? 'bg-cyan-950 text-cyan-400 border-cyan-500/30'
                                : res.status === 'in_transit'
                                  ? 'bg-blue-950 text-blue-400 border-blue-500/30 animate-pulse'
                                  : res.status === 'cancellation_pending'
                                    ? 'bg-amber-950 text-amber-400 border-amber-500/30 animate-pulse'
                                    : res.status === 'completed'
                                      ? 'bg-emerald-950 text-emerald-400 border-emerald-500/30'
                                      : 'bg-slate-900 text-slate-400 border-slate-800'
                            }`}>
                              {res.status}
                            </span>
                          </td>
                          <td className="py-1.5 px-2 text-slate-400 text-[10px]">{res.approved_by || '—'}</td>
                          <td className="py-1.5 px-2 text-slate-400 text-[10px] truncate max-w-[180px]" title={res.reconciliation_notes || ''}>
                            {res.reconciliation_notes || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Audit Log / History List (Col 4) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Resolved Operations Audit Log
              </h3>
              <span className="text-[10px] text-slate-500">Security Archive</span>
            </div>

            <div className="cyber-glass p-5 rounded-xl border border-blue-500/10 space-y-4 min-h-[300px]">
              <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
                {actionedRecs.length === 0 ? (
                  <div className="text-center py-12 text-slate-600 text-xs italic">
                    No resolved operations in active session cache.
                  </div>
                ) : (
                  actionedRecs.map(rec => (
                    <div 
                      key={rec.id} 
                      className={`p-3.5 rounded-xl border text-xs space-y-2
                        ${rec.status === 'completed'
                          ? 'bg-green-950/10 border-green-900/40 text-green-200' 
                          : rec.status === 'cancelled'
                            ? 'bg-amber-950/10 border-amber-900/40 text-amber-200'
                            : 'bg-red-950/10 border-red-900/40 text-red-300'}`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-bold truncate">{rec.title}</span>
                        <span className={`text-[8px] font-bold px-1.5 py-0.2 rounded uppercase border
                          ${rec.status === 'completed'
                            ? 'bg-green-950 border border-green-500/20 text-green-400' 
                            : rec.status === 'cancelled'
                              ? 'bg-amber-950 border border-amber-500/20 text-amber-400'
                              : 'bg-red-950 border border-red-500/20 text-red-400'}`}
                        >
                          {rec.status}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-400 leading-normal">{rec.reason}</p>
                      
                      {rec.overrideReason && (
                        <div className="p-2 rounded bg-slate-950 border border-red-500/20 text-[9px] text-red-300">
                          <strong>Audit Justification:</strong> "{rec.overrideReason}"
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Discreet Academic Research Demonstrator Link at Page Footer */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-900 text-xs flex flex-col sm:flex-row items-center justify-between gap-3 text-slate-500">
          <div className="flex items-center gap-2">
            <ExternalLink className="w-4 h-4 text-cyan-400 shrink-0" />
            <span>Academic research review or mathematical proof inspection?</span>
          </div>
          <button
            onClick={() => navigate('/research-analytics')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-bold underline transition-colors"
          >
            Access Formal Concept Analysis & Algorithm Benchmark Console →
          </button>
        </div>
      </div>

      {/* MANUAL OVERRIDE REASON MODAL */}
      {overrideModalRecId && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-full max-w-md cyber-glass p-6 border border-red-500/30 rounded-2xl space-y-4"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-red-400" />
                <h3 className="text-sm font-bold text-white">Manual Override - Reject Directive</h3>
              </div>
            </div>

            <form onSubmit={handleRejectWithReason} className="space-y-4 text-xs font-mono">
              <p className="text-slate-400 leading-relaxed">
                Rejecting AI Recommendation: <strong className="text-white">"{selectedRec?.title}"</strong>. Please enter an operational justification for security audit logs.
              </p>

              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 block font-mono">Reason for Override</label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. Ground inspection confirms corridor blocked..."
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-white focus:outline-none focus:border-red-500/40 text-xs font-mono"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-900">
                <button
                  type="button"
                  onClick={() => setOverrideModalRecId(null)}
                  className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold"
                >
                  Confirm Override & Reject
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* CANCELLATION RECONCILIATION MODAL */}
      {reconcileModalRecId && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-full max-w-lg cyber-glass p-6 border border-amber-500/40 rounded-2xl space-y-4"
          >
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <ShieldCheck className="w-5 h-5 text-amber-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wide">
                Physical Cancellation Reconciliation
              </h3>
            </div>

            <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-500/20 text-xs text-amber-300/90 leading-relaxed">
              <strong>Authoritative Safety Safeguard:</strong> In-transit cancellation of <strong>"{selectedReconcileRec?.title || 'Operational Diversion'}"</strong> preserves destination capacity reservation until an authorized officer verifies that diverted crowds have safely dispersed or halted.
            </div>

            <form onSubmit={handleReconcileSubmit} className="space-y-4 text-xs font-mono">
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 block">
                  Physical Ground Resolution Action *
                </label>
                <select
                  value={reconcileAction}
                  onChange={(e) => setReconcileAction(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-cyber-border text-white text-xs font-mono focus:outline-none focus:border-amber-500/40"
                >
                  <option value="halted">Halted — Diversion halted mid-route; crowd held safely in transit concourse</option>
                  <option value="redirected">Redirected — Crowd redirected to alternative open space</option>
                  <option value="dispersed">Dispersed — Corridor inspected clear; crowd naturally dispersed</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 block">
                  Officer Inspection Findings & Ground Verification Notes *
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. Officer inspected Corridor Gate 3; verified crowd safely diverted to open concourse with zero congestion..."
                  value={reconcileNotes}
                  onChange={(e) => setReconcileNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-cyber-border text-white text-xs font-mono focus:outline-none focus:border-amber-500/40"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-900">
                <button
                  type="button"
                  onClick={() => setReconcileModalRecId(null)}
                  className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
                >
                  Keep Reservation Held
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold"
                >
                  Authorize & Release Capacity
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
};
