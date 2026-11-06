import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { Calendar, Building, Users, AlertTriangle, Clock, ArrowRight, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';

export const EventSetup: React.FC = () => {
  const navigate = useNavigate();
  const { addEvent, onboardingStatus, user } = useCrowdSystem();

  // Form State
  const [title, setTitle] = useState('');
  const [venueName, setVenueName] = useState('Smart City Arena & Convention Center');
  const [capacity, setCapacity] = useState(5000);
  const [limits, setLimits] = useState(4200);
  const [staff, setStaff] = useState(30);
  const [risk, setRisk] = useState<'low' | 'medium' | 'high'>('medium');
  const [startTime, setStartTime] = useState('08:00 AM');
  const [endTime, setEndTime] = useState('10:00 PM');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // If manager already has an event configured, avoid duplicate creation
  useEffect(() => {
    if (onboardingStatus?.has_event) {
      if (onboardingStatus.has_source) {
        navigate('/dashboard', { replace: true });
      } else {
        navigate('/camera-setup', { replace: true });
      }
    }
  }, [onboardingStatus, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setErrorMsg('Event / Operation title is required.');
      return;
    }
    if (capacity <= 0) {
      setErrorMsg('Venue capacity must be greater than zero.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const newEvt = await addEvent({
        title: title.trim(),
        venue_name: venueName.trim() || 'Main Complex Arena',
        capacity: Number(capacity),
        limits: Number(limits) || Math.round(Number(capacity) * 0.85),
        staff: Number(staff) || 20,
        risk: risk,
        start: startTime,
        end: endTime,
        assignedCameras: []
      });

      if (newEvt) {
        navigate('/camera-setup', { replace: true });
      } else {
        navigate('/camera-setup', { replace: true });
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save event to database. Please retry.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-6 space-y-6">
      {/* Onboarding Workflow Steps Indicator */}
      <div className="flex items-center justify-between px-6 py-4 rounded-2xl bg-slate-900/80 border border-cyber-border/40 select-none">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 flex items-center justify-center font-bold text-xs">
            1
          </div>
          <div>
            <p className="text-xs font-bold text-cyan-400 uppercase tracking-wider">Step 1: Event Setup</p>
            <p className="text-[10px] text-slate-400">Define operation perimeter & capacity</p>
          </div>
        </div>

        <div className="h-0.5 w-12 bg-slate-800 hidden sm:block" />

        <div className="flex items-center gap-3 opacity-50">
          <div className="w-8 h-8 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center font-bold text-xs">
            2
          </div>
          <div className="hidden sm:block">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Step 2: Camera Setup</p>
            <p className="text-[10px] text-slate-500">Connect RTSP or upload video</p>
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

      {/* Main Glass Card Form */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="cyber-glass p-8 rounded-2xl border border-cyan-500/30 space-y-6"
      >
        <div className="flex items-start justify-between border-b border-cyber-border/40 pb-4">
          <div>
            <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono uppercase tracking-wider mb-1">
              <Calendar className="w-4 h-4" />
              <span>Operational Event Registration</span>
            </div>
            <h1 className="text-xl md:text-2xl font-extrabold text-white tracking-tight">
              Configure Surveillance Event
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Welcome, <strong className="text-slate-200">{user?.name || 'Operator'}</strong>. Set up your security operation context to establish physical zone boundaries, capacity thresholds, and AI surveillance scoping.
            </p>
          </div>

          <div className="p-2.5 rounded-xl bg-cyan-950/40 border border-cyan-500/30 text-cyan-400 hidden sm:block">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>

        {errorMsg && (
          <div className="p-3.5 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-medium flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Event Title */}
            <div className="space-y-1.5 md:col-span-2">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Operation / Event Title <span className="text-cyan-400">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Metro Tech Summit 2026 / Stadium Security Command"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 transition-colors text-xs"
              />
              <span className="text-[10px] text-slate-500">A clear, identifiable operational name for this surveillance zone.</span>
            </div>

            {/* Venue Name */}
            <div className="space-y-1.5 md:col-span-2">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Venue / Facility Complex
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Building className="w-4 h-4" />
                </span>
                <input
                  type="text"
                  placeholder="e.g. Smart City Arena & Convention Center"
                  value={venueName}
                  onChange={(e) => setVenueName(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 transition-colors text-xs"
                />
              </div>
            </div>

            {/* Capacity */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Venue Max Capacity
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Users className="w-4 h-4" />
                </span>
                <input
                  type="number"
                  min="50"
                  max="500000"
                  required
                  value={capacity}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setCapacity(val);
                    setLimits(Math.round(val * 0.85));
                  }}
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs font-mono"
                />
              </div>
              <span className="text-[10px] text-slate-500">Physical maximum allowable occupants.</span>
            </div>

            {/* Limits */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Surge Warning Threshold (Limits)
              </label>
              <input
                type="number"
                min="10"
                max={capacity}
                required
                value={limits}
                onChange={(e) => setLimits(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs font-mono"
              />
              <span className="text-[10px] text-slate-500">Crowd count that triggers critical alert escalation (default 85%).</span>
            </div>

            {/* Security Staff */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Active Security Squads
              </label>
              <input
                type="number"
                min="1"
                max="1000"
                value={staff}
                onChange={(e) => setStaff(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs font-mono"
              />
              <span className="text-[10px] text-slate-500">Initial deployed field security personnel count.</span>
            </div>

            {/* Risk Assessment */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Baseline Risk Assessment
              </label>
              <select
                value={risk}
                onChange={(e) => setRisk(e.target.value as any)}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs cursor-pointer"
              >
                <option value="low">Low Risk — Standard Protocol</option>
                <option value="medium">Medium Risk — Enhanced Awareness</option>
                <option value="high">High Risk — Strict Perimeter Defense</option>
              </select>
              <span className="text-[10px] text-slate-500">Configures baseline YOLO alert and density thresholds.</span>
            </div>

            {/* Schedule Start */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Operation Start Time / Date
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Clock className="w-4 h-4" />
                </span>
                <input
                  type="text"
                  placeholder="e.g. 08:00 AM"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs"
                />
              </div>
            </div>

            {/* Schedule End */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Operation Conclude Time / Date
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Clock className="w-4 h-4" />
                </span>
                <input
                  type="text"
                  placeholder="e.g. 10:00 PM"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-950 border border-cyber-border rounded-xl text-white focus:outline-none focus:border-cyan-500/60 transition-colors text-xs"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-cyber-border/40 flex items-center justify-between">
            <span className="text-[10px] text-slate-400">
              * Event will be bound to manager account: <strong className="text-slate-300">{user?.email}</strong>
            </span>

            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-extrabold text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-[0_0_16px_rgba(6,182,212,0.3)] disabled:opacity-50"
            >
              <span>{isSubmitting ? 'Creating Event...' : 'Save & Continue to Camera Setup'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};
