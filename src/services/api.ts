const getApiBaseUrl = () => {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname || 'localhost';
    return `http://${host}:8000/api`;
  }
  return 'http://localhost:8000/api';
};

const getWsBaseUrl = () => {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname || 'localhost';
    return `ws://${host}:8000/ws/live`;
  }
  return 'ws://localhost:8000/ws/live';
};

export const API_BASE_URL = getApiBaseUrl();
export const WS_BASE_URL = getWsBaseUrl();

const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const apiService = {
  // Authentication
  login: async (credentials: { email: string; password: string }) => {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Login failed');
    }
    return await res.json();
  },
  register: async (userData: { name: string; email: string; password: string; confirm_password?: string }) => {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Registration failed');
    }
    return await res.json();
  },
  getMe: async () => {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return null;
    return await res.json();
  },
  updateProfile: async (data: { name?: string; current_password?: string; new_password?: string }) => {
    const res = await fetch(`${API_BASE_URL}/auth/profile`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to update profile' }));
      throw new Error(err.detail || 'Failed to update profile');
    }
    return await res.json();
  },
  getOnboardingStatus: async (eventId?: string) => {
    const url = eventId 
      ? `${API_BASE_URL}/auth/onboarding-status?event_id=${encodeURIComponent(eventId)}` 
      : `${API_BASE_URL}/auth/onboarding-status`;
    const res = await fetch(url, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to verify onboarding status' }));
      throw new Error(err.detail || 'Failed to verify onboarding status');
    }
    return await res.json();
  },

  // Cameras
  getCameras: async (eventId?: string) => {
    const url = eventId ? `${API_BASE_URL}/cameras?event_id=${eventId}` : `${API_BASE_URL}/cameras`;
    const res = await fetch(url);
    return await res.json();
  },
  addCamera: async (camera: { name: string; rtspUrl: string; location: string; capacity?: number; resolution?: string; fps?: number; zone_id?: string; event_id?: string }) => {
    const res = await fetch(`${API_BASE_URL}/cameras`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: camera.name,
        rtsp_url: camera.rtspUrl,
        location: camera.location,
        capacity: camera.capacity || 200,
        resolution: camera.resolution || '1920x1080',
        fps: camera.fps || 30,
        zone_id: camera.zone_id,
        event_id: camera.event_id
      })
    });
    return await res.json();
  },
  addWebcamCamera: async (data?: { name?: string; location?: string; capacity?: number; zone_id?: string; event_id?: string }) => {
    const formData = new FormData();
    if (data?.name) formData.append('name', data.name);
    if (data?.location) formData.append('location', data.location);
    if (data?.capacity) formData.append('capacity', data.capacity.toString());
    if (data?.zone_id) formData.append('zone_id', data.zone_id);
    if (data?.event_id) formData.append('event_id', data.event_id);

    const res = await fetch(`${API_BASE_URL}/cameras/webcam`, {
      method: 'POST',
      body: formData
    });
    return await res.json();
  },
  uploadVideoCamera: async (file: File, name?: string, location?: string, capacity?: number, zone_id?: string, event_id?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('name', name);
    if (location) formData.append('location', location);
    if (capacity) formData.append('capacity', capacity.toString());
    if (zone_id) formData.append('zone_id', zone_id);
    if (event_id) formData.append('event_id', event_id);

    const res = await fetch(`${API_BASE_URL}/cameras/upload-video`, {
      method: 'POST',
      body: formData
    });
    return await res.json();
  },
  analyzeCamera: async (camId: string) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${camId}/analyze`, { method: 'POST' });
    return await res.json();
  },
  controlCameraPlayback: async (camId: string, action: 'analyze' | 'play' | 'pause' | 'stop' | 'restart' | 'start_analysis' | 'stop_analysis') => {
    const res = await fetch(`${API_BASE_URL}/cameras/${camId}/playback?action=${action}`, { method: 'PUT' });
    return await res.json();
  },
  getPipelineDiagnostics: async (eventId?: string, sinceId?: number) => {
    const params = new URLSearchParams();
    if (eventId) params.append('event_id', eventId);
    if (sinceId !== undefined && sinceId > 0) params.append('since_id', sinceId.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/cameras/diagnostics${query}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch pipeline diagnostics');
    }
    return await res.json();
  },
  getVenueHeatmapOverlay: async (eventId?: string, demoScenario?: string) => {
    const params = new URLSearchParams();
    if (eventId) params.append("event_id", eventId);
    if (demoScenario && demoScenario !== "live") params.append("demo_scenario", demoScenario);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${API_BASE_URL}/heatmap/venue-overlay${qs}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch venue heatmap overlay");
    }
    return await res.json();
  },
  updateCamera: async (camId: string, camera: Partial<{ name: string; rtspUrl: string; location: string; capacity: number; resolution: string; fps: number; status: string; enabled: boolean; zone_id: string; event_id: string }>) => {
    const payload: any = {};
    if (camera.name !== undefined) payload.name = camera.name;
    if (camera.rtspUrl !== undefined) payload.rtsp_url = camera.rtspUrl;
    if (camera.location !== undefined) payload.location = camera.location;
    if (camera.capacity !== undefined) payload.capacity = camera.capacity;
    if (camera.resolution !== undefined) payload.resolution = camera.resolution;
    if (camera.fps !== undefined) payload.fps = camera.fps;
    if (camera.status !== undefined) payload.status = camera.status;
    if (camera.enabled !== undefined) payload.enabled = camera.enabled;
    if (camera.zone_id !== undefined) payload.zone_id = camera.zone_id;
    if (camera.event_id !== undefined) payload.event_id = camera.event_id;

    const res = await fetch(`${API_BASE_URL}/cameras/${camId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },
  toggleCameraEnabled: async (camId: string) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${camId}/toggle-enabled`, { method: 'PUT' });
    return await res.json();
  },
  toggleCameraStatus: async (camId: string) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${camId}/toggle-status`, { method: 'PUT' });
    return await res.json();
  },
  deleteCamera: async (camId: string) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${camId}`, { method: 'DELETE' });
    return await res.json();
  },

  // Live Status & Analytics
  getLiveStatus: async (eventId?: string) => {
    const url = eventId ? `${API_BASE_URL}/live-status?event_id=${eventId}` : `${API_BASE_URL}/live-status`;
    const res = await fetch(url);
    return await res.json();
  },
  getCrowdAnalysis: async (camId?: string, eventId?: string) => {
    const params = new URLSearchParams();
    if (camId) params.append('camera_id', camId);
    if (eventId) params.append('event_id', eventId);
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/crowd-analysis${query}`);
    return await res.json();
  },

  // Alerts
  getAlerts: async (camId?: string, eventId?: string) => {
    const params = new URLSearchParams();
    if (camId) params.append('camera_id', camId);
    if (eventId) params.append('event_id', eventId);
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/alerts${query}`);
    return await res.json();
  },
  addAlert: async (alert: { title: string; description: string; level: string; zone: string; camera: string }) => {
    const res = await fetch(`${API_BASE_URL}/alerts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(alert)
    });
    return await res.json();
  },
  resolveAlert: async (alertId: string) => {
    const res = await fetch(`${API_BASE_URL}/alerts/${alertId}/resolve`, { method: 'PUT' });
    return await res.json();
  },

  // Recommendations & FCA
  getRecommendations: async (camId?: string, eventId?: string) => {
    const params = new URLSearchParams();
    if (camId) params.append('camera_id', camId);
    if (eventId) params.append('event_id', eventId);
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/recommendations${query}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return [];
    return await res.json();
  },
  getFCAResearchLattice: async (eventId?: string) => {
    const query = eventId ? `?event_id=${eventId}` : '';
    const res = await fetch(`${API_BASE_URL}/recommendations/fca-lattice${query}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return null;
    return await res.json();
  },
  getCrowdedAreas: async (eventId?: string) => {
    const query = eventId ? `?event_id=${eventId}` : '';
    const res = await fetch(`${API_BASE_URL}/recommendations/crowded-areas${query}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return [];
    return await res.json();
  },
  getPreventionPlans: async (eventId?: string) => {
    const query = eventId ? `?event_id=${eventId}` : '';
    const res = await fetch(`${API_BASE_URL}/recommendations/prevention-plans${query}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return { plans: [] };
    return await res.json();
  },
  approveRecommendation: async (recId: string) => {
    const res = await fetch(`${API_BASE_URL}/recommendations/${recId}/approve`, {
      method: 'POST',
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Approval failed (HTTP ${res.status})` }));
      const error: any = new Error(err.detail || `Approval failed (HTTP ${res.status})`);
      error.status = res.status;
      error.detail = err.detail;
      throw error;
    }
    return await res.json();
  },
  rejectRecommendation: async (recId: string, reason?: string) => {
    const res = await fetch(`${API_BASE_URL}/recommendations/${recId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ reason })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Rejection failed (HTTP ${res.status})` }));
      const error: any = new Error(err.detail || `Rejection failed (HTTP ${res.status})`);
      error.status = res.status;
      error.detail = err.detail;
      throw error;
    }
    return await res.json();
  },
  dismissRecommendation: async (recId: string) => {
    const res = await fetch(`${API_BASE_URL}/recommendations/${recId}/dismiss`, {
      method: 'POST',
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Dismissal failed (HTTP ${res.status})` }));
      const error: any = new Error(err.detail || `Dismissal failed (HTTP ${res.status})`);
      error.status = res.status;
      error.detail = err.detail;
      throw error;
    }
    return await res.json();
  },
  startDiversionInTransit: async (recId: string) => {
    const res = await fetch(`${API_BASE_URL}/recommendations/${recId}/in-transit`, {
      method: 'POST',
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Transition to in-transit failed (HTTP ${res.status})` }));
      const error: any = new Error(err.detail || `Transition to in-transit failed (HTTP ${res.status})`);
      error.status = res.status;
      error.detail = err.detail;
      throw error;
    }
    return await res.json();
  },
  completeDiversion: async (recId: string, notes?: string) => {
    const res = await fetch(`${API_BASE_URL}/recommendations/${recId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ reconciliation_notes: notes })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Completion failed (HTTP ${res.status})` }));
      const error: any = new Error(err.detail || `Completion failed (HTTP ${res.status})`);
      error.status = res.status;
      error.detail = err.detail;
      throw error;
    }
    return await res.json();
  },
  cancelDiversion: async (recId: string, body?: { reason?: string; confirm_reconciled?: boolean; reconciliation_notes?: string }) => {
    const res = await fetch(`${API_BASE_URL}/recommendations/${recId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(body || {})
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Cancellation failed (HTTP ${res.status})` }));
      const error: any = new Error(err.detail || `Cancellation failed (HTTP ${res.status})`);
      error.status = res.status;
      error.detail = err.detail;
      throw error;
    }
    return await res.json();
  },
  reconcileCancellation: async (recId: string, body: { reconciliation_notes: string; resolution_action?: 'halted' | 'redirected' | 'dispersed' }) => {
    const res = await fetch(`${API_BASE_URL}/recommendations/${recId}/reconcile-cancellation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Cancellation reconciliation failed (HTTP ${res.status})` }));
      const error: any = new Error(err.detail || `Cancellation reconciliation failed (HTTP ${res.status})`);
      error.status = res.status;
      error.detail = err.detail;
      throw error;
    }
    return await res.json();
  },
  getReservations: async (eventId?: string, statusFilter?: string) => {
    const params = new URLSearchParams();
    if (eventId) params.append('event_id', eventId);
    if (statusFilter) params.append('status_filter', statusFilter);
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/recommendations/reservations${query}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Failed to fetch reservations (HTTP ${res.status})` }));
      const error: any = new Error(err.detail || `Failed to fetch reservations (HTTP ${res.status})`);
      error.status = res.status;
      error.detail = err.detail;
      throw error;
    }
    return await res.json();
  },
  getZoneConnections: async (eventId: string) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/connections`);
    return await res.json();
  },
  createZoneConnection: async (eventId: string, data: any) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/connections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },
  updateZoneConnection: async (eventId: string, connId: string, data: any) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/connections/${connId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },
  deleteZoneConnection: async (eventId: string, connId: string) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/connections/${connId}`, {
      method: 'DELETE'
    });
    return await res.json();
  },

  // Events
  getEvents: async () => {
    const res = await fetch(`${API_BASE_URL}/events`, {
      headers: { ...getAuthHeaders() }
    });
    return await res.json();
  },
  getMyEvent: async () => {
    const res = await fetch(`${API_BASE_URL}/events/my-event`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return null;
    return await res.json();
  },
  addEvent: async (evt: { title: string; venue_name?: string; capacity: number; staff?: number; risk?: string; start_time?: string; end_time?: string; limits?: number; map_url?: string; manager_id?: number }) => {
    const res = await fetch(`${API_BASE_URL}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(evt)
    });
    return await res.json();
  },
  updateEvent: async (evtId: string, evt: Partial<{ title: string; venue_name: string; capacity: number; staff: number; risk: string; start_time: string; end_time: string; limits: number; map_url: string; manager_id: number }>) => {
    const res = await fetch(`${API_BASE_URL}/events/${evtId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(evt)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update event specifications');
    }
    return await res.json();
  },
  deleteEvent: async (evtId: string) => {
    const res = await fetch(`${API_BASE_URL}/events/${evtId}`, { 
      method: 'DELETE',
      headers: { ...getAuthHeaders() }
    });
    return await res.json();
  },

  // Zones & Sub-areas
  getZones: async (eventId: string) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/zones`);
    return await res.json();
  },
  addZone: async (eventId: string, zone: { name: string; code?: string; capacity?: number; zone_type?: string; coordinates?: string }) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/zones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(zone)
    });
    return await res.json();
  },
  updateZone: async (eventId: string, zoneId: string, zone: Partial<{ name: string; code: string; capacity: number; zone_type: string; coordinates: string }>) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/zones/${zoneId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(zone)
    });
    return await res.json();
  },
  deleteZone: async (eventId: string, zoneId: string) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/zones/${zoneId}`, { method: 'DELETE' });
    return await res.json();
  },

  // Emergency Management
  getEmergencyStatus: async (eventId?: string) => {
    const url = eventId ? `${API_BASE_URL}/emergency/status?event_id=${eventId}` : `${API_BASE_URL}/emergency/status`;
    const res = await fetch(url);
    return await res.json();
  },
  getEmergencyEvents: async (eventId?: string) => {
    const url = eventId ? `${API_BASE_URL}/emergency/events?event_id=${eventId}` : `${API_BASE_URL}/emergency/events`;
    const res = await fetch(url);
    return await res.json();
  },
  triggerEmergency: async (emg: { type: string; location: string; description: string }) => {
    const res = await fetch(`${API_BASE_URL}/emergency/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(emg)
    });
    return await res.json();
  },
  updateEmergencyEventStatus: async (eventId: string, action: string) => {
    const res = await fetch(`${API_BASE_URL}/emergency/events/${eventId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    return await res.json();
  },
  approveEmergencyDispatch: async (eventId: string) => {
    const res = await fetch(`${API_BASE_URL}/emergency/events/${eventId}/approve-dispatch`, {
      method: 'POST'
    });
    return await res.json();
  },
  resolveEmergency: async () => {
    const res = await fetch(`${API_BASE_URL}/emergency/resolve`, { method: 'PUT' });
    return await res.json();
  },
  updateEmergencyServices: async (services: { police?: string; medical?: string; fire?: string }) => {
    const query = new URLSearchParams(services as any).toString();
    const res = await fetch(`${API_BASE_URL}/emergency/services?${query}`, { method: 'PUT' });
    return await res.json();
  },
  dispatchService: async (payload: { service_type: string; event_id?: string; station_name?: string; priority?: string; notes?: string }) => {
    const res = await fetch(`${API_BASE_URL}/emergency/dispatch-service`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Emergency service dispatch failed');
    }
    return await res.json();
  },

  // Security Staff & Personnel Directory
  getStaff: async (params?: { event_id?: string; role?: string; duty_status?: string; zone?: string; search?: string; include_inactive?: boolean }) => {
    const query = new URLSearchParams();
    if (params?.event_id) query.append('event_id', params.event_id);
    if (params?.role && params.role !== 'all') query.append('role', params.role);
    if (params?.duty_status && params.duty_status !== 'all') query.append('duty_status', params.duty_status);
    if (params?.zone && params.zone !== 'all') query.append('zone', params.zone);
    if (params?.search) query.append('search', params.search);
    if (params?.include_inactive) query.append('include_inactive', 'true');
    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/staff${qs}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch security staff');
    }
    return await res.json();
  },
  createStaff: async (data: {
    name: string;
    phone: string;
    role?: string;
    event_id?: string;
    zone: string;
    organization?: string;
    duty_status?: string;
    notes?: string;
  }) => {
    const res = await fetch(`${API_BASE_URL}/staff`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to register personnel');
    }
    return await res.json();
  },
  updateStaff: async (id: string, data: Partial<{
    name: string;
    phone: string;
    role: string;
    event_id: string;
    zone: string;
    organization: string;
    duty_status: string;
    notes: string;
    is_active: boolean;
  }>) => {
    const res = await fetch(`${API_BASE_URL}/staff/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update personnel');
    }
    return await res.json();
  },
  deleteStaff: async (id: string, hardDelete: boolean = false) => {
    const res = await fetch(`${API_BASE_URL}/staff/${id}?hard_delete=${hardDelete}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to deactivate personnel');
    }
    return await res.json();
  },
  getInstructions: async () => {
    const res = await fetch(`${API_BASE_URL}/staff/instructions`);
    return await res.json();
  },
  sendInstruction: async (instruction: { recipient: string; type?: string; priority?: string; text: string }) => {
    const res = await fetch(`${API_BASE_URL}/staff/instructions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(instruction)
    });
    return await res.json();
  },

  // Ground Coordination Messages
  getCoordinationMessages: async (params?: { event_id?: string; zone?: string; recipient_id?: string; status_filter?: string }) => {
    const query = new URLSearchParams();
    if (params?.event_id) query.append('event_id', params.event_id);
    if (params?.zone && params.zone !== 'all') query.append('zone', params.zone);
    if (params?.recipient_id && params.recipient_id !== 'all') query.append('recipient_id', params.recipient_id);
    if (params?.status_filter && params.status_filter !== 'all') query.append('status_filter', params.status_filter);
    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/staff/coordination${qs}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch coordination messages');
    }
    return await res.json();
  },
  sendCoordinationMessage: async (message: {
    event_id: string;
    zone: string;
    recipient: string;
    recipient_id?: string;
    recipient_role?: string;
    camera_id?: string;
    priority?: string;
    text: string;
    status?: string;
    client_mutation_id?: string;
  }) => {
    const res = await fetch(`${API_BASE_URL}/staff/coordination`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(message)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to transmit coordination message');
    }
    return await res.json();
  },
  updateCoordinationStatus: async (messageId: string, status: string) => {
    const res = await fetch(`${API_BASE_URL}/staff/coordination/${messageId}/status`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({ status })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update coordination status');
    }
    return await res.json();
  },

  // System Settings
  getSettings: async () => {
    const res = await fetch(`${API_BASE_URL}/settings`);
    return await res.json();
  },
  updateSettings: async (settings: Partial<{ ai_sensitivity: number; crowd_threshold: number; sound_alerts: boolean; auto_escalation: boolean; fca_auto_recommendation: boolean; language: string; theme: string }>) => {
    const res = await fetch(`${API_BASE_URL}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    return await res.json();
  },

  // Venue Architecture Map & Pins
  getVenueDetails: async (eventId: string) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/venue`);
    return await res.json();
  },
  uploadVenueMap: async (eventId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/venue-map`, {
      method: 'POST',
      body: formData
    });
    return await res.json();
  },
  deleteVenueMap: async (eventId: string) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/venue-map`, { method: 'DELETE' });
    return await res.json();
  },
  addVenuePin: async (eventId: string, pin: { pin_type: string; label: string; x: number; y: number }) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/pins`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pin)
    });
    return await res.json();
  },
  deleteVenuePin: async (eventId: string, pinId: string) => {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/pins/${pinId}`, { method: 'DELETE' });
    return await res.json();
  },

  // Reports Summary
  getReports: async (eventId?: string) => {
    const url = eventId ? `${API_BASE_URL}/reports?event_id=${eventId}` : `${API_BASE_URL}/reports`;
    const res = await fetch(url);
    return await res.json();
  },

  // Download PDF Audit Report
  downloadPDFReport: (options?: { camId?: string; eventId?: string; includeCams?: boolean; includeAlerts?: boolean }) => {
    const params = new URLSearchParams();
    if (options?.camId) params.append('cam_id', options.camId);
    if (options?.eventId) params.append('event_id', options.eventId);
    if (options?.includeCams !== undefined) params.append('include_cams', options.includeCams.toString());
    if (options?.includeAlerts !== undefined) params.append('include_alerts', options.includeAlerts.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    const url = `${API_BASE_URL}/reports/pdf${query}`;
    window.open(url, '_blank');
  }
};

export class LiveWebSocketClient {
  private ws: WebSocket | null = null;
  private onMessageCallback: (data: any) => void;
  private reconnectTimer: any = null;

  constructor(onMessage: (data: any) => void) {
    this.onMessageCallback = onMessage;
  }

  public connect() {
    try {
      this.ws = new WebSocket(WS_BASE_URL);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to backend live stream server: ws://localhost:8000/ws/live');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessageCallback(data);
        } catch (e) {
          console.error('[WebSocket] Error parsing message payload', e);
        }
      };

      this.ws.onerror = () => {};

      this.ws.onclose = () => {
        this.reconnectTimer = setTimeout(() => {
          this.connect();
        }, 3000);
      };
    } catch (e) {
      this.reconnectTimer = setTimeout(() => {
        this.connect();
      }, 3000);
    }
  }

  public disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
