import React, { useState, useEffect } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { GlassCard } from '../components/GlassCard';
import { 
  Calendar, 
  Building, 
  Users, 
  ShieldAlert, 
  Camera, 
  CheckCircle, 
  AlertCircle, 
  Save, 
  RotateCcw,
  Layers,
  Settings
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const MyEventPage: React.FC = () => {
  const navigate = useNavigate();
  const { 
    events, 
    selectedEventId, 
    onboardingStatus, 
    updateEvent, 
    cameras 
  } = useCrowdSystem();

  const activeEvent = events.find(e => e.id === selectedEventId) || onboardingStatus?.event;

  const [title, setTitle] = useState('');
  const [venueName, setVenueName] = useState('');
  const [capacity, setCapacity] = useState(5000);
  const [limits, setLimits] = useState(4200);
  const [staff, setStaff] = useState(25);
  const [risk, setRisk] = useState<'low' | 'medium' | 'high'>('medium');
  const [start, setStart] = useState('08:00 AM');
  const [end, setEnd] = useState('10:00 PM');

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Sync state with active event
  useEffect(() => {
    if (activeEvent) {
      setTitle(activeEvent.title || '');
      setVenueName(activeEvent.venueName || 'Main Arena Complex');
      setCapacity(activeEvent.capacity || 5000);
      setLimits(activeEvent.limits || Math.round((activeEvent.capacity || 5000) * 0.85));
      setStaff(activeEvent.staff || 20);
      setRisk(activeEvent.risk || 'medium');
      setStart(activeEvent.start || '08:00 AM');
      setEnd(activeEvent.end || '10:00 PM');
    }
  }, [activeEvent]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeEvent) {
      setStatusMessage({ type: 'error', text: 'No active event found to update.' });
      return;
    }
    if (!title.trim()) {
      setStatusMessage({ type: 'error', text: 'Event title is required.' });
      return;
    }

    const numCap = Number(capacity);
    if (isNaN(numCap) || numCap <= 0 || !Number.isInteger(numCap)) {
      setStatusMessage({ type: 'error', text: 'Venue capacity must be a valid positive whole number greater than 0.' });
      return;
    }
    if (numCap > 1000000) {
      setStatusMessage({ type: 'error', text: 'Venue capacity exceeds maximum system limit (1,000,000).' });
      return;
    }
    const numLimits = Number(limits) > 0 ? Number(limits) : Math.round(numCap * 0.85);

    setIsSaving(true);
    setStatusMessage(null);
    try {
      await updateEvent(activeEvent.id, {
        title: title.trim(),
        venue_name: venueName.trim(),
        capacity: numCap,
        limits: numLimits,
        staff: Number(staff),
        risk,
        start,
        end
      });
      setStatusMessage({ type: 'success', text: `Venue capacity (${numCap.toLocaleString()}) and event specifications confirmed and saved.` });
      setIsEditing(false);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || err.message || 'Failed to update event configuration.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    if (activeEvent) {
      setTitle(activeEvent.title || '');
      setVenueName(activeEvent.venueName || 'Main Arena Complex');
      setCapacity(activeEvent.capacity || 5000);
      setLimits(activeEvent.limits || 4200);
      setStaff(activeEvent.staff || 20);
      setRisk(activeEvent.risk || 'medium');
      setStart(activeEvent.start || '08:00 AM');
      setEnd(activeEvent.end || '10:00 PM');
    }
    setIsEditing(false);
    setStatusMessage(null);
  };

  const assignedCameras = cameras.filter(c => !c.eventId || c.eventId === activeEvent?.id);

  return (
    <div className="space-y-8 pb-16 max-w-6xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border/40 pb-6">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
            <Calendar className="w-4 h-4" />
            <span>OPERATIONAL EVENT PROFILE & VENUE LIMITS</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            My Event Management
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Configure venue boundaries, capacity thresholds, security staffing, and strict event isolation parameters.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/cameras')}
            className="px-4 py-2.5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-400 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <Camera className="w-4 h-4" />
            <span>Configure Cameras ➔</span>
          </button>
          <button
            onClick={() => navigate('/venue-architecture')}
            className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>Venue Architecture</span>
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {statusMessage && (
        <div className={`p-4 rounded-xl border flex items-center gap-3 text-xs font-semibold animate-fadeIn ${
          statusMessage.type === 'success' 
            ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' 
            : 'bg-red-950/40 border-red-500/40 text-red-300'
        }`}>
          {statusMessage.type === 'success' ? (
            <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <GlassCard className="p-4 border-cyan-500/20 font-mono">
          <div className="flex items-center gap-2 text-cyan-400 text-xs mb-1">
            <Users className="w-4 h-4" />
            <span>Max Capacity</span>
          </div>
          <p className="text-2xl font-extrabold text-white">{capacity.toLocaleString()}</p>
          <p className="text-[10px] text-slate-400 mt-1">Design venue occupancy</p>
        </GlassCard>

        <GlassCard className="p-4 border-cyan-500/20 font-mono">
          <div className="flex items-center gap-2 text-yellow-400 text-xs mb-1">
            <ShieldAlert className="w-4 h-4" />
            <span>Safety Limit</span>
          </div>
          <p className="text-2xl font-extrabold text-yellow-300">{limits.toLocaleString()}</p>
          <p className="text-[10px] text-slate-400 mt-1">Warning threshold (85%)</p>
        </GlassCard>

        <GlassCard className="p-4 border-cyan-500/20 font-mono">
          <div className="flex items-center gap-2 text-emerald-400 text-xs mb-1">
            <Users className="w-4 h-4" />
            <span>Security Personnel</span>
          </div>
          <p className="text-2xl font-extrabold text-emerald-300">{staff} Officers</p>
          <p className="text-[10px] text-slate-400 mt-1">Dedicated command guards</p>
        </GlassCard>

        <GlassCard className="p-4 border-cyan-500/20 font-mono">
          <div className="flex items-center gap-2 text-cyan-400 text-xs mb-1">
            <Camera className="w-4 h-4" />
            <span>Camera Feeds</span>
          </div>
          <p className="text-2xl font-extrabold text-cyan-300">{assignedCameras.length} Active</p>
          <p className="text-[10px] text-slate-400 mt-1">Isolated surveillance inputs</p>
        </GlassCard>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Event Details & Edit Form (Col 8) */}
        <div className="lg:col-span-8 space-y-6">
          <GlassCard className="p-6 space-y-6 border-cyan-500/30">
            <div className="flex items-center justify-between border-b border-slate-900 pb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Building className="w-4 h-4 text-cyan-400" />
                  <span>Event Configuration Specifications</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Settings are strictly isolated to your event and synchronized across all surveillance dashboards.
                </p>
              </div>

              {!isEditing && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-cyan-400 text-xs font-bold transition-all"
                >
                  Edit Specifications
                </button>
              )}
            </div>

            <form onSubmit={handleSave} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Event Title
                  </label>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Metro Stadium Grand Championship"
                    className={`w-full px-3.5 py-2.5 rounded-xl border text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none focus:ring-1 focus:ring-cyan-500'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 cursor-not-allowed'
                    }`}
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Venue Complex Name
                  </label>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={venueName}
                    onChange={(e) => setVenueName(e.target.value)}
                    placeholder="e.g. Olympic Arena Hall 4"
                    className={`w-full px-3.5 py-2.5 rounded-xl border text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none focus:ring-1 focus:ring-cyan-500'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 cursor-not-allowed'
                    }`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Maximum Capacity
                  </label>
                  <input
                    type="number"
                    disabled={!isEditing}
                    value={capacity}
                    onChange={(e) => {
                      const val = parseInt(e.target.value) || 0;
                      setCapacity(val);
                      if (isEditing) setLimits(Math.round(val * 0.85));
                    }}
                    className={`w-full px-3.5 py-2.5 rounded-xl border font-mono text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 cursor-not-allowed'
                    }`}
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Warning Threshold
                  </label>
                  <input
                    type="number"
                    disabled={!isEditing}
                    value={limits}
                    onChange={(e) => setLimits(parseInt(e.target.value) || 0)}
                    className={`w-full px-3.5 py-2.5 rounded-xl border font-mono text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 cursor-not-allowed'
                    }`}
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Security Staff
                  </label>
                  <input
                    type="number"
                    disabled={!isEditing}
                    value={staff}
                    onChange={(e) => setStaff(parseInt(e.target.value) || 0)}
                    className={`w-full px-3.5 py-2.5 rounded-xl border font-mono text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 cursor-not-allowed'
                    }`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Risk Assessment Level
                  </label>
                  <select
                    disabled={!isEditing}
                    value={risk}
                    onChange={(e) => setRisk(e.target.value as any)}
                    className={`w-full px-3.5 py-2.5 rounded-xl border font-mono text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 cursor-not-allowed'
                    }`}
                  >
                    <option value="low">Low Risk (Standard Venue)</option>
                    <option value="medium">Medium Risk (Dense Gathering)</option>
                    <option value="high">High Risk (Surge Vulnerable)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Start Operational Window
                  </label>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                    placeholder="08:00 AM"
                    className={`w-full px-3.5 py-2.5 rounded-xl border font-mono text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 cursor-not-allowed'
                    }`}
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    End Operational Window
                  </label>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                    placeholder="10:00 PM"
                    className={`w-full px-3.5 py-2.5 rounded-xl border font-mono text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 cursor-not-allowed'
                    }`}
                  />
                </div>
              </div>

              {isEditing && (
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-900">
                  <button
                    type="button"
                    onClick={handleCancel}
                    disabled={isSaving}
                    className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white font-bold transition-all flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Cancel</span>
                  </button>
                  <button
                    type="submit"
                    disabled={isSaving}
                    className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] flex items-center gap-1.5"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{isSaving ? 'Saving...' : 'Save Configuration'}</span>
                  </button>
                </div>
              )}
            </form>
          </GlassCard>
        </div>

        {/* Right Side: Associated Feeds & Isolation Information (Col 4) */}
        <div className="lg:col-span-4 space-y-6">
          <GlassCard className="p-6 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <Camera className="w-4 h-4 text-cyan-400" />
              <span>Assigned Camera Feeds</span>
            </h3>
            <p className="text-xs text-slate-400">
              Only cameras attached to this event ID are processed and aggregated into crowd metrics.
            </p>

            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {assignedCameras.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs">
                  No cameras assigned yet.
                </div>
              ) : (
                assignedCameras.map(cam => (
                  <div 
                    key={cam.id} 
                    className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 flex items-center justify-between text-xs"
                  >
                    <div className="space-y-0.5">
                      <p className="font-bold text-white truncate max-w-[160px]">{cam.name}</p>
                      <p className="text-[10px] text-slate-500">{cam.location}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                      cam.status === 'online' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' : 'bg-slate-900 text-slate-500'
                    }`}>
                      {cam.status}
                    </span>
                  </div>
                ))
              )}
            </div>

            <button
              onClick={() => navigate('/cameras')}
              className="w-full mt-2 py-2.5 rounded-xl bg-cyan-950/50 hover:bg-cyan-900/50 border border-cyan-500/30 text-cyan-400 font-bold text-xs flex items-center justify-center gap-1.5 transition-all"
            >
              <Settings className="w-3.5 h-3.5" />
              <span>Manage Feeds in Camera Access ➔</span>
            </button>
          </GlassCard>

          {/* Strict Isolation Notice */}
          <GlassCard className="p-5 border-slate-800 space-y-3 font-mono text-xs">
            <div className="flex items-center gap-2 text-cyan-400 font-bold">
              <ShieldAlert className="w-4 h-4" />
              <span>Event Data Isolation</span>
            </div>
            <p className="text-[10px] text-slate-400 leading-relaxed">
              In accordance with enterprise surveillance standards, each event operates within a hermetic sandbox. Cameras, incident reports, density graphs, and alerts cannot leak across boundaries.
            </p>
          </GlassCard>
        </div>
      </div>
    </div>
  );
};
