import React, { useState } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { GlassCard } from '../components/GlassCard';
import { 
  Key, 
  Lock, 
  ShieldCheck, 
  LogOut, 
  CheckCircle, 
  AlertCircle, 
  Eye, 
  EyeOff, 
  Save, 
  RotateCcw,
  User,
  Sliders,
  Calendar,
  ArrowRight,
  Shield,
  Fingerprint
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const AccountSettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout, updateUserProfile, updateSettings, activeEventObj, currentEvent } = useCrowdSystem();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'OP';

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMessage(null);

    if (!currentPassword) {
      setStatusMessage({ type: 'error', text: 'Please enter your current password.' });
      return;
    }
    if (newPassword.length < 8) {
      setStatusMessage({ type: 'error', text: 'New password must be at least 8 characters long.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setStatusMessage({ type: 'error', text: 'New password and confirmation password do not match.' });
      return;
    }

    setIsSaving(true);
    const res = await updateUserProfile({
      current_password: currentPassword,
      new_password: newPassword
    });
    setIsSaving(false);

    if (res.success) {
      setStatusMessage({
        type: 'success',
        text: 'Password updated successfully. Your credentials are securely updated.'
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } else {
      setStatusMessage({
        type: 'error',
        text: res.error || 'Failed to update password. Please check your current password.'
      });
    }
  };

  const handleCancelPassword = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setStatusMessage(null);
  };

  const handleResetPreferences = () => {
    if (window.confirm('Reset all local appearance and layout preferences to default? Your account credentials and event configurations will remain untouched.')) {
      updateSettings({
        theme: 'dark',
        timezone: 'Local',
        timeFormat: '12h',
        accentColor: 'cyan',
        compactMode: false,
        sidebarCollapsedDefault: false,
        tablePageSize: 10,
        defaultCameraGrid: '2x2',
        showFpsOverlay: true,
        showTrackIds: true,
        desktopNotifications: true,
        highContrast: false,
        fontSize: 'md',
        reducedMotion: false
      });
      setStatusMessage({
        type: 'success',
        text: 'Local application display preferences have been reset to default values.'
      });
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/', { replace: true });
  };

  return (
    <div className="space-y-8 pb-16 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border/40 pb-6">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
            <Key className="w-4 h-4" />
            <span>SECURITY, PRIVACY & CREDENTIAL MANAGEMENT</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Account & Security Settings
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Manage your credentials, update your access password, configure active session parameters, and review security clearance.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => navigate('/profile')}
            className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <User className="w-4 h-4 text-cyan-400" />
            <span>My Profile</span>
          </button>

          <button
            onClick={() => navigate('/officer-control')}
            className="px-4 py-2.5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-400 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <Sliders className="w-4 h-4" />
            <span>Officer Control Panel ➔</span>
          </button>

          <button
            onClick={handleLogout}
            className="px-4 py-2.5 rounded-xl bg-red-950/60 hover:bg-red-900/60 border border-red-500/30 text-red-300 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2"
          >
            <LogOut className="w-4 h-4 text-red-400" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Status Notifications */}
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

      {/* Main Grid: Matching 12-Column Layout of ProfilePage */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Security & Identity Badge + Shortcuts (Col 4) */}
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
                Active Session
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
                <span>Security Grade:</span>
                <span className="text-emerald-400 font-bold">Level 3 Enterprise</span>
              </div>
              <div className="flex justify-between items-center text-slate-400">
                <span>Assigned Event:</span>
                <span className="text-cyan-300 font-bold truncate max-w-[140px]" title={activeEventObj?.title || currentEvent}>
                  {activeEventObj?.title || currentEvent || 'Active System'}
                </span>
              </div>
            </div>
          </GlassCard>

          {/* Quick Shortcuts */}
          <GlassCard className="p-5 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">Quick Navigation</h3>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/profile')}
                className="w-full p-2.5 rounded-lg bg-slate-950/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/30 text-left flex items-center justify-between text-xs text-slate-300 hover:text-white transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <User className="w-4 h-4 text-cyan-400" />
                  <span>My Operator Profile</span>
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
                onClick={() => navigate('/my-event')}
                className="w-full p-2.5 rounded-lg bg-slate-950/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/30 text-left flex items-center justify-between text-xs text-slate-300 hover:text-white transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <Calendar className="w-4 h-4 text-cyan-400" />
                  <span>My Active Event</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition-transform group-hover:translate-x-1" />
              </button>
            </div>
          </GlassCard>

          {/* Preferences Reset */}
          <GlassCard className="p-5 space-y-3 border-slate-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-amber-400" />
              <span>Reset Display Preferences</span>
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              If client dashboard layout or appearance preferences become misaligned, safely reset display options to defaults without modifying credentials.
            </p>
            <button
              onClick={handleResetPreferences}
              className="mt-2 w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-amber-500/30 text-amber-300 font-bold text-xs flex items-center justify-center gap-2 transition-all"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Local Preferences</span>
            </button>
          </GlassCard>
        </div>

        {/* Right Column: Password Management & Security Parameters (Col 8) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Password Management Card */}
          <GlassCard className="p-6 space-y-6 border-cyan-500/20">
            <div className="border-b border-slate-900 pb-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Lock className="w-4 h-4 text-cyan-400" />
                <span>Change Operator Password</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Passwords are authenticated using SHA-256 / PBKDF2 hashing. Never disclose your surveillance credentials.
              </p>
            </div>

            <form onSubmit={handlePasswordChange} className="space-y-5 text-xs">
              {/* Current Password */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type={showCurrent ? 'text' : 'password'}
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500/50"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrent(!showCurrent)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    title={showCurrent ? "Hide password" : "Show password"}
                  >
                    {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* New Password & Confirm Password Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showNew ? 'text' : 'password'}
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      className="w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500/50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNew(!showNew)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                      title={showNew ? "Hide password" : "Show password"}
                    >
                      {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirm ? 'text' : 'password'}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter new password"
                      className="w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500/50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(!showConfirm)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                      title={showConfirm ? "Hide password" : "Show password"}
                    >
                      {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Password Guidelines */}
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 space-y-1 text-[11px] text-slate-400 font-mono">
                <div className="flex items-center gap-2 text-cyan-400 font-bold text-xs mb-1">
                  <Shield className="w-3.5 h-3.5" />
                  <span>Credential Requirements</span>
                </div>
                <p>• Must contain at least 8 characters (alphanumeric and symbols recommended).</p>
                <p>• Updating your password immediately invalidates active sessions on other terminals.</p>
                <p>• Password hashes are stored using PBKDF2 with unique cryptographic salt.</p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-900">
                {(currentPassword || newPassword || confirmPassword) && (
                  <button
                    type="button"
                    onClick={handleCancelPassword}
                    disabled={isSaving}
                    className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white font-bold transition-all flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Cancel</span>
                  </button>
                )}
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  <span>{isSaving ? 'Updating...' : 'Update Password'}</span>
                </button>
              </div>
            </form>
          </GlassCard>

          {/* Session Security & Privacy Parameters Matrix */}
          <GlassCard className="p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>Security Parameters & Active Session Safeguards</span>
            </h3>
            <p className="text-xs text-slate-400">
              Active cryptographic controls and authentication safeguards enforced for this operator session.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 font-mono text-xs">
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-white">Encrypted Bearer Authentication</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">HS256 signed JSON Web Tokens attached via Bearer authorization headers.</p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-white">Multi-Device Revocation</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">Password updates trigger instant token invalidation across all operator instances.</p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-white">Role-Based Route Isolation</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">Enforced least-privilege verification for live video streams and dispatch controls.</p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-white">Cryptographic Event Auditing</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">Emergency dispatches and critical threshold adjustments are logged with operator signatures.</p>
                </div>
              </div>
            </div>
          </GlassCard>

          {/* Terminal Security Verification */}
          <GlassCard className="p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Fingerprint className="w-4 h-4 text-cyan-400" />
              <span>Terminal Security Verification</span>
            </h3>
            <p className="text-xs text-slate-400">
              Verified attributes and cryptographic status of the current terminal session.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 font-mono text-xs">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 flex justify-between items-center">
                <span className="text-slate-400">Authenticated Email:</span>
                <span className="text-white font-bold truncate max-w-[170px]" title={user?.email || 'operator@surveillance.gov'}>
                  {user?.email || 'operator@surveillance.gov'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 flex justify-between items-center">
                <span className="text-slate-400">Security Clearance:</span>
                <span className="text-emerald-400 font-bold">Level 3 Enterprise</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 flex justify-between items-center">
                <span className="text-slate-400">Session Protocol:</span>
                <span className="text-slate-200">JWT / Bearer Encrypted</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 flex justify-between items-center">
                <span className="text-slate-400">Encryption Scheme:</span>
                <span className="text-cyan-300 font-bold">PBKDF2-SHA256 (Salted)</span>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
};

