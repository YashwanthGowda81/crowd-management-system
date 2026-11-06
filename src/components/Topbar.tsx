import React, { useState, useRef, useEffect } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { 
  Bell, 
  ShieldAlert, 
  Clock, 
  Calendar, 
  Check, 
  AlertCircle, 
  Sliders, 
  Moon, 
  Sun,
  User,
  Users,
  Settings,
  LogOut,
  ChevronDown
} from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';

export const Topbar: React.FC = () => {
  const navigate = useNavigate();
  const { 
    emergencyState, 
    currentTime, 
    currentEvent, 
    events, 
    selectedEventId, 
    alerts, 
    resolveAlert, 
    settings, 
    updateSettings,
    user,
    logout,
    onboardingStatus
  } = useCrowdSystem();

  const [showNotifications, setShowNotifications] = useState(false);
  const [showAccountMenu, setShowAccountMenu] = useState(false);

  const accountMenuRef = useRef<HTMLDivElement>(null);
  const activeAlerts = alerts.filter(a => !a.resolved);

  const activeEventObj = events.find(e => e.id === selectedEventId) || onboardingStatus?.event;

  // Click outside listener to close account dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target as Node)) {
        setShowAccountMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleTheme = () => {
    const nextTheme = settings.theme === 'dark' ? 'light' : 'dark';
    updateSettings({ theme: nextTheme });
  };

  const handleLogout = () => {
    setShowAccountMenu(false);
    logout();
    navigate('/', { replace: true });
  };

  // User initials
  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'OP';

  return (
    <>
      <header className="h-16 border-b border-cyber-border/40 px-6 flex items-center justify-between bg-[#0B0F19]/80 backdrop-blur-md sticky top-0 z-20 w-full select-none font-mono">
        {/* Left Side: Active Operation Context Display */}
        <div className="flex items-center gap-4">
          <NavLink 
            to="/dashboard" 
            className="px-3 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-400 font-bold text-xs flex items-center gap-1.5 transition-colors"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </NavLink>

          {/* Current Running Event Banner (Read-only badge scoped to authenticated manager) */}
          <div className="flex items-center gap-2 text-xs font-medium text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-cyan-500/30">
            <Calendar className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
            <span className="hidden md:inline text-slate-400">Event:</span>
            <span 
              className="text-cyan-300 font-bold max-w-[220px] sm:max-w-[320px] truncate"
              title={activeEventObj?.title || currentEvent || 'No Active Event'}
            >
              {activeEventObj?.title || currentEvent || 'No Active Event'}
            </span>
          </div>
        </div>

        {/* Emergency Status Banner */}
        {emergencyState.isTriggered && (
          <NavLink 
            to="/emergency"
            className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-red-950/80 border border-red-500/50 text-red-200 text-xs font-semibold animate-pulse cursor-pointer shadow-[0_0_15px_rgba(239,68,68,0.2)]"
          >
            <ShieldAlert className="w-4 h-4 text-red-500" />
            <span>ACTIVE CRISIS: {emergencyState.type} IN {emergencyState.location.toUpperCase()}</span>
          </NavLink>
        )}

        {/* Right Side Actions */}
        <div className="flex items-center gap-3">
          {/* Quick Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg bg-slate-900/50 border border-cyber-border hover:border-cyan-500/40 text-slate-300 transition-colors"
            title={`Current Theme: ${settings.theme}. Click to toggle.`}
          >
            {settings.theme === 'light' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-cyan-400" />}
          </button>

          {/* Current Local Clock */}
          <div className="hidden md:flex items-center gap-1.5 text-xs font-semibold text-slate-300 bg-slate-900/40 px-3 py-1.5 rounded-lg border border-cyber-border/20 font-mono">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>{currentTime}</span>
          </div>

          {/* Notifications Icon with Dropdown */}
          <div className="relative">
            <button 
              onClick={() => setShowNotifications(!showNotifications)}
              className="p-2 rounded-lg bg-slate-900/50 border border-cyber-border hover:border-cyan-500/40 transition-colors relative"
              title="Notifications Drawer"
            >
              <Bell className="w-4 h-4 text-slate-300" />
              {activeAlerts.length > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full animate-ping" />
              )}
            </button>

            {/* Notifications Dropdown Panel */}
            {showNotifications && (
              <div className="absolute right-0 mt-3 w-80 rounded-xl bg-slate-950 border border-cyber-border shadow-2xl p-4 z-50">
                <div className="flex items-center justify-between mb-3 border-b border-cyber-border/20 pb-2">
                  <span className="text-xs uppercase tracking-wider font-semibold text-slate-300">Active Alert Logs</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-red-950 text-red-400 font-bold">
                    {activeAlerts.length} Active
                  </span>
                </div>

                <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                  {activeAlerts.length === 0 ? (
                    <div className="text-center py-6 text-slate-500 text-xs">
                      No active warnings. System secure.
                    </div>
                  ) : (
                    activeAlerts.map(alert => (
                      <div 
                        key={alert.id} 
                        className={`p-2.5 rounded-lg border text-xs flex gap-2 justify-between items-start
                          ${alert.level === 'critical' 
                            ? 'bg-red-950/20 border-red-900/40 text-red-200' 
                            : 'bg-amber-950/20 border-amber-900/40 text-amber-200'}`}
                      >
                        <div className="flex gap-2">
                          {alert.level === 'critical' 
                            ? <ShieldAlert className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" /> 
                            : <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                          }
                          <div>
                            <p className="font-semibold leading-tight">{alert.title}</p>
                            <p className="text-[10px] text-slate-400 leading-normal mt-0.5">{alert.description}</p>
                            <span className="text-[9px] text-slate-500 block mt-1">{alert.timestamp} · {alert.zone}</span>
                          </div>
                        </div>
                        <button 
                          onClick={() => resolveAlert(alert.id)}
                          className="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-green-400"
                          title="Mark alert as resolved"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
                <div className="mt-3 pt-2 border-t border-cyber-border/20 text-center">
                  <NavLink 
                    to="/alerts" 
                    onClick={() => setShowNotifications(false)}
                    className="text-[10px] text-cyan-400 hover:text-cyan-300 font-semibold"
                  >
                    View All Alert History →
                  </NavLink>
                </div>
              </div>
            )}
          </div>

          {/* User Profile Badge / Clickable Avatar */}
          <div className="relative" ref={accountMenuRef}>
            <button
              onClick={() => setShowAccountMenu(!showAccountMenu)}
              className="flex items-center gap-2.5 border-l border-cyber-border/40 pl-4 py-1 hover:opacity-90 transition-opacity cursor-pointer group"
              title="Click to view Account Menu"
            >
              <div className="w-8 h-8 rounded-full bg-cyan-950 border border-cyan-500/40 group-hover:border-cyan-400 flex items-center justify-center font-bold text-cyan-400 text-xs shadow-[0_0_10px_rgba(6,182,212,0.2)]">
                {initials}
              </div>
              <div className="hidden lg:block text-left">
                <p className="text-xs font-bold text-white leading-tight group-hover:text-cyan-300 transition-colors">
                  {user?.name || 'Operator'}
                </p>
                <p className="text-[9px] text-slate-400 leading-none">
                  {user?.role || 'Surveillance Operator'}
                </p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-400 transition-transform duration-200" />
            </button>

            {/* EXACT 4-OPTION ACCOUNT DROPDOWN */}
            {/* STRICTLY NO CAMERA OPTIONS */}
            {showAccountMenu && (
              <div className="absolute right-0 mt-3 w-56 rounded-2xl bg-[#090D1A] border border-cyan-500/30 shadow-[0_10px_30px_rgba(0,0,0,0.8)] py-2 z-50 divide-y divide-slate-800/60 font-sans">
                {/* User Header in Dropdown */}
                <div className="px-4 py-2.5">
                  <p className="text-xs font-bold text-white truncate">{user?.name || 'Operator'}</p>
                  <p className="text-[10px] text-slate-400 truncate">{user?.email || 'operator@surveillance.gov'}</p>
                  <span className="inline-block mt-1 text-[9px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 font-bold border border-cyan-500/30">
                    {user?.role || 'Surveillance Operator'}
                  </span>
                </div>

                {/* Exactly 5 Specified Options */}
                <div className="py-1">
                  {/* Option 1: My Profile */}
                  <button
                    onClick={() => {
                      setShowAccountMenu(false);
                      navigate('/profile');
                    }}
                    className="w-full px-4 py-2.5 text-left text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-900/80 flex items-center gap-2.5 transition-colors"
                  >
                    <User className="w-4 h-4 text-cyan-400" />
                    <span>My Profile</span>
                  </button>

                  {/* Option 2: My Event */}
                  <button
                    onClick={() => {
                      setShowAccountMenu(false);
                      navigate('/my-event');
                    }}
                    className="w-full px-4 py-2.5 text-left text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-900/80 flex items-center gap-2.5 transition-colors"
                  >
                    <Calendar className="w-4 h-4 text-cyan-400" />
                    <span>My Event</span>
                  </button>

                  {/* Option 3: Officer Control Panel */}
                  <button
                    onClick={() => {
                      setShowAccountMenu(false);
                      navigate('/officer-control');
                    }}
                    className="w-full px-4 py-2.5 text-left text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-900/80 flex items-center gap-2.5 transition-colors"
                  >
                    <Sliders className="w-4 h-4 text-cyan-400" />
                    <span>Officer Control Panel</span>
                  </button>

                  {/* Option 4: Manage Event Personnel */}
                  <button
                    onClick={() => {
                      setShowAccountMenu(false);
                      navigate('/manage-personnel');
                    }}
                    className="w-full px-4 py-2.5 text-left text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-900/80 flex items-center gap-2.5 transition-colors"
                  >
                    <Users className="w-4 h-4 text-cyan-400" />
                    <span>Manage Event Personnel</span>
                  </button>

                  {/* Option 5: Account Settings */}
                  <button
                    onClick={() => {
                      setShowAccountMenu(false);
                      navigate('/account-settings');
                    }}
                    className="w-full px-4 py-2.5 text-left text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-900/80 flex items-center gap-2.5 transition-colors"
                  >
                    <Settings className="w-4 h-4 text-cyan-400" />
                    <span>Account Settings</span>
                  </button>
                </div>

                {/* Option 6: Logout */}
                <div className="py-1">
                  <button
                    onClick={handleLogout}
                    className="w-full px-4 py-2.5 text-left text-xs font-semibold text-red-400 hover:text-red-300 hover:bg-red-950/30 flex items-center gap-2.5 transition-colors"
                  >
                    <LogOut className="w-4 h-4 text-red-400" />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  );
};
