import React, { useState, useMemo } from 'react';
import { useCrowdSystem, type SecurityGuard } from '../context/CrowdSystemContext';
import { GlassCard } from './GlassCard';
import { 
  Users, 
  UserCheck, 
  Clock, 
  Building2, 
  Search, 
  Filter, 
  MapPin, 
  Phone, 
  Eye, 
  EyeOff, 
  Edit2, 
  Trash2, 
  Battery, 
  UserPlus, 
  AlertCircle, 
  CheckCircle2
} from 'lucide-react';

export interface PersonnelDirectoryProps {
  className?: string;
  showEventContextBanner?: boolean;
  onSelectPersonnel?: (guard: SecurityGuard) => void;
}

export const PersonnelDirectory: React.FC<PersonnelDirectoryProps> = ({
  className = '',
  showEventContextBanner = true,
  onSelectPersonnel
}) => {
  const { 
    guards, 
    events, 
    selectedEventId, 
    cameras, 
    user, 
    addStaffMember, 
    updateStaffMember, 
    deactivateStaffMember 
  } = useCrowdSystem();

  const currentEvent = events.find(e => e.id === selectedEventId) || events[0];

  // Directory Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [zoneFilter, setZoneFilter] = useState('all');
  const [revealPhones, setRevealPhones] = useState<Record<string, boolean>>({});

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingGuard, setEditingGuard] = useState<SecurityGuard | null>(null);
  const [deactivatingGuard, setDeactivatingGuard] = useState<SecurityGuard | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State for Add / Edit
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    role: 'Security Guard',
    eventId: selectedEventId || '',
    zone: 'North Main Gate',
    organization: '',
    dutyStatus: 'On Duty',
    notes: ''
  });

  // Unique zones for directory filter
  const availableZones = useMemo(() => {
    const set = new Set<string>();
    guards.forEach(g => {
      if (g.zone) set.add(g.zone);
    });
    cameras.forEach(c => {
      if (c.location) set.add(c.location);
    });
    return Array.from(set);
  }, [guards, cameras]);

  // Event-Scoped Filtered Personnel
  const filteredGuards = useMemo(() => {
    return guards.filter(guard => {
      // Event isolation
      if (selectedEventId && guard.eventId && guard.eventId !== selectedEventId) {
        return false;
      }
      if (roleFilter !== 'all' && (guard.role || 'Security Guard') !== roleFilter) {
        return false;
      }
      if (statusFilter !== 'all' && (guard.dutyStatus || 'On Duty') !== statusFilter) {
        return false;
      }
      if (zoneFilter !== 'all' && guard.zone !== zoneFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const nameMatch = guard.name.toLowerCase().includes(q);
        const phoneMatch = guard.phone.toLowerCase().includes(q);
        const orgMatch = (guard.organization || '').toLowerCase().includes(q);
        const zoneMatch = guard.zone.toLowerCase().includes(q);
        const roleMatch = (guard.role || '').toLowerCase().includes(q);
        if (!nameMatch && !phoneMatch && !orgMatch && !zoneMatch && !roleMatch) {
          return false;
        }
      }
      return true;
    });
  }, [guards, selectedEventId, roleFilter, statusFilter, zoneFilter, searchQuery]);

  // Phone masking
  const togglePhoneReveal = (id: string) => {
    setRevealPhones(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const maskPhone = (phone: string) => {
    if (!phone || phone.length < 6) return '*******';
    return phone.slice(0, 3) + '••••••' + phone.slice(-3);
  };

  const validatePhone = (num: string): boolean => {
    const clean = num.trim();
    if (clean.length < 7) return false;
    const digitCount = (clean.match(/\d/g) || []).length;
    return digitCount >= 7;
  };

  // Open Add Modal
  const openAddModal = () => {
    setFormError(null);
    setFormData({
      name: '',
      phone: '+1-',
      role: 'Security Guard',
      eventId: selectedEventId || (events[0]?.id || ''),
      zone: availableZones[0] || 'North Main Gate',
      organization: 'Venue Operations Team',
      dutyStatus: 'On Duty',
      notes: ''
    });
    setIsAddModalOpen(true);
  };

  // Open Edit Modal
  const openEditModal = (guard: SecurityGuard) => {
    setFormError(null);
    setEditingGuard(guard);
    setFormData({
      name: guard.name,
      phone: guard.phone,
      role: guard.role || 'Security Guard',
      eventId: guard.eventId || selectedEventId || '',
      zone: guard.zone,
      organization: guard.organization || '',
      dutyStatus: guard.dutyStatus || 'On Duty',
      notes: guard.notes || ''
    });
  };

  // Submit Add Personnel
  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (formData.name.trim().length < 2) {
      setFormError('Personnel name must be at least 2 characters long.');
      return;
    }
    if (!validatePhone(formData.phone)) {
      setFormError('Mobile number must include a valid country code and at least 7 digits (e.g. +1-555-0199 or +91-9876543210).');
      return;
    }

    setIsSubmitting(true);
    try {
      await addStaffMember({
        name: formData.name.trim(),
        phone: formData.phone.trim(),
        role: formData.role,
        eventId: formData.eventId || selectedEventId,
        zone: formData.zone.trim(),
        organization: formData.organization.trim() || undefined,
        dutyStatus: formData.dutyStatus,
        notes: formData.notes.trim() || undefined
      });
      setIsAddModalOpen(false);
    } catch (err: any) {
      setFormError(err.message || 'Failed to register ground personnel.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Edit Personnel
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingGuard) return;
    setFormError(null);

    if (formData.name.trim().length < 2) {
      setFormError('Personnel name must be at least 2 characters long.');
      return;
    }
    if (!validatePhone(formData.phone)) {
      setFormError('Mobile number must include a valid country code and at least 7 digits.');
      return;
    }

    setIsSubmitting(true);
    try {
      await updateStaffMember(editingGuard.id, {
        name: formData.name.trim(),
        phone: formData.phone.trim(),
        role: formData.role,
        eventId: formData.eventId,
        zone: formData.zone.trim(),
        organization: formData.organization.trim() || undefined,
        dutyStatus: formData.dutyStatus,
        notes: formData.notes.trim() || undefined
      });
      setEditingGuard(null);
    } catch (err: any) {
      setFormError(err.message || 'Failed to update personnel record.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Deactivate Personnel
  const handleDeactivate = async () => {
    if (!deactivatingGuard) return;
    setIsSubmitting(true);
    try {
      await deactivateStaffMember(deactivatingGuard.id, false);
      setDeactivatingGuard(null);
    } catch (err: any) {
      setFormError(err.message || 'Failed to deactivate personnel.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`space-y-6 font-mono ${className}`}>
      {/* Event Context Banner */}
      {showEventContextBanner && (
        <div className="p-3 rounded-xl bg-slate-900/50 border border-cyber-border/40 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-cyan-400" />
            <span>Active Operational Event:</span>
            <span className="text-cyan-300 font-bold">{currentEvent ? currentEvent.title : 'Global Operations'}</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">
            Operator: {user?.name || user?.role || 'Authorized'}
          </span>
        </div>
      )}

      {/* Metrics Summary Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <GlassCard className="p-4 flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Total Registered</p>
            <p className="text-2xl font-extrabold text-white mt-0.5">{filteredGuards.length}</p>
            <p className="text-[10px] text-cyan-400 mt-1">In Selected Event</p>
          </div>
          <Users className="w-7 h-7 text-cyan-400/60" />
        </GlassCard>

        <GlassCard className="p-4 flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">On Duty Active</p>
            <p className="text-2xl font-extrabold text-emerald-400 mt-0.5">
              {filteredGuards.filter(g => (g.dutyStatus || 'On Duty') === 'On Duty').length}
            </p>
            <p className="text-[10px] text-emerald-500 mt-1">Stationed On Ground</p>
          </div>
          <UserCheck className="w-7 h-7 text-emerald-400/60" />
        </GlassCard>

        <GlassCard className="p-4 flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Off Duty</p>
            <p className="text-2xl font-extrabold text-slate-300 mt-0.5">
              {filteredGuards.filter(g => g.dutyStatus === 'Off Duty').length}
            </p>
            <p className="text-[10px] text-slate-500 mt-1">Standby Reserve</p>
          </div>
          <Clock className="w-7 h-7 text-slate-400/60" />
        </GlassCard>

        <GlassCard className="p-4 flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Event Isolation</p>
            <p className="text-sm font-extrabold text-cyan-300 truncate mt-1">
              {currentEvent ? currentEvent.title : 'Global Operations'}
            </p>
            <p className="text-[10px] text-slate-400 mt-1">Scoped Database Records</p>
          </div>
          <Building2 className="w-7 h-7 text-cyan-400/60" />
        </GlassCard>
      </div>

      {/* Search, Filter Toolbar & Add Button */}
      <GlassCard className="p-4">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
          {/* Search Bar */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by personnel name, mobile number, role, organization, or zone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          {/* Filters & Actions */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Filter className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-[10px] uppercase font-bold">Filters:</span>
            </div>

            {/* Role Filter */}
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="px-3 py-2 rounded-xl bg-slate-950 border border-cyber-border text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
            >
              <option value="all">All Roles</option>
              <option value="Security Guard">Security Guard</option>
              <option value="Event Coordinator">Event Coordinator</option>
              <option value="Team Leader">Team Leader</option>
              <option value="Event Volunteer">Event Volunteer</option>
              <option value="Medical Contact">Medical Contact</option>
            </select>

            {/* Duty Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 rounded-xl bg-slate-950 border border-cyber-border text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
            >
              <option value="all">All Duty Statuses</option>
              <option value="On Duty">On Duty</option>
              <option value="Off Duty">Off Duty</option>
              <option value="Unavailable">Unavailable</option>
            </select>

            {/* Zone Filter */}
            {availableZones.length > 0 && (
              <select
                value={zoneFilter}
                onChange={(e) => setZoneFilter(e.target.value)}
                className="px-3 py-2 rounded-xl bg-slate-950 border border-cyber-border text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
              >
                <option value="all">All Zones</option>
                {availableZones.map(z => (
                  <option key={z} value={z}>{z}</option>
                ))}
              </select>
            )}

            {(searchQuery || roleFilter !== 'all' || statusFilter !== 'all' || zoneFilter !== 'all') && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setRoleFilter('all');
                  setStatusFilter('all');
                  setZoneFilter('all');
                }}
                className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-[10px] uppercase font-bold text-cyan-400 hover:text-cyan-300"
              >
                Reset
              </button>
            )}

            {/* Primary Action: Register Personnel */}
            <button
              onClick={openAddModal}
              className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider inline-flex items-center gap-2 shadow-[0_0_12px_rgba(6,182,212,0.25)] transition-all ml-auto"
            >
              <UserPlus className="w-4 h-4" />
              <span>Register Personnel</span>
            </button>
          </div>
        </div>
      </GlassCard>

      {/* Personnel Table / Cards Grid */}
      {filteredGuards.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredGuards.map((guard) => {
            const isRevealed = revealPhones[guard.id];
            const displayRole = guard.role || 'Security Guard';
            const displayDuty = guard.dutyStatus || 'On Duty';

            return (
              <GlassCard 
                key={guard.id} 
                className="p-5 flex flex-col justify-between space-y-4 relative group hover:border-cyan-500/40 transition-colors"
              >
                {/* Top Row: Name, Role, Duty Status */}
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1 min-w-0">
                    <h3 className="font-bold text-sm text-white group-hover:text-cyan-300 transition-colors truncate">
                      {guard.name}
                    </h3>
                    <div>
                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-cyan-950/80 border border-cyan-500/30 text-cyan-300">
                        {displayRole}
                      </span>
                    </div>
                  </div>

                  {/* Duty Status Badge */}
                  <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border shrink-0 ${
                    displayDuty === 'On Duty'
                      ? 'bg-emerald-950/80 border-emerald-500/30 text-emerald-400 flex items-center gap-1'
                      : displayDuty === 'Off Duty'
                      ? 'bg-slate-900 border-slate-800 text-slate-400'
                      : 'bg-amber-950/80 border-amber-500/30 text-amber-400'
                  }`}>
                    {displayDuty === 'On Duty' && <CheckCircle2 className="w-2.5 h-2.5" />}
                    {displayDuty}
                  </span>
                </div>

                {/* Middle Details: Zone, Organization, Mobile */}
                <div className="space-y-2 text-xs border-y border-slate-800/80 py-3">
                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-500 text-[10px] uppercase font-bold flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-cyan-400" /> Assigned Zone:
                    </span>
                    <span className="font-semibold text-white truncate max-w-[170px]">{guard.zone}</span>
                  </div>

                  {guard.organization && (
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="text-slate-500 text-[10px] uppercase font-bold flex items-center gap-1">
                        <Building2 className="w-3 h-3 text-cyan-400" /> Organization:
                      </span>
                      <span className="text-slate-300 truncate max-w-[170px]">{guard.organization}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 text-[10px] uppercase font-bold flex items-center gap-1">
                      <Phone className="w-3 h-3 text-cyan-400" /> Mobile:
                    </span>
                    <div className="flex items-center gap-1.5 font-mono">
                      <span className="text-cyan-300 font-bold">
                        {isRevealed ? guard.phone : maskPhone(guard.phone)}
                      </span>
                      <button
                        type="button"
                        onClick={() => togglePhoneReveal(guard.id)}
                        title={isRevealed ? "Mask mobile number" : "Reveal full mobile number"}
                        className="p-1 hover:text-white text-slate-500 transition-colors"
                      >
                        {isRevealed ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  {guard.notes && (
                    <p className="text-[11px] text-slate-400 italic bg-slate-950/60 p-2 rounded-lg border border-slate-900 leading-relaxed">
                      "{guard.notes}"
                    </p>
                  )}
                </div>

                {/* Card Actions Footer */}
                <div className="flex items-center justify-between pt-1 text-[11px]">
                  <div className="flex items-center gap-1 text-slate-500 text-[10px]">
                    <Battery className="w-3.5 h-3.5 text-slate-400" />
                    <span>{guard.battery || 100}% Battery</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {onSelectPersonnel && (
                      <button
                        type="button"
                        onClick={() => onSelectPersonnel(guard)}
                        className="px-2.5 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/30 text-cyan-300 font-bold text-[10px] uppercase"
                      >
                        Direct
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => openEditModal(guard)}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors flex items-center gap-1 font-bold text-[10px] uppercase"
                    >
                      <Edit2 className="w-3 h-3 text-cyan-400" /> Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeactivatingGuard(guard)}
                      className="px-2.5 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/40 border border-red-500/20 text-red-400 transition-colors flex items-center gap-1 font-bold text-[10px] uppercase"
                    >
                      <Trash2 className="w-3 h-3" /> Deactivate
                    </button>
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
      ) : (
        <GlassCard className="p-12 text-center space-y-4">
          <Users className="w-12 h-12 text-slate-600 mx-auto" />
          <div>
            <h3 className="text-base font-bold text-white">No Personnel Records Found</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              {searchQuery || roleFilter !== 'all' || statusFilter !== 'all' || zoneFilter !== 'all'
                ? "No personnel match your current filter settings. Try clearing search filters."
                : `No security guards, event volunteers, or coordinators registered for ${currentEvent?.title || 'this event'} yet.`}
            </p>
          </div>
          <button
            onClick={openAddModal}
            className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider inline-flex items-center gap-2 shadow-lg"
          >
            <UserPlus className="w-4 h-4" /> Register First Ground Personnel
          </button>
        </GlassCard>
      )}

      {/* MODAL: REGISTER GROUND PERSONNEL */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in font-sans">
          <div className="bg-[#0D1424] border border-cyan-500/40 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-cyan-400">
                <UserPlus className="w-5 h-5" />
                <h3 className="font-extrabold text-sm uppercase text-white font-mono">Register Ground Personnel</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-500 hover:text-white text-xs font-bold p-1"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-red-950/80 border border-red-500/40 text-red-300 text-xs flex items-center gap-2 font-mono">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleAddSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Marcus Vance or Sarah Jenkins"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Mobile (+Country Code) *</label>
                  <input
                    type="text"
                    required
                    placeholder="+1-555-0199 or +91-..."
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Personnel Role *</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="Security Guard">Security Guard</option>
                    <option value="Event Coordinator">Event Coordinator</option>
                    <option value="Team Leader">Team Leader</option>
                    <option value="Event Volunteer">Event Volunteer</option>
                    <option value="Medical Contact">Medical Contact</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Duty Status *</label>
                  <select
                    value={formData.dutyStatus}
                    onChange={(e) => setFormData({ ...formData, dutyStatus: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="On Duty">On Duty</option>
                    <option value="Off Duty">Off Duty</option>
                    <option value="Unavailable">Unavailable</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Assigned Venue Zone *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. North Gate / Concourse A"
                    value={formData.zone}
                    onChange={(e) => setFormData({ ...formData, zone: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Team / Organization</label>
                  <input
                    type="text"
                    placeholder="e.g. Apex Security / Arena Ops"
                    value={formData.organization}
                    onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Assigned Event</label>
                <select
                  value={formData.eventId}
                  onChange={(e) => setFormData({ ...formData, eventId: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500 font-mono"
                >
                  {events.map(ev => (
                    <option key={ev.id} value={ev.id}>{ev.title}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Responsibilities & Notes</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Responsible for turnstile verification, spectator guidance, and auxiliary corridor ingress..."
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800 font-mono">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold uppercase tracking-wider disabled:opacity-50"
                >
                  {isSubmitting ? 'Registering...' : 'Save Personnel Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: EDIT GROUND PERSONNEL */}
      {editingGuard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in font-sans">
          <div className="bg-[#0D1424] border border-cyan-500/40 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-cyan-400">
                <Edit2 className="w-5 h-5" />
                <h3 className="font-extrabold text-sm uppercase text-white font-mono">Edit Personnel Record</h3>
              </div>
              <button
                type="button"
                onClick={() => setEditingGuard(null)}
                className="text-slate-500 hover:text-white text-xs font-bold p-1"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-red-950/80 border border-red-500/40 text-red-300 text-xs flex items-center gap-2 font-mono">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Mobile (+Country Code) *</label>
                  <input
                    type="text"
                    required
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Personnel Role *</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="Security Guard">Security Guard</option>
                    <option value="Event Coordinator">Event Coordinator</option>
                    <option value="Team Leader">Team Leader</option>
                    <option value="Event Volunteer">Event Volunteer</option>
                    <option value="Medical Contact">Medical Contact</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Duty Status *</label>
                  <select
                    value={formData.dutyStatus}
                    onChange={(e) => setFormData({ ...formData, dutyStatus: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="On Duty">On Duty</option>
                    <option value="Off Duty">Off Duty</option>
                    <option value="Unavailable">Unavailable</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Assigned Venue Zone *</label>
                  <input
                    type="text"
                    required
                    value={formData.zone}
                    onChange={(e) => setFormData({ ...formData, zone: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Team / Organization</label>
                  <input
                    type="text"
                    value={formData.organization}
                    onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] uppercase font-bold text-slate-400 font-mono">Responsibilities & Notes</label>
                <textarea
                  rows={2}
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800 font-mono">
                <button
                  type="button"
                  onClick={() => setEditingGuard(null)}
                  className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold uppercase tracking-wider disabled:opacity-50"
                >
                  {isSubmitting ? 'Updating...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: DEACTIVATE CONFIRMATION */}
      {deactivatingGuard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in font-sans">
          <div className="bg-[#0D1424] border border-red-500/40 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl relative">
            <div className="flex items-center gap-3 text-red-400">
              <div className="p-2.5 rounded-full bg-red-950/80 border border-red-500/40">
                <AlertCircle className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="font-extrabold text-sm uppercase text-white font-mono">Deactivate Personnel</h3>
                <p className="text-[11px] text-slate-400">Ground staff status will be changed to Unavailable.</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-900">
              Are you sure you want to deactivate <strong className="text-white">{deactivatingGuard.name}</strong> ({deactivatingGuard.role || 'Security Guard'} at {deactivatingGuard.zone})?
              This will remove them from active deployment and mobile dispatches.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2 font-mono">
              <button
                type="button"
                onClick={() => setDeactivatingGuard(null)}
                className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white font-bold text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleDeactivate}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs uppercase tracking-wider disabled:opacity-50"
              >
                {isSubmitting ? 'Deactivating...' : 'Confirm Deactivation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
