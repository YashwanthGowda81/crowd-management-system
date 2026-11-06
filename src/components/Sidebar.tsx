import React from 'react';
import { NavLink } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { 
  LayoutDashboard, 
  Video, 
  BarChart3, 
  Cpu, 
  Bell, 
  FileText, 
  Server, 
  AlertOctagon, 
  Settings, 
  Radio,
  Layers,
  PhoneCall,
  LogOut,
  Flame
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, setCollapsed }) => {
  const { emergencyState, logout } = useCrowdSystem();

  // Exactly 12 Sidebar Items
  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard, highlightCyan: true },
    { name: 'Live Monitoring', path: '/live', icon: Video },
    { name: 'Crowd Density Heatmap', path: '/heatmap', icon: Flame },
    { name: 'Camera Access & Health', path: '/cameras', icon: Server },
    { name: 'Venue Architecture & Map', path: '/venue-architecture', icon: Layers },
    { name: 'Security Staff Dispatch', path: '/staff-communication', icon: PhoneCall },
    { name: 'Crowd Analytics', path: '/analytics', icon: BarChart3 },
    { name: 'Decision Support', path: '/decision-support', icon: Cpu },
    { name: 'Alerts Logs', path: '/alerts', icon: Bell },
    { name: 'Emergency Panel', path: '/emergency', icon: AlertOctagon, highlightRed: true },
    { name: 'Reports Generator', path: '/reports', icon: FileText },
    { name: 'System Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside 
      className={`fixed top-0 left-0 h-screen z-30 transition-all duration-300 ease-in-out border-r border-cyber-border flex flex-col
        ${collapsed ? 'w-20' : 'w-[270px]'} 
        ${emergencyState.isTriggered ? 'bg-[#150508] border-red-900/30' : 'bg-[#0B0F19]'}`}
    >
      {/* Brand Logo Header (Stationary) */}
      <div className="h-16 flex items-center px-4 border-b border-cyber-border/40 gap-3.5 flex-shrink-0 overflow-hidden select-none">
        <div className={`p-2.5 rounded-xl ${emergencyState.isTriggered ? 'bg-red-500/20 text-red-400' : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'}`}>
          <Radio className={`w-5 h-5 ${emergencyState.isTriggered ? 'animate-ping' : ''}`} />
        </div>
        {!collapsed && (
          <div className="flex flex-col min-w-0">
            <span className="font-bold text-[11px] uppercase tracking-wider text-slate-400 font-mono">
              AGY SURVEILLANCE
            </span>
            <span className={`text-[15px] font-extrabold tracking-tight truncate ${emergencyState.isTriggered ? 'text-red-400' : 'text-cyan-400 glow-text-cyan'}`}>
              CROWD-AI v2.4
            </span>
          </div>
        )}
      </div>

      {/* Nav Links (Independently scrollable if screen height requires) */}
      <nav className="p-3 space-y-1.5 flex-1 overflow-y-auto min-h-0">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isEmergency = item.highlightRed && emergencyState.isTriggered;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `
                flex items-center gap-3.5 px-3.5 py-3 rounded-xl text-[15.5px] font-medium transition-all group relative tracking-normal leading-snug
                ${isEmergency 
                  ? 'bg-red-900/40 text-red-200 border border-red-500/40 animate-pulse font-semibold' 
                  : item.highlightRed 
                    ? 'hover:bg-red-900/20 hover:text-red-300 text-slate-400 border border-transparent'
                    : item.highlightCyan && isActive
                      ? 'bg-cyan-950/70 text-cyan-300 border border-cyan-500/40 font-semibold shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                      : isActive 
                        ? 'bg-cyan-950/50 text-cyan-400 border border-cyan-500/30 font-semibold' 
                        : 'text-slate-300 hover:bg-slate-900/70 hover:text-white border border-transparent'
                }
              `}
            >
              {({ isActive }) => (
                <>
                  <Icon className={`w-[19px] h-[19px] flex-shrink-0 transition-transform group-hover:scale-110
                    ${isEmergency 
                      ? 'text-red-400' 
                      : item.highlightRed 
                        ? 'text-red-400/90'
                        : isActive
                          ? 'text-cyan-400'
                          : 'text-slate-400 group-hover:text-cyan-400'}`} 
                  />
                  
                  {!collapsed && (
                    <span className="truncate">{item.name}</span>
                  )}

                  {/* Tooltip for collapsed sidebar */}
                  {collapsed && (
                    <div className="absolute left-full ml-4 px-3 py-1.5 rounded-lg bg-slate-950 text-slate-200 text-xs 
                      invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-opacity whitespace-nowrap 
                      z-50 border border-slate-800 shadow-xl pointer-events-none font-medium">
                      {item.name}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Collapse Toggle & Logout (Stationary pinned to bottom) */}
      <div className="flex-shrink-0 w-full p-3 border-t border-cyber-border/40 space-y-1.5 bg-[#0B0F19]">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 rounded-xl text-slate-400 hover:bg-slate-900/70 hover:text-white transition-colors border border-transparent hover:border-slate-800"
          title="Toggle Navigation Menu"
        >
          <span className="text-xs uppercase tracking-wider font-semibold font-mono">
            {collapsed ? '→' : '← collapse sidebar'}
          </span>
        </button>

        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-red-400/90 hover:bg-red-950/30 hover:text-red-300 transition-all border border-transparent hover:border-red-900/40"
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!collapsed && <span>System Logout</span>}
        </button>
      </div>
    </aside>
  );
};
