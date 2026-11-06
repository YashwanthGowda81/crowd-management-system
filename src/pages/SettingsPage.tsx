import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { GlassCard } from '../components/GlassCard';
import { 
  Sliders, 
  Monitor, 
  Layout, 
  User, 
  Shield, 
  Bell, 
  Eye, 
  Info, 
  Check, 
  AlertCircle, 
  Save, 
  RotateCcw,
  Moon,
  Sun,
  Laptop,
  CheckCircle
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { settings, updateSettings, user, hardwareInfo, cameras, selectedEventId } = useCrowdSystem();

  const activeTab = searchParams.get('tab') || 'general';
  const setActiveTab = (tab: string) => {
    setSearchParams({ tab });
    setStatusMessage(null);
  };

  // Local draft state for form controls with dirty-state detection
  const [draft, setDraft] = useState({ ...settings });
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Sync draft when settings change from outside (e.g. initial load)
  useEffect(() => {
    setDraft({ ...settings });
    setIsDirty(false);
  }, [settings]);

  const updateDraft = (partial: Partial<typeof draft>) => {
    setDraft(prev => {
      const next = { ...prev, ...partial };
      setIsDirty(true);
      return next;
    });
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsSaving(true);
    setStatusMessage(null);
    try {
      await updateSettings(draft);
      setIsDirty(false);
      setStatusMessage({
        type: 'success',
        text: 'System settings and user preferences saved and applied across the application.'
      });
      setTimeout(() => setStatusMessage(null), 5000);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to save settings.'
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    setDraft({ ...settings });
    setIsDirty(false);
    setStatusMessage(null);
  };

  const handleResetDefaults = () => {
    if (window.confirm('Reset all parameters in this view to system defaults?')) {
      const defaults = {
        aiSensitivity: 75,
        crowdThreshold: 85,
        soundAlerts: true,
        autoEscalation: false,
        language: 'English',
        theme: 'dark' as const,
        defaultLandingPage: '/dashboard',
        timezone: 'Local',
        timeFormat: '12h' as const,
        accentColor: 'cyan' as const,
        sidebarCollapsedDefault: false,
        compactMode: false,
        tablePageSize: 10,
        defaultCameraGrid: '2x2' as const,
        showFpsOverlay: true,
        showTrackIds: true,
        desktopNotifications: true,
        highContrast: false,
        fontSize: 'md' as const,
        reducedMotion: false
      };
      setDraft(defaults);
      setIsDirty(true);
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Sliders, desc: 'Display, landing page, timezone' },
    { id: 'appearance', label: 'Appearance', icon: Monitor, desc: 'Theme, colors, layout density' },
    { id: 'preferences', label: 'Preferences', icon: Layout, desc: 'Camera grid, tables, overlays' },
    { id: 'account', label: 'Account Settings', icon: User, desc: 'Operator identity & password' },
    { id: 'security', label: 'Privacy & Security', icon: Shield, desc: 'Audit logging & active session' },
    { id: 'notifications', label: 'Notifications', icon: Bell, desc: 'Alert sounds & escalation' },
    { id: 'accessibility', label: 'Accessibility', icon: Eye, desc: 'High contrast & text scaling' },
    { id: 'about', label: 'About & System Info', icon: Info, desc: 'Version, hardware & engine' },
  ];

  return (
    <div className="space-y-6 pb-20 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border/40 pb-5">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
            <Sliders className="w-4 h-4" />
            <span>GLOBAL CONFIGURATION & USER PREFERENCES</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Surveillance System Settings
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Configure application display preferences, computer vision sensitivity thresholds, emergency escalation rules, and enterprise settings.
          </p>
        </div>

        {/* Global Save/Discard Header Actions */}
        <div className="flex items-center gap-3">
          {isDirty && (
            <span className="text-[11px] font-mono font-bold text-amber-400 bg-amber-950/40 border border-amber-500/30 px-3 py-1.5 rounded-lg flex items-center gap-1.5 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Unsaved changes
            </span>
          )}

          <button
            onClick={handleDiscard}
            disabled={!isDirty || isSaving}
            className={`px-4 py-2 rounded-xl text-xs font-bold font-mono transition-all border ${
              isDirty 
                ? 'bg-slate-900 border-slate-700 text-slate-300 hover:text-white' 
                : 'bg-slate-900/40 border-slate-900 text-slate-600 cursor-not-allowed'
            }`}
          >
            Discard
          </button>

          <button
            onClick={() => handleSave()}
            disabled={!isDirty || isSaving}
            className={`px-5 py-2 rounded-xl text-xs font-bold font-mono uppercase tracking-wider transition-all flex items-center gap-1.5 shadow-lg ${
              isDirty 
                ? 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-600/30' 
                : 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed'
            }`}
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
          </button>
        </div>
      </div>

      {/* Status Notifications Banner */}
      {statusMessage && (
        <div className={`p-4 rounded-xl border flex items-center justify-between text-xs font-semibold animate-fadeIn ${
          statusMessage.type === 'success' 
            ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' 
            : 'bg-red-950/40 border-red-500/40 text-red-300'
        }`}>
          <div className="flex items-center gap-2.5">
            {statusMessage.type === 'success' ? (
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button 
            onClick={() => setStatusMessage(null)}
            className="text-slate-400 hover:text-white ml-4 font-mono text-[10px]"
          >
            ✕ Dismiss
          </button>
        </div>
      )}

      {/* Main Settings Layout: Left Nav Tabs (Col 4) + Right Content Panel (Col 8) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Navigation Sidebar Tabs */}
        <div className="lg:col-span-4 space-y-2">
          <GlassCard className="p-2 space-y-1 border-slate-800">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full p-3 rounded-xl text-left flex items-start gap-3 transition-all ${
                    isActive
                      ? 'bg-cyan-950/70 border border-cyan-500/40 text-cyan-300 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                      : 'hover:bg-slate-900/60 border border-transparent text-slate-400 hover:text-white'
                  }`}
                >
                  <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                  <div className="min-w-0">
                    <span className="font-bold text-xs block text-white">{tab.label}</span>
                    <span className="text-[10px] text-slate-500 block truncate">{tab.desc}</span>
                  </div>
                </button>
              );
            })}
          </GlassCard>

          <GlassCard className="p-4 border-slate-800/80 space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center text-slate-400 text-[11px]">
              <span>Operator Role:</span>
              <span className="text-cyan-300 font-bold">{user?.role || 'Surveillance Operator'}</span>
            </div>
            <div className="flex justify-between items-center text-slate-400 text-[11px]">
              <span>Active Event ID:</span>
              <span className="text-slate-300 truncate max-w-[140px]">{selectedEventId || 'Global'}</span>
            </div>
            <button
              onClick={handleResetDefaults}
              className="w-full mt-2 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white text-[10px] font-bold flex items-center justify-center gap-1.5 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset All to Defaults</span>
            </button>
          </GlassCard>
        </div>

        {/* Content Panel */}
        <div className="lg:col-span-8 space-y-6">
          <GlassCard className="p-6 space-y-6 border-cyan-500/20">
            
            {/* 1. GENERAL SETTINGS */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div className="border-b border-slate-900 pb-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Sliders className="w-5 h-5 text-cyan-400" />
                    <span>General Application Preferences</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Control default landing pages, timezones, clock formatting, and computer vision thresholds.
                  </p>
                </div>

                {/* Default Landing Page */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-300 block font-mono">
                    Default Landing Page
                  </label>
                  <p className="text-[10px] text-slate-500 font-mono">
                    Screen opened upon completing login or clicking the brand header logo.
                  </p>
                  <select
                    value={draft.defaultLandingPage}
                    onChange={(e) => updateDraft({ defaultLandingPage: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono text-xs focus:outline-none focus:border-cyan-500/50"
                  >
                    <option value="/dashboard">Surveillance Dashboard (/dashboard)</option>
                    <option value="/live">Live Camera Monitoring Grid (/live)</option>
                    <option value="/officer-control">Central Officer Control Panel (/officer-control)</option>
                    <option value="/cameras">Camera Access & Health (/cameras)</option>
                  </select>
                </div>

                {/* Timezone and Clock Format */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-slate-300 block font-mono">
                      System Timezone
                    </label>
                    <select
                      value={draft.timezone}
                      onChange={(e) => updateDraft({ timezone: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono text-xs focus:outline-none focus:border-cyan-500/50"
                    >
                      <option value="Local">Local Host Browser Timezone</option>
                      <option value="UTC">Universal Coordinated Time (UTC)</option>
                      <option value="Asia/Kolkata">Asia/Kolkata (IST +05:30)</option>
                      <option value="America/New_York">America/New_York (EST/EDT)</option>
                      <option value="Europe/London">Europe/London (GMT/BST)</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-bold text-slate-300 block font-mono">
                      Clock Display Format
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => updateDraft({ timeFormat: '12h' })}
                        className={`py-2 px-3 rounded-xl border text-xs font-mono font-bold transition-all ${
                          draft.timeFormat === '12h'
                            ? 'bg-cyan-950/60 border-cyan-500 text-cyan-300'
                            : 'bg-slate-950 border-slate-800 text-slate-400'
                        }`}
                      >
                        12-Hour (AM/PM)
                      </button>
                      <button
                        type="button"
                        onClick={() => updateDraft({ timeFormat: '24h' })}
                        className={`py-2 px-3 rounded-xl border text-xs font-mono font-bold transition-all ${
                          draft.timeFormat === '24h'
                            ? 'bg-cyan-950/60 border-cyan-500 text-cyan-300'
                            : 'bg-slate-950 border-slate-800 text-slate-400'
                        }`}
                      >
                        24-Hour (Military)
                      </button>
                    </div>
                  </div>
                </div>

                {/* Computer Vision Thresholds (Server Persisted) */}
                <div className="pt-4 border-t border-slate-900 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                        YOLO Model Confidence Threshold
                      </h3>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                        Synchronized with backend WebSocket detection filtering (Database-persisted).
                      </p>
                    </div>
                    <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950/50 border border-cyan-500/30 px-2.5 py-1 rounded-lg">
                      {draft.aiSensitivity}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="95"
                    value={draft.aiSensitivity}
                    onChange={(e) => updateDraft({ aiSensitivity: parseInt(e.target.value) })}
                    className="w-full accent-cyan-500"
                  />
                </div>

                <div className="pt-2 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                        Crowd Density Warning Limit
                      </h3>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                        Triggers visual amber/red surge indicators on video overlays.
                      </p>
                    </div>
                    <span className="text-xs font-mono font-bold text-yellow-400 bg-yellow-950/50 border border-yellow-500/30 px-2.5 py-1 rounded-lg">
                      {draft.crowdThreshold}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="60"
                    max="95"
                    value={draft.crowdThreshold}
                    onChange={(e) => updateDraft({ crowdThreshold: parseInt(e.target.value) })}
                    className="w-full accent-yellow-500"
                  />
                </div>
              </div>
            )}

            {/* 2. APPEARANCE SETTINGS */}
            {activeTab === 'appearance' && (
              <div className="space-y-6">
                <div className="border-b border-slate-900 pb-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Monitor className="w-5 h-5 text-cyan-400" />
                    <span>Appearance & Theme System</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Theme changes apply immediately across sidebar, top navigation, dashboard cards, and surveillance views.
                  </p>
                </div>

                {/* Theme Selector */}
                <div className="space-y-3">
                  <label className="text-xs font-bold text-slate-300 block font-mono">
                    Application Theme Mode
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
                    {[
                      { id: 'dark', label: 'Dark Cyber', icon: Moon, desc: 'Enterprise surveillance high-tech dark interface' },
                      { id: 'light', label: 'Light Clean', icon: Sun, desc: 'High-contrast light mode for bright control rooms' },
                      { id: 'system', label: 'System Default', icon: Laptop, desc: 'Matches operating system appearance' }
                    ].map(t => {
                      const Icon = t.icon;
                      const isSelected = draft.theme === t.id;
                      return (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => {
                            updateDraft({ theme: t.id as any });
                            // Immediate update for live preview!
                            updateSettings({ theme: t.id as any });
                          }}
                          className={`p-4 rounded-xl border text-left flex flex-col justify-between gap-3 transition-all ${
                            isSelected 
                              ? 'bg-cyan-950/70 border-cyan-500 text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.2)]' 
                              : 'bg-slate-950 border-slate-900 text-slate-400 hover:text-white hover:border-slate-800'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <Icon className={`w-5 h-5 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
                            {isSelected && <Check className="w-4 h-4 text-cyan-400" />}
                          </div>
                          <div>
                            <span className="font-bold block text-white text-xs">{t.label}</span>
                            <span className="text-[10px] text-slate-500 block leading-tight mt-0.5">{t.desc}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Accent Color */}
                <div className="pt-4 border-t border-slate-900 space-y-3">
                  <label className="text-xs font-bold text-slate-300 block font-mono">
                    Interface Accent Color
                  </label>
                  <div className="grid grid-cols-5 gap-2.5">
                    {[
                      { id: 'cyan', label: 'Cyan', color: 'bg-cyan-500' },
                      { id: 'blue', label: 'Blue', color: 'bg-blue-500' },
                      { id: 'emerald', label: 'Emerald', color: 'bg-emerald-500' },
                      { id: 'violet', label: 'Violet', color: 'bg-purple-500' },
                      { id: 'amber', label: 'Amber', color: 'bg-amber-500' }
                    ].map(c => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => updateDraft({ accentColor: c.id as any })}
                        className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition-all ${
                          draft.accentColor === c.id
                            ? 'bg-slate-900 border-white/40 shadow-md'
                            : 'bg-slate-950 border-slate-900 hover:border-slate-800'
                        }`}
                      >
                        <span className={`w-4 h-4 rounded-full ${c.color} shadow-sm`} />
                        <span className="text-[10px] font-mono text-slate-300 font-bold">{c.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Layout Density */}
                <div className="pt-4 border-t border-slate-900 space-y-3">
                  <label className="text-xs font-bold text-slate-300 block font-mono">
                    Layout Density & Sidebar Defaults
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                      <div>
                        <span className="text-xs font-bold text-white block">Compact Display Density</span>
                        <span className="text-[10px] text-slate-500 font-mono">Reduce card padding for dense multi-monitor setups</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={draft.compactMode}
                        onChange={(e) => updateDraft({ compactMode: e.target.checked })}
                        className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                      />
                    </label>

                    <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                      <div>
                        <span className="text-xs font-bold text-white block">Auto-Collapse Sidebar</span>
                        <span className="text-[10px] text-slate-500 font-mono">Start in icon-only collapsed state by default</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={draft.sidebarCollapsedDefault}
                        onChange={(e) => updateDraft({ sidebarCollapsedDefault: e.target.checked })}
                        className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                      />
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* 3. PREFERENCES */}
            {activeTab === 'preferences' && (
              <div className="space-y-6">
                <div className="border-b border-slate-900 pb-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Layout className="w-5 h-5 text-cyan-400" />
                    <span>Dashboard & Surveillance Grid Preferences</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Customize multi-camera grid sizing, video telemetry overlays, and table pagination.
                  </p>
                </div>

                {/* Default Grid Size */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-300 block font-mono">
                    Default Camera Grid Layout
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 font-mono text-xs">
                    {[
                      { id: '2x2', label: '2 × 2 Matrix (4 feeds)' },
                      { id: '3x3', label: '3 × 3 Wall (9 feeds)' },
                      { id: '1x2', label: '1 × 2 Panoramic' },
                      { id: 'auto', label: 'Adaptive Auto' }
                    ].map(g => (
                      <button
                        key={g.id}
                        type="button"
                        onClick={() => updateDraft({ defaultCameraGrid: g.id as any })}
                        className={`p-3 rounded-xl border font-bold text-center transition-all ${
                          draft.defaultCameraGrid === g.id
                            ? 'bg-cyan-950/60 border-cyan-500 text-cyan-300'
                            : 'bg-slate-950 border-slate-900 text-slate-400 hover:text-white'
                        }`}
                      >
                        {g.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Stream Overlays */}
                <div className="pt-4 border-t border-slate-900 space-y-3">
                  <label className="text-xs font-bold text-slate-300 block font-mono">
                    Video Player HUD Overlays
                  </label>
                  <div className="space-y-2.5">
                    <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                      <div>
                        <span className="text-xs font-bold text-white block">Show Source & Inference FPS Badges</span>
                        <span className="text-[10px] text-slate-500 font-mono">Displays real-time capture FPS and YOLO processing FPS in video corners</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={draft.showFpsOverlay}
                        onChange={(e) => updateDraft({ showFpsOverlay: e.target.checked })}
                        className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                      />
                    </label>

                    <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                      <div>
                        <span className="text-xs font-bold text-white block">Show Person Tracker Identifiers</span>
                        <span className="text-[10px] text-slate-500 font-mono">Displays persistent track ID tags above bounding boxes</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={draft.showTrackIds}
                        onChange={(e) => updateDraft({ showTrackIds: e.target.checked })}
                        className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                      />
                    </label>
                  </div>
                </div>

                {/* Table Page Size */}
                <div className="pt-4 border-t border-slate-900 space-y-2">
                  <label className="text-xs font-bold text-slate-300 block font-mono">
                    Table Pagination Page Size
                  </label>
                  <div className="flex gap-3">
                    {[10, 25, 50].map(size => (
                      <button
                        key={size}
                        type="button"
                        onClick={() => updateDraft({ tablePageSize: size })}
                        className={`px-4 py-2 rounded-xl border text-xs font-mono font-bold transition-all ${
                          draft.tablePageSize === size
                            ? 'bg-cyan-950/60 border-cyan-500 text-cyan-300'
                            : 'bg-slate-950 border-slate-900 text-slate-400 hover:text-white'
                        }`}
                      >
                        {size} rows / page
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 4. ACCOUNT SETTINGS SHORTCUT */}
            {activeTab === 'account' && (
              <div className="space-y-6">
                <div className="border-b border-slate-900 pb-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <User className="w-5 h-5 text-cyan-400" />
                    <span>Account Security & Operator Credentials</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Manage your authenticated credentials, change your password, and review security levels.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-900 space-y-3 font-mono text-xs">
                  <div className="flex justify-between items-center text-slate-400">
                    <span>Operator Identity:</span>
                    <span className="text-white font-bold">{user?.name || 'Operator'}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-400">
                    <span>Email Address:</span>
                    <span className="text-cyan-300 font-bold">{user?.email || 'operator@surveillance.gov'}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-400">
                    <span>Role Authorization:</span>
                    <span className="text-emerald-400 font-bold">{user?.role || 'Command Officer'}</span>
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-gradient-to-r from-cyan-950/40 to-blue-950/40 border border-cyan-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-white">Full-Page Account Settings</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Open the dedicated security screen to change password or manage sessions.
                    </p>
                  </div>
                  <button
                    onClick={() => navigate('/account-settings')}
                    className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 whitespace-nowrap shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                  >
                    <span>Open Account Settings ➔</span>
                  </button>
                </div>
              </div>
            )}

            {/* 5. PRIVACY & SECURITY */}
            {activeTab === 'security' && (
              <div className="space-y-6">
                <div className="border-b border-slate-900 pb-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Shield className="w-5 h-5 text-cyan-400" />
                    <span>Privacy & Audit Security</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Surveillance audit logging, session verification, and data retention parameters.
                  </p>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 space-y-1">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="font-bold">Active JWT Bearer Protocol:</span>
                      <span className="text-emerald-400 font-bold">Encrypted & Valid</span>
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Tokens are validated per API request and strictly scoped to authenticated manager events.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 space-y-1">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="font-bold">Surveillance Audit Trail:</span>
                      <span className="text-cyan-400 font-bold">Enabled</span>
                    </div>
                    <p className="text-[10px] text-slate-500">
                      All emergency dispatches, instruction logs, and camera control actions are recorded in the database.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 space-y-1">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="font-bold">Event Isolation Boundary:</span>
                      <span className="text-emerald-400 font-bold">Hermetic Mode Active</span>
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Surveillance feeds and density telemetry are isolated to the active event identifier.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 6. NOTIFICATIONS */}
            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <div className="border-b border-slate-900 pb-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Bell className="w-5 h-5 text-cyan-400" />
                    <span>Alerts & Emergency Dispatch Notifications</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Configure audio alarms, desktop notifications, and automated emergency review policies.
                  </p>
                </div>

                <div className="space-y-3">
                  <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                    <div>
                      <span className="text-xs font-bold text-white block">Audible Siren Alarm</span>
                      <span className="text-[10px] text-slate-500 font-mono">Play audible alert warnings when density surpasses safety limit</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={draft.soundAlerts}
                      onChange={(e) => updateDraft({ soundAlerts: e.target.checked })}
                      className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                    />
                  </label>

                  <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                    <div>
                      <span className="text-xs font-bold text-white block">Auto Emergency Escalation Rule</span>
                      <span className="text-[10px] text-slate-500 font-mono">Automatically escalate persistent critical surges to Emergency Review Required</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={draft.autoEscalation}
                      onChange={(e) => updateDraft({ autoEscalation: e.target.checked })}
                      className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                    />
                  </label>

                  <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                    <div>
                      <span className="text-xs font-bold text-white block">In-App Banner Notifications</span>
                      <span className="text-[10px] text-slate-500 font-mono">Show top alert drawer badges when security anomalies are detected</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={draft.desktopNotifications}
                      onChange={(e) => updateDraft({ desktopNotifications: e.target.checked })}
                      className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                    />
                  </label>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800 text-[10px] text-slate-400 font-mono">
                  <span className="text-cyan-400 font-bold block mb-1">Safety Critical Rule:</span>
                  Essential safety alerts and emergency broadcast triggers cannot be silenced or disabled by preference settings.
                </div>
              </div>
            )}

            {/* 7. ACCESSIBILITY */}
            {activeTab === 'accessibility' && (
              <div className="space-y-6">
                <div className="border-b border-slate-900 pb-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Eye className="w-5 h-5 text-cyan-400" />
                    <span>Interface Accessibility & Legibility</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Visual contrast, interface scaling, and motion reduction options.
                  </p>
                </div>

                <div className="space-y-3">
                  <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                    <div>
                      <span className="text-xs font-bold text-white block">High Contrast Mode</span>
                      <span className="text-[10px] text-slate-500 font-mono">Increase contrast ratio between text, borders, and cards</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={draft.highContrast}
                      onChange={(e) => updateDraft({ highContrast: e.target.checked })}
                      className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                    />
                  </label>

                  <label className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-900 cursor-pointer">
                    <div>
                      <span className="text-xs font-bold text-white block">Reduced Motion Mode</span>
                      <span className="text-[10px] text-slate-500 font-mono">Disable animated slide transitions and pulse glows</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={draft.reducedMotion}
                      onChange={(e) => updateDraft({ reducedMotion: e.target.checked })}
                      className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-cyan-500 w-4 h-4"
                    />
                  </label>
                </div>

                {/* Font Scaling */}
                <div className="pt-4 border-t border-slate-900 space-y-2">
                  <label className="text-xs font-bold text-slate-300 block font-mono">
                    Interface Font Scaling
                  </label>
                  <div className="grid grid-cols-3 gap-2.5 font-mono text-xs">
                    {[
                      { id: 'sm', label: 'Compact (13px)' },
                      { id: 'md', label: 'Standard (14px)' },
                      { id: 'lg', label: 'Enlarged (16px)' }
                    ].map(f => (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => updateDraft({ fontSize: f.id as any })}
                        className={`p-3 rounded-xl border font-bold text-center transition-all ${
                          draft.fontSize === f.id
                            ? 'bg-cyan-950/60 border-cyan-500 text-cyan-300'
                            : 'bg-slate-950 border-slate-900 text-slate-400 hover:text-white'
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 8. ABOUT & SYSTEM INFO */}
            {activeTab === 'about' && (
              <div className="space-y-6">
                <div className="border-b border-slate-900 pb-4">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Info className="w-5 h-5 text-cyan-400" />
                    <span>System Architecture & Operational Information</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Software release version, computer vision pipeline, and active hardware specs.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-900 space-y-1">
                    <span className="text-slate-500 text-[10px] block">SOFTWARE PRODUCT:</span>
                    <span className="text-white font-bold block text-sm">AGY Surveillance — CROWD-AI</span>
                    <span className="text-cyan-400 text-[11px] block">v2.4.2 Enterprise Release</span>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-900 space-y-1">
                    <span className="text-slate-500 text-[10px] block">COMPUTER VISION ENGINE:</span>
                    <span className="text-white font-bold block text-sm">Ultralytics YOLOv8n + PyTorch</span>
                    <span className="text-emerald-400 text-[11px] block">
                      {hardwareInfo.device || 'Host CPU Acceleration'}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-900 space-y-1">
                    <span className="text-slate-500 text-[10px] block">INFERENCE SCHEDULER:</span>
                    <span className="text-white font-bold block text-sm">DynamicInferenceScheduler</span>
                    <span className="text-cyan-300 text-[11px] block">
                      Round-Robin Fair Scheduling (Depth-1)
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-900 space-y-1">
                    <span className="text-slate-500 text-[10px] block">ACTIVE SURVEILLANCE STREAMS:</span>
                    <span className="text-white font-bold block text-sm">{cameras.length} Active Feeds</span>
                    <span className="text-slate-400 text-[11px] block">
                      MJPEG WebSockets Pipeline
                    </span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 text-[10px] text-slate-400 font-mono">
                  All rights reserved. Real-Time AI-Based Crowd Surveillance System with Predictive Analytics & Smart Evacuation.
                </div>
              </div>
            )}

            {/* Bottom Actions Bar */}
            <div className="pt-6 border-t border-slate-900 flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                onClick={handleResetDefaults}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white text-xs font-bold font-mono transition-all flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Category</span>
              </button>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleDiscard}
                  disabled={!isDirty || isSaving}
                  className={`px-4 py-2 rounded-xl text-xs font-bold font-mono transition-all border ${
                    isDirty 
                      ? 'bg-slate-900 border-slate-700 text-slate-300 hover:text-white' 
                      : 'bg-slate-900/40 border-slate-900 text-slate-600 cursor-not-allowed'
                  }`}
                >
                  Discard Changes
                </button>

                <button
                  type="button"
                  onClick={() => handleSave()}
                  disabled={!isDirty || isSaving}
                  className={`px-5 py-2 rounded-xl text-xs font-bold font-mono uppercase tracking-wider transition-all flex items-center gap-1.5 shadow-lg ${
                    isDirty 
                      ? 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-600/30' 
                      : 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed'
                  }`}
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
                </button>
              </div>
            </div>

          </GlassCard>
        </div>

      </div>
    </div>
  );
};
