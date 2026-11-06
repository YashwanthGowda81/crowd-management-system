import React, { useState } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { GlassCard } from '../components/GlassCard';
import { 
  User, 
  Shield, 
  Key, 
  Calendar, 
  CheckCircle, 
  AlertCircle, 
  Sliders, 
  ArrowRight, 
  Award, 
  Lock,
  Save,
  RotateCcw
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const { user, updateUserProfile, activeEventObj, currentEvent, cameras } = useCrowdSystem();

  const [name, setName] = useState(user?.name || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'OP';

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setMessage({ type: 'error', text: 'Name cannot be empty.' });
      return;
    }
    setIsSaving(true);
    setMessage(null);
    const res = await updateUserProfile({ name: name.trim() });
    setIsSaving(false);
    if (res.success) {
      setMessage({ type: 'success', text: res.message || 'Profile information updated successfully.' });
      setIsEditing(false);
    } else {
      setMessage({ type: 'error', text: res.error || 'Failed to update profile.' });
    }
  };

  const handleCancel = () => {
    setName(user?.name || '');
    setIsEditing(false);
    setMessage(null);
  };

  return (
    <div className="space-y-8 pb-16 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border/40 pb-6">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
            <User className="w-4 h-4" />
            <span>OPERATOR CREDENTIALS & IDENTITY</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            My Operator Profile
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Official surveillance clearance, authenticated operator credentials, and command responsibilities.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/officer-control')}
            className="px-4 py-2.5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-400 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <Sliders className="w-4 h-4" />
            <span>Officer Control Panel ➔</span>
          </button>
          <button
            onClick={() => navigate('/account-settings')}
            className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <Key className="w-4 h-4 text-cyan-400" />
            <span>Security & Password</span>
          </button>
        </div>
      </div>

      {/* Status Notifications */}
      {message && (
        <div className={`p-4 rounded-xl border flex items-center gap-3 text-xs font-semibold animate-fadeIn ${
          message.type === 'success' 
            ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' 
            : 'bg-red-950/40 border-red-500/40 text-red-300'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Main Profile Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: ID Badge & Overview (Col 4) */}
        <div className="lg:col-span-4 space-y-6">
          <GlassCard className="p-6 border-cyan-500/30 text-center relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" />

            {/* Avatar Circle */}
            <div className="w-24 h-24 mx-auto rounded-2xl bg-gradient-to-br from-cyan-950 to-slate-950 border-2 border-cyan-500/50 flex items-center justify-center text-3xl font-extrabold text-cyan-400 shadow-[0_0_25px_rgba(6,182,212,0.25)] mb-4">
              {initials}
            </div>

            <h2 className="text-xl font-bold text-white tracking-tight">{user?.name || 'Operator'}</h2>
            <p className="text-xs text-slate-400 mt-0.5">{user?.email || 'operator@surveillance.gov'}</p>

            <div className="mt-3 flex items-center justify-center gap-2">
              <span className="px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-[10px] font-mono font-bold uppercase tracking-wider">
                {user?.role || 'Surveillance Operator'}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-400 text-[10px] font-mono font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Active Duty
              </span>
            </div>

            <div className="mt-6 pt-6 border-t border-slate-900 text-left space-y-3 font-mono text-xs">
              <div className="flex justify-between items-center text-slate-400">
                <span>Operator ID:</span>
                <span className="text-cyan-300 font-bold">OP-{user?.id ? String(user.id).padStart(4, '0') : '0001'}</span>
              </div>
              <div className="flex justify-between items-center text-slate-400">
                <span>Auth Protocol:</span>
                <span className="text-slate-200">JWT Bearer (HS256)</span>
              </div>
              <div className="flex justify-between items-center text-slate-400">
                <span>Assigned Event:</span>
                <span className="text-cyan-300 font-bold truncate max-w-[140px]" title={activeEventObj?.title || currentEvent}>
                  {activeEventObj?.title || currentEvent || 'Active System'}
                </span>
              </div>
              <div className="flex justify-between items-center text-slate-400">
                <span>Monitored Feeds:</span>
                <span className="text-slate-200">{cameras.length} Active Streams</span>
              </div>
            </div>
          </GlassCard>

          {/* Quick Shortcuts */}
          <GlassCard className="p-5 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">Quick Navigation</h3>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/my-event')}
                className="w-full p-2.5 rounded-lg bg-slate-950/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/30 text-left flex items-center justify-between text-xs text-slate-300 hover:text-white transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <Calendar className="w-4 h-4 text-cyan-400" />
                  <span>My Active Event</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition-transform group-hover:translate-x-1" />
              </button>

              <button
                onClick={() => navigate('/officer-control')}
                className="w-full p-2.5 rounded-lg bg-slate-950/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/30 text-left flex items-center justify-between text-xs text-slate-300 hover:text-white transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <Sliders className="w-4 h-4 text-cyan-400" />
                  <span>Officer Control Panel</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition-transform group-hover:translate-x-1" />
              </button>

              <button
                onClick={() => navigate('/account-settings')}
                className="w-full p-2.5 rounded-lg bg-slate-950/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/30 text-left flex items-center justify-between text-xs text-slate-300 hover:text-white transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <Key className="w-4 h-4 text-cyan-400" />
                  <span>Account & Password</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition-transform group-hover:translate-x-1" />
              </button>
            </div>
          </GlassCard>
        </div>

        {/* Right Column: Editable Profile & Clearances (Col 8) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Identity & Profile Editing Form */}
          <GlassCard className="p-6 space-y-6 border-cyan-500/20">
            <div className="flex items-center justify-between border-b border-slate-900 pb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Shield className="w-4 h-4 text-cyan-400" />
                  <span>Profile Information</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  View and update your official operator name displayed on audit logs and dispatcher logs.
                </p>
              </div>

              {!isEditing && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-cyan-400 text-xs font-bold transition-all"
                >
                  Edit Profile
                </button>
              )}
            </div>

            <form onSubmit={handleSave} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Full Name
                  </label>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className={`w-full px-3.5 py-2.5 rounded-xl border font-sans text-xs transition-all ${
                      isEditing
                        ? 'bg-slate-950 border-cyan-500/50 text-white focus:outline-none focus:ring-1 focus:ring-cyan-500'
                        : 'bg-slate-900/60 border-slate-800/80 text-slate-300 cursor-not-allowed'
                    }`}
                  />
                  <span className="text-[10px] text-slate-500 font-mono">
                    Official name attached to critical emergency dispatches and alert resolutions.
                  </span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Email Address
                  </label>
                  <input
                    type="email"
                    disabled
                    value={user?.email || 'operator@surveillance.gov'}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-slate-400 cursor-not-allowed text-xs font-mono"
                  />
                  <span className="text-[10px] text-slate-500 font-mono">
                    Primary authentication identity. Cannot be changed without administrator approval.
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Assigned Role
                  </label>
                  <div className="px-3.5 py-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-cyan-300 font-bold font-mono text-xs flex items-center justify-between">
                    <span>{user?.role || 'Surveillance Operator'}</span>
                    <Lock className="w-3.5 h-3.5 text-slate-500" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Account Status
                  </label>
                  <div className="px-3.5 py-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-emerald-400 font-bold font-mono text-xs flex items-center justify-between">
                    <span>Active & Verified</span>
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                  </div>
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
                    <span>{isSaving ? 'Saving...' : 'Save Profile Changes'}</span>
                  </button>
                </div>
              )}
            </form>
          </GlassCard>

          {/* Operational Clearances & Security Matrix */}
          <GlassCard className="p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Award className="w-4 h-4 text-cyan-400" />
              <span>Surveillance Clearances & Access Matrix</span>
            </h3>
            <p className="text-xs text-slate-400">
              Your role has been verified for high-priority operational surveillance capabilities.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 font-mono text-xs">
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-white">Live Multi-Camera Surveillance</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">Clearance to view, record, and control live camera streams & RTSP feeds.</p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-white">Emergency Dispatch Clearance</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">Authority to approve and dispatch Police, Medical, and Fire services.</p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-white">AI Inference Module Tuning</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">Authorization to toggle YOLOv8 detection and density thresholds.</p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-white">Audit & Forensic Reporting</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">Clearance to generate and download comprehensive incident PDF reports.</p>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
};
