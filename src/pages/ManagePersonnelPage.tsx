import React from 'react';
import { NavLink } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { PersonnelDirectory } from '../components/PersonnelDirectory';
import { 
  Users, 
  Shield, 
  Calendar, 
  Compass, 
  CheckCircle2
} from 'lucide-react';

export const ManagePersonnelPage: React.FC = () => {
  const { 
    events, 
    selectedEventId, 
    user, 
    onboardingStatus 
  } = useCrowdSystem();

  const activeEvent = events.find(e => e.id === selectedEventId) || onboardingStatus?.event;

  return (
    <div className="space-y-6 pb-12 font-mono">
      {/* Top Banner & Context Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs mb-1">
            <Users className="w-4 h-4" />
            <span>SECURITY COMMAND · GROUND PERSONNEL ROSTER</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <span>Manage Event Personnel</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-3xl font-sans">
            Dedicated operational workspace for registering and organizing event volunteers, security guards, 
            event coordinators, and team leaders stationed across active venue zones for:{' '}
            <span className="text-cyan-400 font-bold font-mono">
              {activeEvent ? activeEvent.title : 'Global Operations'}
            </span>.
          </p>
        </div>

        {/* Right Header Navigation & Event Context */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Active Event Badge */}
          <div className="flex items-center gap-2 bg-slate-900 px-3 py-2 rounded-xl border border-cyan-500/30 text-xs">
            <Calendar className="w-4 h-4 text-cyan-400" />
            <span className="text-slate-400">Event:</span>
            <span className="text-cyan-300 font-bold max-w-[200px] truncate">
              {activeEvent?.title || 'Global Operations'}
            </span>
          </div>

          {/* Quick Nav to Ground Coordination */}
          <NavLink
            to="/staff-communication"
            className="px-3.5 py-2 rounded-xl bg-cyan-950/70 hover:bg-cyan-900/80 border border-cyan-500/40 text-cyan-300 font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-colors shadow-[0_0_12px_rgba(6,182,212,0.2)]"
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Ground Coordination ➔</span>
          </NavLink>
        </div>
      </div>

      {/* Role & Permission Status Banner */}
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-cyber-border/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2.5">
          <Shield className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="text-slate-300">
            Authorized Operator: <strong className="text-white">{user?.name || 'Surveillance Operator'}</strong>
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-cyan-950 text-cyan-300 border border-cyan-500/30">
            {user?.role || 'Surveillance Operator'}
          </span>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-emerald-400">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Full Personnel CRUD & Event-Scoped Permissions Active</span>
        </div>
      </div>

      {/* Reusable Personnel Directory Component */}
      <PersonnelDirectory />
    </div>
  );
};
export default ManagePersonnelPage;
