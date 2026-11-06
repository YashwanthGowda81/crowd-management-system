import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiService, LiveWebSocketClient } from '../services/api';

export interface Camera {
  id: string;
  name: string;
  rtspUrl: string;
  location: string;
  status: 'online' | 'offline' | 'ready';
  enabled: boolean;
  resolution: string;
  fps: number;
  lastActive: string;
  count: number;
  capacity: number;
  density: number;
  risk: 'low' | 'medium' | 'high' | 'critical';
  health: 'green' | 'yellow' | 'red';
  sourceType: 'rtsp' | 'webcam' | 'video';
  sourceFps: number;
  processingFps: number;
  playbackStatus: 'playing' | 'paused' | 'stopped' | 'analyzing' | 'ready';
  zoneId?: string;
  eventId?: string;
  isTelemetryValid?: boolean;
  observationTimestamp?: string;
  frameSeq?: number;
  detectionAgeFrames?: number;
}

export interface Zone {
  id: string;
  event_id: string;
  name: string;
  code: string;
  capacity: number;
  current_count: number;
  sensor_derived_count?: number;
  estimated_zone_count?: number;
  fov_overlap_discount_pct?: number;
  has_unique_tracking?: boolean;
  density: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  zone_type: 'gate_area' | 'corridor' | 'standing' | 'seated' | 'restricted' | 'general' | string;
  coordinates?: string;
  is_monitored?: boolean;
  monitoring_status?: 'healthy' | 'unmonitored' | 'stale' | string;
  assigned_cameras_count?: number;
}

export interface HardwareInfo {
  engine: string;
  device: string;
  isCuda: boolean;
  inferenceEngine: string;
  message: string;
}

export interface AreaSummary {
  totalCount: number; // estimated occupancy
  sensorDerivedCount?: number; // raw aggregated detections
  estimatedAreaCount?: number;
  hasUniqueTracking?: boolean;
  totalCapacity: number;
  averageDensity: number;
  overallRisk: 'low' | 'medium' | 'high' | 'critical';
  highRiskZonesCount: number;
  activeCamerasCount: number;
}

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: string;
}

export interface Alert {
  id: string;
  title: string;
  description: string;
  level: 'critical' | 'warning' | 'info';
  timestamp: string;
  zone: string;
  camera: string;
  resolved: boolean;
}

export interface CrowdEvent {
  id: string;
  title: string;
  venueName?: string;
  capacity: number;
  staff: number;
  risk: 'low' | 'medium' | 'high';
  start: string;
  end: string;
  limits: number;
  assignedCameras: string[];
  mapUrl?: string;
}

export interface EmergencyState {
  isTriggered: boolean;
  type: string;
  location: string;
  description: string;
  timestamp: string;
  police: 'dispatched' | 'standby' | 'none';
  medical: 'dispatched' | 'standby' | 'none';
  fire: 'dispatched' | 'standby' | 'none';
}

export interface EmergencyDispatch {
  id: string;
  emergency_event_id: string;
  service_type: string;
  camera_id: string;
  location: string;
  zone: string;
  message: string;
  assigned_staff_id?: string;
  staff_name?: string;
  timestamp: string;
  status: string;
}

export interface EmergencyEvent {
  id: string;
  camera_id: string;
  incident_type: string;
  severity: string;
  crowd_count: number;
  density_pct: number;
  occupancy_pct: number;
  location: string;
  zone: string;
  latitude?: number;
  longitude?: number;
  reason: string;
  detected_at: string;
  status: string;
}

export interface SystemSettings {
  aiSensitivity: number;
  crowdThreshold: number;
  soundAlerts: boolean;
  autoEscalation: boolean;
  language: string;
  theme: 'dark' | 'light' | 'system';
  
  // Client/User Preference Settings:
  defaultLandingPage: string; // '/dashboard' | '/live' | '/officer-control'
  timezone: string; // 'UTC' | 'Asia/Kolkata' | 'America/New_York' | 'Europe/London' | 'Local'
  timeFormat: '12h' | '24h';
  accentColor: 'cyan' | 'blue' | 'emerald' | 'violet' | 'amber';
  sidebarCollapsedDefault: boolean;
  compactMode: boolean;
  tablePageSize: number;
  defaultCameraGrid: '2x2' | '3x3' | '1x2' | 'auto';
  showFpsOverlay: boolean;
  showTrackIds: boolean;
  desktopNotifications: boolean;
  highContrast: boolean;
  fontSize: 'sm' | 'md' | 'lg';
  reducedMotion: boolean;
}

export type RecommendationStatus = 
  | 'pending'
  | 'approved'
  | 'in_transit'
  | 'cancellation_pending'
  | 'completed'
  | 'rejected'
  | 'dismissed'
  | 'cancelled';

export interface Recommendation {
  id: string;
  title: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  reason: string;
  confidence: number;
  zone: string;
  officer: string;
  status: RecommendationStatus;
  overrideReason?: string;
  destination_zone?: string;
  diversion_volume?: number;
  is_capacity_verified?: boolean;
  mitigation_capacity?: number;
  problemsDetected?: string[];
  suggestedAction?: string;
}

export interface CapacityReservation {
  id: string;
  recommendation_id: string;
  event_id: string;
  source_zone: string;
  destination_zone: string;
  diversion_volume: number;
  status: string;
  approved_by?: string;
  reconciliation_notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AIModule {
  id: string;
  name: string;
  enabled: boolean;
  status: 'active' | 'degraded' | 'disabled';
  health: 'green' | 'yellow' | 'red';
  lastUpdated: string;
  description: string;
}

export interface SecurityGuard {
  id: string;
  eventId?: string;
  name: string;
  role?: string;
  zone: string;
  organization?: string;
  dutyStatus?: 'On Duty' | 'Off Duty' | 'Unavailable' | string;
  isOnline: boolean;
  mobileStatus: 'connected' | 'low_battery' | 'disconnected';
  battery: number;
  phone: string;
  avatar: string;
  status: 'idle' | 'dispatched' | 'alerted';
  notes?: string;
  isActive?: boolean;
}

export interface InstructionLog {
  id: string;
  timestamp: string;
  recipient: string;
  type: 'individual' | 'group' | 'emergency';
  priority: 'normal' | 'urgent' | 'emergency';
  text: string;
  deliveryStatus: 'SENT' | 'DELIVERED' | 'FAILED';
  readStatus: 'READ' | 'UNREAD';
}

export interface CoordinationMessage {
  id: string;
  eventId?: string;
  timestamp: string;
  recipient: string;
  recipientId?: string;
  recipientRole?: string;
  zone?: string;
  cameraId?: string;
  officerName?: string;
  officerId?: number;
  type: string;
  priority: 'normal' | 'high' | 'critical';
  text: string;
  status: 'Draft' | 'Queued' | 'Internally Sent' | 'Acknowledged' | 'Failed';
  deliveryStatus?: string;
  readStatus?: string;
  channel: string;
  clientMutationId?: string;
  acknowledgedAt?: string;
}

export interface VenuePin {
  id: string;
  type: 'gate_entry' | 'gate_exit' | 'emergency_exit' | 'security' | 'medical' | 'fire' | 'restricted' | 'camera';
  label: string;
  x: number; // relative percentage
  y: number; // relative percentage
}

export interface VenueMapConfig {
  url: string;
  opacity: number;
  pins: VenuePin[];
}

export interface OnboardingStatus {
  has_event: boolean;
  event: any | null;
  has_source: boolean;
  source_count: number;
  cameras: Camera[];
  status: 'needs_event' | 'needs_source' | 'complete';
  next_route: string;
}

interface CrowdSystemContextType {
  user: AuthUser | null;
  token: string | null;
  login: (credentials: { email: string; password: string }) => Promise<OnboardingStatus | null>;
  logout: () => void;
  onboardingStatus: OnboardingStatus | null;
  isOnboardingLoading: boolean;
  checkOnboardingStatus: (eventId?: string) => Promise<OnboardingStatus | null>;
  zones: Zone[];
  fetchZones: (eventId?: string) => Promise<void>;
  fetchCameras: (eventId?: string) => Promise<void>;
  fetchAlerts: (eventId?: string) => Promise<void>;
  fetchRecommendations: (eventId?: string) => Promise<void>;
  fetchEmergencyStatus: (eventId?: string) => Promise<void>;
  addZone: (zone: { name: string; code?: string; capacity?: number; zone_type?: string; coordinates?: string }) => Promise<any>;
  updateZone: (zoneId: string, zone: Partial<{ name: string; code: string; capacity: number; zone_type: string; coordinates: string }>) => Promise<any>;
  deleteZone: (zoneId: string) => Promise<void>;
  areaSummary: AreaSummary;
  hardwareInfo: HardwareInfo;
  fetchHardwareInfo: () => Promise<void>;
  cameras: Camera[];
  alerts: Alert[];
  events: CrowdEvent[];
  emergencyState: EmergencyState;
  activeEmergencyEvent: EmergencyEvent | null;
  activeEmergencyDispatches: EmergencyDispatch[];
  activeEmergenciesCount: number;
  settings: SystemSettings;
  recommendations: Recommendation[];
  reservations: CapacityReservation[];
  fetchReservations: (eventId?: string, statusFilter?: string) => Promise<void>;
  recommendationError: string | null;
  clearRecommendationError: () => void;
  aiModules: AIModule[];
  guards: SecurityGuard[];
  refreshStaff: (eventId?: string) => Promise<void>;
  addStaffMember: (data: Partial<SecurityGuard>) => Promise<any>;
  updateStaffMember: (id: string, data: Partial<SecurityGuard>) => Promise<any>;
  deactivateStaffMember: (id: string, hardDelete?: boolean) => Promise<any>;
  instructionLogs: InstructionLog[];
  coordinationMessages: CoordinationMessage[];
  refreshCoordinationMessages: (eventId?: string) => Promise<void>;
  sendCoordinationMessage: (msg: {
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
  }) => Promise<any>;
  acknowledgeCoordinationMessage: (messageId: string) => Promise<any>;
  venueMap: VenueMapConfig;
  selectedEventId: string;
  setSelectedEventId: (id: string) => void;
  activeCameraId: string;
  setActiveCameraId: (id: string) => void;
  triggerEmergency: (type: string, location: string, description: string) => Promise<void>;
  resolveEmergency: () => Promise<void>;
  updateEmergencyEventStatus: (eventId: string, action: string) => Promise<void>;
  approveEmergencyDispatch: (eventId: string) => Promise<void>;
  updateEmergencyServices: (services: Partial<Pick<EmergencyState, 'police' | 'medical' | 'fire'>>) => Promise<void>;
  dispatchEmergencyService: (serviceType: string, stationName?: string, notes?: string) => Promise<any>;
  resolveRecommendation: (id: string) => void;
  approveRecommendation: (id: string) => Promise<{ success: boolean; message?: string; error?: string }>;
  rejectRecommendation: (id: string, reason: string) => Promise<{ success: boolean; message?: string; error?: string }>;
  dismissRecommendation: (id: string) => Promise<{ success: boolean; message?: string; error?: string }>;
  startDiversionInTransit: (id: string) => Promise<{ success: boolean; message?: string; error?: string }>;
  completeDiversion: (id: string, notes?: string) => Promise<{ success: boolean; message?: string; error?: string }>;
  cancelDiversion: (id: string, body?: { reason?: string; confirm_reconciled?: boolean; reconciliation_notes?: string }) => Promise<{ success: boolean; message?: string; error?: string; status?: string }>;
  reconcileCancellation: (id: string, body: { reconciliation_notes: string; resolution_action?: 'halted' | 'redirected' | 'dispersed' }) => Promise<{ success: boolean; message?: string; error?: string }>;
  addCamera: (camera: Omit<Camera, 'id' | 'lastActive' | 'count' | 'density' | 'risk' | 'health' | 'sourceType' | 'sourceFps' | 'processingFps' | 'playbackStatus'> & { zone_id?: string; event_id?: string }) => Promise<any>;
  addWebcamCamera: (data?: { name?: string; location?: string; capacity?: number; zone_id?: string; event_id?: string }) => Promise<any>;
  uploadVideoCamera: (file: File, name?: string, location?: string, capacity?: number, zone_id?: string, event_id?: string) => Promise<any>;
  analyzeCamera: (id: string) => Promise<void>;
  controlCameraPlayback: (camId: string, action: 'analyze' | 'play' | 'pause' | 'stop' | 'restart' | 'start_analysis' | 'stop_analysis') => Promise<void>;
  removeCamera: (id: string) => Promise<void>;
  toggleCameraStatus: (id: string) => Promise<void>;
  toggleCameraEnabled: (id: string) => Promise<void>;
  toggleAIModule: (id: string) => void;
  updateSettings: (settings: Partial<SystemSettings>) => Promise<void>;
  addAlert: (alert: Omit<Alert, 'id' | 'timestamp' | 'resolved'>) => Promise<void>;
  resolveAlert: (id: string) => Promise<void>;
  sendInstruction: (instruction: Omit<InstructionLog, 'id' | 'timestamp' | 'deliveryStatus' | 'readStatus'>) => Promise<void>;
  updateVenueMap: (config: Partial<VenueMapConfig>) => void;
  uploadVenueMapFile: (file: File) => Promise<void>;
  deleteVenueMapFile: () => Promise<void>;
  addVenuePin: (pin: { type: VenuePin['type']; label: string; x: number; y: number }) => Promise<void>;
  deleteVenuePin: (pinId: string) => Promise<void>;
  addEvent: (evt: Omit<CrowdEvent, 'id'> & { venue_name?: string }) => Promise<any>;
  updateEvent: (id: string, evt: Partial<CrowdEvent> & { venue_name?: string }) => Promise<void>;
  deleteEvent: (id: string) => Promise<void>;
  updateUserProfile: (data: { name?: string; current_password?: string; new_password?: string }) => Promise<{ success: boolean; message?: string; error?: string }>;
  currentTime: string;
  currentEvent: string;
  activeEventObj: CrowdEvent | undefined;
}

const CrowdSystemContext = createContext<CrowdSystemContextType | undefined>(undefined);

export const CrowdSystemProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentTime, setCurrentTime] = useState<string>(new Date().toLocaleTimeString());

  // User Authentication State
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem('user');
    try {
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });

  // Events State (Database-backed)
  const [events, setEvents] = useState<CrowdEvent[]>([]);
  const [selectedEventId, _setSelectedEventId] = useState<string>(() => {
    return localStorage.getItem('activeEventId') || localStorage.getItem('selectedEventId') || '';
  });

  const setSelectedEventId = (id: string) => {
    _setSelectedEventId(id);
    if (id) {
      localStorage.setItem('activeEventId', id);
      localStorage.setItem('selectedEventId', id);
    }
  };

  const selectedEventIdRef = React.useRef(selectedEventId);
  useEffect(() => {
    selectedEventIdRef.current = selectedEventId;
  }, [selectedEventId]);

  const eventsRef = React.useRef(events);
  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  // Onboarding status state
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);
  const [isOnboardingLoading, setIsOnboardingLoading] = useState<boolean>(true);

  const checkOnboardingStatus = async (eventId?: string): Promise<OnboardingStatus | null> => {
    const currentToken = localStorage.getItem('token');
    if (!currentToken) {
      setOnboardingStatus(null);
      setIsOnboardingLoading(false);
      return null;
    }
    try {
      setIsOnboardingLoading(true);
      const targetEvtId = eventId || selectedEventId || localStorage.getItem('activeEventId') || localStorage.getItem('selectedEventId') || undefined;
      const statusData = await apiService.getOnboardingStatus(targetEvtId);
      if (statusData) {
        setOnboardingStatus(statusData);
        if (statusData.event && statusData.event.id) {
          _setSelectedEventId(statusData.event.id);
          localStorage.setItem('activeEventId', statusData.event.id);
          localStorage.setItem('selectedEventId', statusData.event.id);
        }
        return statusData;
      }
      return null;
    } catch (err) {
      console.error('Error checking onboarding status:', err);
      logout();
      return null;
    } finally {
      setIsOnboardingLoading(false);
    }
  };

  const login = async (credentials: { email: string; password: string }): Promise<OnboardingStatus | null> => {
    setCameras([]);
    setAlerts([]);
    setRecommendations([]);
    setEvents([]);
    setZones([]);
    setActiveEmergencyEvent(null);
    setActiveEmergencyDispatches([]);
    const data = await apiService.login(credentials);
    if (data && data.token) {
      localStorage.setItem('token', data.token);
      const userObj = {
        id: data.id,
        email: data.email,
        name: data.name,
        role: data.role
      };
      localStorage.setItem('user', JSON.stringify(userObj));
      setToken(data.token);
      setUser(userObj);
      const statusData = await checkOnboardingStatus();
      return statusData;
    }
    return null;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('activeEventId');
    localStorage.removeItem('selectedEventId');
    setToken(null);
    setUser(null);
    setOnboardingStatus(null);
    _setSelectedEventId('');
    setCameras([]);
    setAlerts([]);
    setRecommendations([]);
    setReservations([]);
    setRecommendationError(null);
    setEvents([]);
    setZones([]);
    setActiveEmergencyEvent(null);
    setActiveEmergencyDispatches([]);
    setVenueMap({
      url: '',
      opacity: 65,
      pins: []
    });
    setAreaSummary({
      totalCount: 0,
      totalCapacity: 5000,
      averageDensity: 0,
      overallRisk: 'low',
      highRiskZonesCount: 0,
      activeCamerasCount: 0
    });
  };

  // Mount effect to check onboarding status
  useEffect(() => {
    if (token) {
      checkOnboardingStatus();
    } else {
      setIsOnboardingLoading(false);
    }
  }, [token]);


  // Zones State (Database-backed)
  const [zones, setZones] = useState<Zone[]>([]);

  // Area & Hardware Summary State
  const [areaSummary, setAreaSummary] = useState<AreaSummary>({
    totalCount: 0,
    totalCapacity: 5000,
    averageDensity: 0,
    overallRisk: 'low',
    highRiskZonesCount: 0,
    activeCamerasCount: 0
  });

  const [hardwareInfo, setHardwareInfo] = useState<HardwareInfo>({
    engine: 'Ultralytics YOLOv8',
    device: 'cpu',
    isCuda: false,
    inferenceEngine: 'PyTorch (CPU Execution Provider)',
    message: 'System running with standard CPU acceleration.'
  });

  // Cameras List State (Database is single source of truth)
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [activeCameraId, setActiveCameraId] = useState<string>('');

  // Security Staff Roster (Database-backed)
  const [guards, setGuards] = useState<SecurityGuard[]>([]);

  // Instruction Logs State (Database-backed)
  const [instructionLogs, setInstructionLogs] = useState<InstructionLog[]>([]);

  // Ground Coordination Messages State (Database-backed)
  const [coordinationMessages, setCoordinationMessages] = useState<CoordinationMessage[]>([]);

  // Alerts State (Database-backed)
  const [alerts, setAlerts] = useState<Alert[]>([]);

  // Recommendations State (Database-backed)
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [reservations, setReservations] = useState<CapacityReservation[]>([]);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const clearRecommendationError = () => setRecommendationError(null);

  // System Settings State (Database-backed + User Preferences)
  const [settings, setSettings] = useState<SystemSettings>(() => {
    let parsedLocal: any = {};
    try {
      const userStr = localStorage.getItem('user');
      const userId = userStr ? JSON.parse(userStr)?.id : 'guest';
      const localSaved = localStorage.getItem(`user_settings_${userId}`) || localStorage.getItem('app_user_settings');
      if (localSaved) {
        parsedLocal = JSON.parse(localSaved);
      }
    } catch (e) {}

    return {
      aiSensitivity: 75,
      crowdThreshold: 85,
      soundAlerts: true,
      autoEscalation: false,
      language: 'English',
      theme: 'dark',
      defaultLandingPage: '/dashboard',
      timezone: 'Local',
      timeFormat: '12h',
      accentColor: 'cyan',
      sidebarCollapsedDefault: false,
      compactMode: false,
      tablePageSize: 10,
      defaultCameraGrid: '2x2',
      showFpsOverlay: true,
      showTrackIds: true,
      desktopNotifications: true,
      highContrast: false,
      fontSize: 'md',
      reducedMotion: false,
      ...parsedLocal
    };
  });

  // Real-time clock tick respecting configured timezone and time format
  useEffect(() => {
    const formatClock = (tz?: string, fmt?: '12h' | '24h') => {
      try {
        const opts: Intl.DateTimeFormatOptions = {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: fmt !== '24h'
        };
        if (tz && tz !== 'Local') {
          opts.timeZone = tz;
        }
        return new Date().toLocaleTimeString('en-US', opts);
      } catch (e) {
        return new Date().toLocaleTimeString();
      }
    };

    setCurrentTime(formatClock(settings.timezone, settings.timeFormat));
    const timer = setInterval(() => {
      setCurrentTime(formatClock(settings.timezone, settings.timeFormat));
    }, 1000);
    return () => clearInterval(timer);
  }, [settings.timezone, settings.timeFormat]);

  // Emergency Events & Dispatches State (Database-backed)
  const [activeEmergencyEvent, setActiveEmergencyEvent] = useState<EmergencyEvent | null>(null);
  const [activeEmergencyDispatches, setActiveEmergencyDispatches] = useState<EmergencyDispatch[]>([]);
  const [activeEmergenciesCount, setActiveEmergenciesCount] = useState<number>(0);

  const [emergencyState, setEmergencyState] = useState<EmergencyState>({
    isTriggered: false,
    type: '',
    location: '',
    description: '',
    timestamp: '',
    police: 'none',
    medical: 'none',
    fire: 'none'
  });

  // Venue Architecture Map Config State
  const [venueMap, setVenueMap] = useState<VenueMapConfig>({
    url: '',
    opacity: 65,
    pins: []
  });

  // AI Inference Modules Control State
  const [aiModules, setAiModules] = useState<AIModule[]>([
    { id: 'mod-1', name: 'Human Detection (YOLOv8)', enabled: true, status: 'active', health: 'green', lastUpdated: '10ms ago', description: 'Identifies individual bounding boxes & human figures in video streams.' },
    { id: 'mod-2', name: 'Crowd Counting', enabled: true, status: 'active', health: 'green', lastUpdated: '15ms ago', description: 'Calculates real-time head count per camera frame.' },
    { id: 'mod-3', name: 'Crowd Density Estimation', enabled: true, status: 'active', health: 'green', lastUpdated: '12ms ago', description: 'Computes occupancy density % and flags high-risk bottleneck areas.' },
    { id: 'mod-5', name: 'Crowd Analytics & Velocity', enabled: true, status: 'active', health: 'green', lastUpdated: '25ms ago', description: 'Tracks entry/exit rates and detects turbulence/stagnation vectors.' },
    { id: 'mod-7', name: 'AI Decision Recommendations', enabled: true, status: 'active', health: 'green', lastUpdated: '50ms ago', description: 'Generates operational dispatch recommendations for control officers.' },
    { id: 'mod-8', name: 'Missing Child Detection', enabled: true, status: 'active', health: 'green', lastUpdated: '20ms ago', description: 'Flags unaccompanied minors separated from adult groups.' },
    { id: 'mod-9', name: 'Emergency Crisis Detection', enabled: true, status: 'active', health: 'green', lastUpdated: '8ms ago', description: 'Triggers alarm overrides on stampede, fire, or panic surges.' },
    { id: 'mod-10', name: 'Restricted Zone Intrusion', enabled: true, status: 'active', health: 'green', lastUpdated: '18ms ago', description: 'Detects perimeter breaches in VIP & backstage areas.' },
  ]);

  const fetchZones = async (eventId?: string) => {
    const targetId = eventId || selectedEventId;
    if (!targetId) return;
    try {
      const data = await apiService.getZones(targetId);
      if (Array.isArray(data)) {
        setZones(data);
      }
    } catch (e) {}
  };

  const addZone = async (zoneData: { name: string; code?: string; capacity?: number; zone_type?: string; coordinates?: string }) => {
    if (!selectedEventId) return;
    const res = await apiService.addZone(selectedEventId, zoneData);
    if (res && res.id) {
      setZones(prev => [...prev, res]);
    }
    return res;
  };

  const updateZone = async (zoneId: string, zoneData: Partial<{ name: string; code: string; capacity: number; zone_type: string; coordinates: string }>) => {
    if (!selectedEventId) return;
    const res = await apiService.updateZone(selectedEventId, zoneId, zoneData);
    if (res && res.id) {
      setZones(prev => prev.map(z => z.id === zoneId ? res : z));
    }
    return res;
  };

  const deleteZone = async (zoneId: string) => {
    if (!selectedEventId) return;
    await apiService.deleteZone(selectedEventId, zoneId);
    setZones(prev => prev.filter(z => z.id !== zoneId));
  };

  const fetchHardwareInfo = async () => {};


  const mapCameraObj = (c: any): Camera => ({
    id: c.id,
    name: c.name,
    rtspUrl: c.rtsp_url || c.rtspUrl,
    location: c.location,
    status: c.status || 'ready',
    enabled: c.enabled ?? false,
    resolution: c.resolution || '1920x1080',
    fps: c.fps || 30,
    lastActive: c.last_active || c.lastActive || 'Ready for analysis',
    count: c.count ?? 0,
    capacity: c.capacity || 200,
    density: c.density ?? 0,
    risk: c.risk || 'low',
    health: c.health || 'green',
    sourceType: (c.source_type || c.sourceType || 'video') as 'rtsp' | 'webcam' | 'video',
    sourceFps: c.source_fps || 30.0,
    processingFps: c.processing_fps || 30.0,
    playbackStatus: (c.playback_status || 'ready') as any,
    zoneId: c.zone_id || c.zoneId,
    eventId: c.event_id || c.eventId,
    isTelemetryValid: c.is_telemetry_valid !== undefined ? c.is_telemetry_valid : (c.status === 'online'),
    observationTimestamp: c.observation_timestamp,
    frameSeq: c.frame_seq,
    detectionAgeFrames: c.detection_age_frames
  });

  const fetchCameras = async (eventId?: string) => {
    const targetId = eventId !== undefined ? eventId : selectedEventId;
    try {
      const data = await apiService.getCameras(targetId || undefined);
      if (Array.isArray(data)) {
        const mapped = data.map(mapCameraObj);
        setCameras(mapped);
        setActiveCameraId(prev => {
          if (mapped.some(c => c.id === prev)) return prev;
          return mapped.length > 0 ? mapped[0].id : '';
        });
      } else {
        setCameras([]);
        setActiveCameraId('');
      }
    } catch (e) {
      setCameras([]);
      setActiveCameraId('');
    }
  };

  const fetchAlerts = async (eventId?: string) => {
    const targetId = eventId !== undefined ? eventId : selectedEventId;
    try {
      const data = await apiService.getAlerts(undefined, targetId || undefined);
      if (Array.isArray(data)) {
        setAlerts(data.map((a: any) => ({
          id: a.id,
          title: a.title,
          description: a.description,
          level: a.level,
          timestamp: a.timestamp,
          zone: a.zone,
          camera: a.camera,
          resolved: a.resolved
        })));
      } else {
        setAlerts([]);
      }
    } catch (e) {
      setAlerts([]);
    }
  };

  const fetchRecommendations = async (eventId?: string) => {
    const targetId = eventId !== undefined ? eventId : selectedEventId;
    try {
      const data = await apiService.getRecommendations(undefined, targetId || undefined);
      if (Array.isArray(data)) {
        setRecommendations(data.map((r: any) => ({
          id: r.id,
          title: r.title,
          priority: r.priority,
          reason: r.reason,
          confidence: r.confidence,
          zone: r.zone,
          officer: r.officer,
          status: r.status,
          overrideReason: r.override_reason,
          destination_zone: r.destination_zone,
          diversion_volume: r.diversion_volume,
          is_capacity_verified: r.is_capacity_verified,
          mitigation_capacity: r.mitigation_capacity,
          problemsDetected: [r.reason],
          suggestedAction: r.title
        })));
      } else {
        setRecommendations([]);
      }
    } catch (e) {
      setRecommendations([]);
    }
  };

  const fetchReservations = async (eventId?: string, statusFilter?: string) => {
    const targetId = eventId !== undefined ? eventId : selectedEventId;
    try {
      const data = await apiService.getReservations(targetId || undefined, statusFilter);
      if (Array.isArray(data)) {
        setReservations(data);
      } else {
        setReservations([]);
      }
    } catch (e) {
      setReservations([]);
    }
  };

  const fetchEmergencyStatus = async (eventId?: string) => {
    const targetId = eventId !== undefined ? eventId : selectedEventId;
    try {
      const res = await apiService.getEmergencyStatus(targetId || undefined);
      if (res && res.has_active_emergency && res.active_event) {
        setActiveEmergencyEvent(res.active_event);
        setActiveEmergencyDispatches(res.dispatches || []);
        setActiveEmergenciesCount(1);
        setEmergencyState({
          isTriggered: true,
          type: res.active_event.incident_type,
          location: res.active_event.location,
          description: res.active_event.reason,
          timestamp: res.active_event.detected_at,
          police: 'dispatched',
          medical: 'dispatched',
          fire: 'none'
        });
      } else {
        setActiveEmergencyEvent(null);
        setActiveEmergencyDispatches([]);
        setActiveEmergenciesCount(0);
        setEmergencyState({
          isTriggered: false,
          type: '',
          location: '',
          description: '',
          timestamp: '',
          police: 'none',
          medical: 'none',
          fire: 'none'
        });
      }
    } catch (e) {
      setActiveEmergencyEvent(null);
      setActiveEmergencyDispatches([]);
      setActiveEmergenciesCount(0);
    }
  };

  // Unified Database Data Loader on Mount
  useEffect(() => {
    // 1. Events
    apiService.getEvents().then(data => {
      if (Array.isArray(data)) {
        const mapped = data.map((e: any) => ({
          id: e.id,
          title: e.title,
          capacity: e.capacity,
          staff: e.staff,
          risk: e.risk,
          start: e.start_time,
          end: e.end_time,
          limits: e.limits,
          assignedCameras: [],
          mapUrl: e.map_url
        }));
        setEvents(mapped);
        const saved = localStorage.getItem('activeEventId') || localStorage.getItem('selectedEventId');
        if (saved && mapped.some((ev: any) => ev.id === saved)) {
          setSelectedEventId(saved);
        } else if (mapped.length > 0) {
          setSelectedEventId(mapped[0].id);
        }
      }
    }).catch(() => {});

    // 2. Security Staff
    apiService.getStaff({ event_id: selectedEventId || undefined }).then(data => {
      if (Array.isArray(data)) {
        setGuards(data.map((g: any) => ({
          id: g.id,
          eventId: g.event_id,
          name: g.name,
          role: g.role || 'Security Guard',
          zone: g.zone,
          organization: g.organization,
          dutyStatus: g.duty_status || 'On Duty',
          isOnline: g.is_online,
          mobileStatus: g.mobile_status,
          battery: g.battery,
          phone: g.phone,
          avatar: g.avatar,
          status: g.status,
          notes: g.notes,
          isActive: g.is_active
        })));
      }
    }).catch(() => {});

    // 3. Instruction Logs
    apiService.getInstructions().then(data => {
      if (Array.isArray(data)) {
        setInstructionLogs(data.map((i: any) => ({
          id: i.id,
          timestamp: i.timestamp,
          recipient: i.recipient,
          type: i.type,
          priority: i.priority,
          text: i.text,
          deliveryStatus: i.delivery_status,
          readStatus: i.read_status
        })));
      }
    }).catch(() => {});

    // 4. System Settings
    apiService.getSettings().then(s => {
      if (s) {
        setSettings(prev => ({
          ...prev,
          aiSensitivity: s.ai_sensitivity ?? prev.aiSensitivity,
          crowdThreshold: s.crowd_threshold ?? prev.crowdThreshold,
          soundAlerts: s.sound_alerts ?? prev.soundAlerts,
          autoEscalation: s.auto_escalation ?? prev.autoEscalation,
          language: s.language ?? prev.language,
          theme: (s.theme as any) ?? prev.theme
        }));
      }
    }).catch(() => {});
  }, []);

  const currentEvent = events.find(e => e.id === selectedEventId)?.title || (events.length > 0 ? events[0].title : 'System Active');
  const activeEventObj = events.find(e => e.id === selectedEventId) || onboardingStatus?.event;

  // Event Switcher Effect
  useEffect(() => {
    if (!selectedEventId) return;

    localStorage.setItem('activeEventId', selectedEventId);
    localStorage.setItem('selectedEventId', selectedEventId);

    // Immediately clear markers and load the selected event's map URL to prevent marker leak across events
    const eventObj = events.find(e => e.id === selectedEventId);
    setVenueMap(prev => ({
      ...prev,
      url: eventObj?.mapUrl || '',
      pins: []
    }));

    // Reset cameras and alerts immediately for clean transition
    setCameras([]);
    setActiveCameraId('');
    setAlerts([]);
    setRecommendations([]);
    setReservations([]);
    setRecommendationError(null);

    fetchZones(selectedEventId);
    fetchCameras(selectedEventId);
    fetchAlerts(selectedEventId);
    fetchRecommendations(selectedEventId);
    fetchReservations(selectedEventId);
    fetchEmergencyStatus(selectedEventId);

    apiService.getVenueDetails(selectedEventId)
      .then(res => {
        if (res) {
          const mapUrl = res.map_url || '';
          const pins = Array.isArray(res.pins) ? res.pins.map((p: any) => ({
            id: p.id,
            type: p.pin_type,
            label: p.label,
            x: p.x,
            y: p.y
          })) : [];

          setVenueMap(prev => ({
            ...prev,
            url: mapUrl,
            pins: pins
          }));

          setEvents(prev => prev.map(e => e.id === selectedEventId ? { ...e, mapUrl } : e));
        }
      })
      .catch(() => {});
  }, [selectedEventId]);

  // Venue Map Persistence Functions
  const uploadVenueMapFile = async (file: File) => {
    try {
      const res = await apiService.uploadVenueMap(selectedEventId, file);
      if (res && res.map_url) {
        setVenueMap(prev => ({
          ...prev,
          url: res.map_url,
          pins: Array.isArray(res.pins) ? res.pins.map((p: any) => ({ id: p.id, type: p.pin_type, label: p.label, x: p.x, y: p.y })) : []
        }));

        setEvents(prev => prev.map(e => e.id === selectedEventId ? { ...e, mapUrl: res.map_url } : e));
      }
    } catch (e) {
      const blobUrl = URL.createObjectURL(file);
      setVenueMap(prev => ({ ...prev, url: blobUrl }));
      setEvents(prev => prev.map(e => e.id === selectedEventId ? { ...e, mapUrl: blobUrl } : e));
    }
  };

  const deleteVenueMapFile = async () => {
    try {
      await apiService.deleteVenueMap(selectedEventId);
    } catch (e) {}
    setVenueMap(prev => ({ ...prev, url: '', pins: [] }));
    setEvents(prev => prev.map(e => e.id === selectedEventId ? { ...e, mapUrl: '' } : e));
  };

  const addVenuePin = async (pin: { type: VenuePin['type']; label: string; x: number; y: number }) => {
    try {
      const res = await apiService.addVenuePin(selectedEventId, {
        pin_type: pin.type,
        label: pin.label,
        x: pin.x,
        y: pin.y
      });
      if (res && res.id) {
        const newPin: VenuePin = { id: res.id, type: res.pin_type || pin.type, label: res.label, x: res.x, y: res.y };
        setVenueMap(prev => ({ ...prev, pins: [...prev.pins, newPin] }));
        return;
      }
    } catch (e) {}
    
    const fallbackPin: VenuePin = { id: `pin-${Date.now()}`, type: pin.type, label: pin.label, x: pin.x, y: pin.y };
    setVenueMap(prev => ({ ...prev, pins: [...prev.pins, fallbackPin] }));
  };

  const deleteVenuePin = async (pinId: string) => {
    try {
      await apiService.deleteVenuePin(selectedEventId, pinId);
    } catch (e) {}
    setVenueMap(prev => ({ ...prev, pins: prev.pins.filter(p => p.id !== pinId) }));
  };

  // Emergency Handlers (MySQL Backed)
  const triggerEmergency = async (type: string, location: string, description: string) => {
    try {
      const res = await apiService.triggerEmergency({ type, location, description });
      if (res) {
        setEmergencyState({
          isTriggered: true,
          type: type,
          location: location,
          description: description,
          timestamp: new Date().toLocaleTimeString(),
          police: 'dispatched',
          medical: 'dispatched',
          fire: 'none'
        });
      }
    } catch (e) {}
  };

  const updateEmergencyEventStatus = async (eventId: string, action: string) => {
    try {
      await apiService.updateEmergencyEventStatus(eventId, action);
      if (action.toUpperCase() === 'RESOLVED') {
        setActiveEmergencyEvent(null);
        setActiveEmergencyDispatches([]);
        setActiveEmergenciesCount(0);
        setEmergencyState({
          isTriggered: false,
          type: '',
          location: '',
          description: '',
          timestamp: '',
          police: 'none',
          medical: 'none',
          fire: 'none'
        });
      }
    } catch (e) {}
  };

  const approveEmergencyDispatch = async (eventId: string) => {
    try {
      await apiService.approveEmergencyDispatch(eventId);
      const res = await apiService.getEmergencyStatus();
      if (res && res.has_active_emergency && res.active_event) {
        setActiveEmergencyEvent(res.active_event);
        setActiveEmergencyDispatches(res.dispatches || []);
        setActiveEmergenciesCount(1);
      }
    } catch (e) {
      console.error('Failed to approve emergency dispatch:', e);
    }
  };

  const resolveEmergency = async () => {
    try {
      await apiService.resolveEmergency();
    } catch (e) {}
    setActiveEmergencyEvent(null);
    setActiveEmergencyDispatches([]);
    setActiveEmergenciesCount(0);
    setEmergencyState({
      isTriggered: false,
      type: '',
      location: '',
      description: '',
      timestamp: '',
      police: 'none',
      medical: 'none',
      fire: 'none'
    });
  };

  const updateEmergencyServices = async (services: Partial<Pick<EmergencyState, 'police' | 'medical' | 'fire'>>) => {
    try {
      const res = await apiService.updateEmergencyServices(services);
      if (res) {
        setEmergencyState(prev => ({
          ...prev,
          police: res.police_status || prev.police,
          medical: res.medical_status || prev.medical,
          fire: res.fire_status || prev.fire
        }));
      }
    } catch (e) {}
  };

  // Recommendations & Capacity Reservations Handlers (Authoritative backend verification)
  const resolveRecommendation = (id: string) => {
    setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'completed' } : r));
  };

  const approveRecommendation = async (id: string): Promise<{ success: boolean; message?: string; error?: string }> => {
    try {
      setRecommendationError(null);
      const res = await apiService.approveRecommendation(id);
      setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'approved' } : r));
      if (selectedEventIdRef.current) {
        await fetchReservations(selectedEventIdRef.current);
      }
      return { success: true, message: res?.message || 'Recommendation approved and capacity reserved.' };
    } catch (err: any) {
      const msg = err.detail || err.message || 'Approval failed';
      setRecommendationError(msg);
      return { success: false, error: msg };
    }
  };

  const rejectRecommendation = async (id: string, reason: string): Promise<{ success: boolean; message?: string; error?: string }> => {
    try {
      setRecommendationError(null);
      await apiService.rejectRecommendation(id, reason);
      setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'rejected', overrideReason: reason } : r));
      if (selectedEventIdRef.current) {
        await fetchReservations(selectedEventIdRef.current);
      }
      return { success: true, message: 'Recommendation rejected.' };
    } catch (err: any) {
      const msg = err.detail || err.message || 'Rejection failed';
      setRecommendationError(msg);
      return { success: false, error: msg };
    }
  };

  const dismissRecommendation = async (id: string): Promise<{ success: boolean; message?: string; error?: string }> => {
    try {
      setRecommendationError(null);
      await apiService.dismissRecommendation(id);
      setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'dismissed' } : r));
      return { success: true, message: 'Recommendation dismissed.' };
    } catch (err: any) {
      const msg = err.detail || err.message || 'Dismissal failed';
      setRecommendationError(msg);
      return { success: false, error: msg };
    }
  };

  const startDiversionInTransit = async (id: string): Promise<{ success: boolean; message?: string; error?: string }> => {
    try {
      setRecommendationError(null);
      const res = await apiService.startDiversionInTransit(id);
      setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'in_transit' } : r));
      if (selectedEventIdRef.current) {
        await fetchReservations(selectedEventIdRef.current);
      }
      return { success: true, message: res?.message || 'Diversion confirmed in transit.' };
    } catch (err: any) {
      const msg = err.detail || err.message || 'Failed to start in-transit diversion';
      setRecommendationError(msg);
      return { success: false, error: msg };
    }
  };

  const completeDiversion = async (id: string, notes?: string): Promise<{ success: boolean; message?: string; error?: string }> => {
    try {
      setRecommendationError(null);
      const res = await apiService.completeDiversion(id, notes);
      setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'completed' } : r));
      if (selectedEventIdRef.current) {
        await fetchReservations(selectedEventIdRef.current);
      }
      return { success: true, message: res?.message || 'Diversion operation marked completed.' };
    } catch (err: any) {
      const msg = err.detail || err.message || 'Failed to complete diversion';
      setRecommendationError(msg);
      return { success: false, error: msg };
    }
  };

  const cancelDiversion = async (
    id: string, 
    body?: { reason?: string; confirm_reconciled?: boolean; reconciliation_notes?: string }
  ): Promise<{ success: boolean; message?: string; error?: string; status?: string }> => {
    try {
      setRecommendationError(null);
      const res = await apiService.cancelDiversion(id, body);
      const newStatus = res?.status || 'cancelled';
      setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: newStatus as RecommendationStatus, overrideReason: body?.reason || body?.reconciliation_notes } : r));
      if (selectedEventIdRef.current) {
        await fetchReservations(selectedEventIdRef.current);
      }
      return { success: true, message: res?.message || 'Diversion cancelled.', status: newStatus };
    } catch (err: any) {
      const msg = err.detail || err.message || 'Failed to cancel diversion';
      setRecommendationError(msg);
      return { success: false, error: msg };
    }
  };

  const reconcileCancellation = async (
    id: string, 
    body: { reconciliation_notes: string; resolution_action?: 'halted' | 'redirected' | 'dispersed' }
  ): Promise<{ success: boolean; message?: string; error?: string }> => {
    try {
      setRecommendationError(null);
      const res = await apiService.reconcileCancellation(id, body);
      setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'cancelled', overrideReason: body.reconciliation_notes } : r));
      if (selectedEventIdRef.current) {
        await fetchReservations(selectedEventIdRef.current);
      }
      return { success: true, message: res?.message || 'Cancellation reconciled and capacity released.' };
    } catch (err: any) {
      const msg = err.detail || err.message || 'Failed to reconcile cancellation';
      setRecommendationError(msg);
      return { success: false, error: msg };
    }
  };

  // MySQL Database-Backed Camera Management Handlers
  const addCamera = async (camera: Omit<Camera, 'id' | 'lastActive' | 'count' | 'density' | 'risk' | 'health' | 'sourceType' | 'sourceFps' | 'processingFps' | 'playbackStatus'> & { zone_id?: string; event_id?: string }) => {
    try {
      const res = await apiService.addCamera({
        name: camera.name,
        rtspUrl: camera.rtspUrl,
        location: camera.location,
        capacity: camera.capacity,
        resolution: camera.resolution,
        fps: camera.fps,
        zone_id: camera.zone_id,
        event_id: camera.event_id || selectedEventId
      });
      if (res && res.id) {
        const newCam = mapCameraObj(res);
        setCameras(prev => [...prev.filter(c => c.id !== newCam.id), newCam]);
        setActiveCameraId(newCam.id);
        await checkOnboardingStatus(camera.event_id || selectedEventId);
        return newCam;
      }
    } catch (e) {
      console.error('Error creating camera in MySQL DB via API:', e);
    }
  };

  const addWebcamCamera = async (data?: { name?: string; location?: string; capacity?: number; zone_id?: string; event_id?: string }) => {
    try {
      const res = await apiService.addWebcamCamera({
        ...data,
        event_id: data?.event_id || selectedEventId
      });
      if (res && res.id) {
        const newCam = mapCameraObj(res);
        setCameras(prev => [...prev.filter(c => c.id !== newCam.id), newCam]);
        setActiveCameraId(newCam.id);
        await checkOnboardingStatus(data?.event_id || selectedEventId);
        return newCam;
      }
    } catch (e) {
      console.error('Error adding webcam camera:', e);
    }
  };

  const uploadVideoCamera = async (file: File, name?: string, location?: string, capacity?: number, zone_id?: string, event_id?: string) => {
    try {
      const res = await apiService.uploadVideoCamera(file, name, location, capacity, zone_id, event_id || selectedEventId);
      if (res && res.id) {
        const newCam = mapCameraObj(res);
        setCameras(prev => [...prev.filter(c => c.id !== newCam.id), newCam]);
        setActiveCameraId(newCam.id);
        await checkOnboardingStatus(event_id || selectedEventId);
        return newCam;
      }
    } catch (e) {
      console.error('Error uploading video camera:', e);
    }
  };

  const analyzeCamera = async (camId: string) => {
    try {
      const res = await apiService.analyzeCamera(camId);
      if (res && res.id) {
        const updated = mapCameraObj(res);
        setCameras(prev => prev.map(c => c.id === camId ? updated : c));
        setActiveCameraId(camId);
      }
    } catch (e) {
      console.error('Error analyzing camera:', e);
    }
  };

  const controlCameraPlayback = async (camId: string, action: 'analyze' | 'play' | 'pause' | 'stop' | 'restart' | 'start_analysis' | 'stop_analysis') => {
    try {
      const res = await apiService.controlCameraPlayback(camId, action);
      if (res && res.id) {
        const updated = mapCameraObj(res);
        setCameras(prev => prev.map(c => c.id === camId ? updated : c));
      }
    } catch (e) {
      console.error('Error controlling playback:', e);
    }
  };

  const removeCamera = async (id: string) => {
    try {
      await apiService.deleteCamera(id);
    } catch (e) {
      console.error('Error deleting camera from MySQL DB via API:', e);
    }
    setCameras(prev => prev.filter(c => c.id !== id));
    if (activeCameraId === id) {
      setActiveCameraId('');
    }
  };

  const toggleCameraStatus = async (id: string) => {
    try {
      const res = await apiService.toggleCameraStatus(id);
      if (res && res.id) {
        setCameras(prev => prev.map(c => c.id === id ? { ...c, status: res.status, health: res.health || c.health } : c));
        return;
      }
    } catch (e) {}
    setCameras(prev => prev.map(c => c.id === id ? { ...c, status: c.status === 'online' ? 'offline' : 'online' } : c));
  };

  const toggleCameraEnabled = async (id: string) => {
    try {
      const res = await apiService.toggleCameraEnabled(id);
      if (res && res.id) {
        setCameras(prev => prev.map(c => c.id === id ? { ...c, enabled: res.enabled } : c));
        return;
      }
    } catch (e) {}
    setCameras(prev => prev.map(c => c.id === id ? { ...c, enabled: !c.enabled } : c));
  };

  const toggleAIModule = (id: string) => {
    setAiModules(prev => prev.map(m => {
      if (m.id === id) {
        const nextEnabled = !m.enabled;
        return {
          ...m,
          enabled: nextEnabled,
          status: nextEnabled ? 'active' : 'disabled',
          lastUpdated: 'Just now'
        };
      }
      return m;
    }));
  };

  // System Settings (Database-backed + User Preferences)
  const updateSettings = async (newSettings: Partial<SystemSettings>) => {
    const updated = { ...settings, ...newSettings };
    setSettings(updated);

    // Persist user-specific client preferences
    try {
      const userKey = `user_settings_${user?.id || 'guest'}`;
      localStorage.setItem(userKey, JSON.stringify(updated));
      localStorage.setItem('app_user_settings', JSON.stringify(updated));
    } catch (e) {}

    // Persist server-side database settings
    try {
      await apiService.updateSettings({
        ai_sensitivity: updated.aiSensitivity,
        crowd_threshold: updated.crowdThreshold,
        sound_alerts: updated.soundAlerts,
        auto_escalation: updated.autoEscalation,
        language: updated.language,
        theme: updated.theme
      });
    } catch (e) {}
  };

  const updateUserProfile = async (data: { name?: string; current_password?: string; new_password?: string }) => {
    try {
      const res = await apiService.updateProfile(data);
      if (res && res.id && user) {
        const updatedUser: AuthUser = {
          ...user,
          name: res.name || user.name,
          email: res.email || user.email,
          role: res.role || user.role
        };
        setUser(updatedUser);
        localStorage.setItem('user', JSON.stringify(updatedUser));
      }
      return { success: true, message: res?.message || 'Profile updated successfully.' };
    } catch (err: any) {
      return { success: false, error: err.message || 'Failed to update profile.' };
    }
  };

  // MySQL Backed Alerts
  const addAlert = async (alert: Omit<Alert, 'id' | 'timestamp' | 'resolved'>) => {
    try {
      const res = await apiService.addAlert({
        title: alert.title,
        description: alert.description,
        level: alert.level,
        zone: alert.zone,
        camera: alert.camera
      });
      if (res && res.id) {
        setAlerts(prev => [res, ...prev]);
        return;
      }
    } catch (e) {}
    const newAlert: Alert = { ...alert, id: `alert-${Date.now()}`, timestamp: new Date().toLocaleTimeString(), resolved: false };
    setAlerts(prev => [newAlert, ...prev]);
  };

  const resolveAlert = async (id: string) => {
    try {
      await apiService.resolveAlert(id);
    } catch (e) {}
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, resolved: true } : a));
  };

  // MySQL Backed Instructions
  const sendInstruction = async (instruction: Omit<InstructionLog, 'id' | 'timestamp' | 'deliveryStatus' | 'readStatus'>) => {
    try {
      const res = await apiService.sendInstruction({
        recipient: instruction.recipient,
        type: instruction.type,
        priority: instruction.priority,
        text: instruction.text
      });
      if (res && res.id) {
        setInstructionLogs(prev => [{
          id: res.id,
          timestamp: res.timestamp,
          recipient: res.recipient,
          type: res.type,
          priority: res.priority,
          text: res.text,
          deliveryStatus: res.delivery_status || 'DELIVERED',
          readStatus: res.read_status || 'READ'
        }, ...prev]);
        return;
      }
    } catch (e) {}
    const log: InstructionLog = { ...instruction, id: `inst-${Date.now()}`, timestamp: new Date().toLocaleTimeString(), deliveryStatus: 'DELIVERED', readStatus: 'UNREAD' };
    setInstructionLogs(prev => [log, ...prev]);
  };

  // Database-Backed Security Personnel & Coordinator Management
  const refreshStaff = async (eventId?: string) => {
    try {
      const targetEventId = eventId !== undefined ? eventId : selectedEventId;
      const data = await apiService.getStaff({
        event_id: targetEventId || undefined,
        include_inactive: false
      });
      if (Array.isArray(data)) {
        setGuards(data.map((g: any) => ({
          id: g.id,
          eventId: g.event_id,
          name: g.name,
          role: g.role || 'Security Guard',
          zone: g.zone,
          organization: g.organization,
          dutyStatus: g.duty_status || 'On Duty',
          isOnline: g.is_online,
          mobileStatus: g.mobile_status,
          battery: g.battery,
          phone: g.phone,
          avatar: g.avatar,
          status: g.status,
          notes: g.notes,
          isActive: g.is_active
        })));
      }
    } catch (e) {
      console.error('Failed to refresh security staff:', e);
    }
  };

  useEffect(() => {
    if (selectedEventId) {
      refreshStaff(selectedEventId);
      refreshCoordinationMessages(selectedEventId);
    }
  }, [selectedEventId]);

  const addStaffMember = async (data: Partial<SecurityGuard>) => {
    const res = await apiService.createStaff({
      name: data.name || '',
      phone: data.phone || '',
      role: data.role || 'Security Guard',
      event_id: data.eventId || selectedEventId,
      zone: data.zone || 'General',
      organization: data.organization,
      duty_status: data.dutyStatus || 'On Duty',
      notes: data.notes
    });
    await refreshStaff(selectedEventId);
    return res;
  };

  const updateStaffMember = async (id: string, data: Partial<SecurityGuard>) => {
    const payload: any = {};
    if (data.name !== undefined) payload.name = data.name;
    if (data.phone !== undefined) payload.phone = data.phone;
    if (data.role !== undefined) payload.role = data.role;
    if (data.eventId !== undefined) payload.event_id = data.eventId;
    if (data.zone !== undefined) payload.zone = data.zone;
    if (data.organization !== undefined) payload.organization = data.organization;
    if (data.dutyStatus !== undefined) payload.duty_status = data.dutyStatus;
    if (data.notes !== undefined) payload.notes = data.notes;
    if (data.isActive !== undefined) payload.is_active = data.isActive;

    const res = await apiService.updateStaff(id, payload);
    await refreshStaff(selectedEventId);
    return res;
  };

  const deactivateStaffMember = async (id: string, hardDelete: boolean = false) => {
    const res = await apiService.deleteStaff(id, hardDelete);
    await refreshStaff(selectedEventId);
    return res;
  };

  // Database-Backed Ground Coordination Guidance Messages
  const refreshCoordinationMessages = async (eventId?: string) => {
    try {
      const targetEventId = eventId !== undefined ? eventId : selectedEventId;
      const data = await apiService.getCoordinationMessages({
        event_id: targetEventId || undefined
      });
      if (Array.isArray(data)) {
        setCoordinationMessages(data.map((m: any) => ({
          id: m.id,
          eventId: m.event_id,
          timestamp: m.timestamp,
          recipient: m.recipient,
          recipientId: m.recipient_id,
          recipientRole: m.recipient_role,
          zone: m.zone,
          cameraId: m.camera_id,
          officerName: m.officer_name,
          officerId: m.officer_id,
          type: m.type,
          priority: m.priority || 'normal',
          text: m.text,
          status: m.status || 'Internally Sent',
          deliveryStatus: m.delivery_status,
          readStatus: m.read_status,
          channel: m.channel || 'internal',
          clientMutationId: m.client_mutation_id,
          acknowledgedAt: m.acknowledged_at
        })));
      }
    } catch (e) {
      console.error('Failed to refresh coordination messages:', e);
    }
  };

  const sendCoordinationMessage = async (msg: any) => {
    const res = await apiService.sendCoordinationMessage(msg);
    await refreshCoordinationMessages(selectedEventId);
    return res;
  };

  const acknowledgeCoordinationMessage = async (messageId: string) => {
    const res = await apiService.updateCoordinationStatus(messageId, 'Acknowledged');
    await refreshCoordinationMessages(selectedEventId);
    return res;
  };

  const updateVenueMap = (config: Partial<VenueMapConfig>) => {
    setVenueMap(prev => ({ ...prev, ...config }));
  };

  // MySQL Backed Events CRUD
  const addEvent = async (evt: Omit<CrowdEvent, 'id'> & { venue_name?: string }) => {
    try {
      const res = await apiService.addEvent({
        title: evt.title,
        venue_name: evt.venue_name || evt.venueName || 'Main Arena Complex',
        capacity: evt.capacity,
        staff: evt.staff,
        risk: evt.risk,
        start_time: evt.start,
        end_time: evt.end,
        limits: evt.limits,
        map_url: evt.mapUrl
      });
      if (res && res.id) {
        const newEvt: CrowdEvent = {
          id: res.id,
          title: res.title,
          venueName: res.venue_name,
          capacity: res.capacity,
          staff: res.staff,
          risk: res.risk,
          start: res.start_time,
          end: res.end_time,
          limits: res.limits,
          assignedCameras: [],
          mapUrl: res.map_url
        };
        setEvents(prev => [...prev.filter(e => e.id !== newEvt.id), newEvt]);
        setSelectedEventId(newEvt.id);
        await checkOnboardingStatus(newEvt.id);
        return newEvt;
      }
    } catch (e) {
      console.error('Error adding event:', e);
    }
    const fallbackEvt: CrowdEvent = { ...evt, id: `evt-${Date.now()}` };
    setEvents(prev => [...prev, fallbackEvt]);
    setSelectedEventId(fallbackEvt.id);
    return fallbackEvt;
  };

  const updateEvent = async (id: string, evt: Partial<CrowdEvent> & { venue_name?: string }) => {
    try {
      const res = await apiService.updateEvent(id, {
        title: evt.title,
        venue_name: (evt as any).venue_name,
        capacity: evt.capacity,
        staff: evt.staff,
        risk: evt.risk,
        start_time: evt.start,
        end_time: evt.end,
        limits: evt.limits,
        map_url: evt.mapUrl
      });
      if (res && res.id) {
        setEvents(prev => prev.map(e => e.id === id ? {
          ...e,
          title: res.title,
          capacity: res.capacity,
          staff: res.staff,
          risk: res.risk,
          start: res.start_time,
          end: res.end_time,
          limits: res.limits,
          mapUrl: res.map_url
        } : e));
        setOnboardingStatus(prev => prev ? {
          ...prev,
          event: {
            ...prev.event,
            ...res,
            start: res.start_time,
            end: res.end_time,
            mapUrl: res.map_url
          }
        } : prev);
        if (res.capacity && res.capacity > 0) {
          setAreaSummary(prev => ({ ...prev, totalCapacity: res.capacity }));
        }
        return res;
      }
    } catch (e: any) {
      console.error('Error updating event:', e);
      throw e;
    }
  };

  const dispatchEmergencyService = async (serviceType: string, stationName?: string, notes?: string) => {
    const curEventId = selectedEventIdRef.current;
    const res = await apiService.dispatchService({
      service_type: serviceType,
      event_id: curEventId || undefined,
      station_name: stationName,
      notes: notes
    });
    await fetchEmergencyStatus(curEventId || undefined);
    return res;
  };

  const deleteEvent = async (id: string) => {
    try {
      await apiService.deleteEvent(id);
    } catch (e) {}
    setEvents(prev => prev.filter(e => e.id !== id));
  };

  // Real-time WebSockets connection to Python FastAPI backend
  useEffect(() => {
    const wsClient = new LiveWebSocketClient((data) => {
      if (data && data.type === 'TELEMETRY_UPDATE') {
        const curEventId = selectedEventIdRef.current;

        // Emergency event scoping & synchronization
        if (data.active_emergency_event !== undefined) {
          if (data.active_emergency_event && curEventId) {
            const eventCamIds = new Set(
              (Array.isArray(data.cameras) ? data.cameras : [])
                .filter((c: any) => c.event_id === curEventId)
                .map((c: any) => c.id)
            );
            const matchesEvent = eventCamIds.has(data.active_emergency_event.camera_id) || data.active_emergency_event.event_id === curEventId;
            if (matchesEvent) {
              setActiveEmergencyEvent(data.active_emergency_event);
              setActiveEmergenciesCount(1);
              setEmergencyState({
                isTriggered: true,
                type: data.active_emergency_event.incident_type,
                location: data.active_emergency_event.location,
                description: data.active_emergency_event.reason,
                timestamp: data.active_emergency_event.detected_at,
                police: 'dispatched',
                medical: 'dispatched',
                fire: 'none'
              });
            } else {
              setActiveEmergencyEvent(null);
              setActiveEmergenciesCount(0);
              setEmergencyState({
                isTriggered: false,
                type: '',
                location: '',
                description: '',
                timestamp: '',
                police: 'none',
                medical: 'none',
                fire: 'none'
              });
            }
          } else if (data.active_emergency_event) {
            setActiveEmergencyEvent(data.active_emergency_event);
            setActiveEmergenciesCount(data.active_emergencies_count || 1);
            setEmergencyState({
              isTriggered: true,
              type: data.active_emergency_event.incident_type,
              location: data.active_emergency_event.location,
              description: data.active_emergency_event.reason,
              timestamp: data.active_emergency_event.detected_at,
              police: 'dispatched',
              medical: 'dispatched',
              fire: 'none'
            });
          } else {
            setActiveEmergencyEvent(null);
            setActiveEmergenciesCount(0);
            setEmergencyState({
              isTriggered: false,
              type: '',
              location: '',
              description: '',
              timestamp: '',
              police: 'none',
              medical: 'none',
              fire: 'none'
            });
          }
        }

        if (Array.isArray(data.emergency_dispatches)) {
          if (curEventId && activeEmergencyEvent === null) {
            setActiveEmergencyDispatches([]);
          } else {
            setActiveEmergencyDispatches(data.emergency_dispatches);
          }
        }

        if (Array.isArray(data.zones)) {
          const curZones = curEventId ? data.zones.filter((z: any) => z.event_id === curEventId) : data.zones;
          setZones(curZones.map((z: any) => ({
            id: z.id,
            event_id: z.event_id,
            name: z.name,
            code: z.code,
            capacity: z.capacity,
            current_count: z.current_count,
            sensor_derived_count: z.sensor_derived_count,
            estimated_zone_count: z.estimated_zone_count,
            fov_overlap_discount_pct: z.fov_overlap_discount_pct,
            has_unique_tracking: z.has_unique_tracking,
            density: z.density,
            risk_level: z.risk_level,
            zone_type: z.zone_type,
            coordinates: z.coordinates,
            is_monitored: z.is_monitored ?? (z.assigned_cameras_count > 0),
            monitoring_status: z.monitoring_status || (z.is_monitored ? 'healthy' : 'unmonitored'),
            assigned_cameras_count: z.assigned_cameras_count
          })));
        }

        if (Array.isArray(data.cameras)) {
          const relevantCams = curEventId ? data.cameras.filter((c: any) => c.event_id === curEventId) : data.cameras;

          if (relevantCams.length > 0 && Math.random() < 0.1) {
            const sample = relevantCams[0];
            console.log(`[WS-FRONTEND] selectedEventId=${curEventId} incomingCameraId=${sample.id} incomingEventId=${sample.event_id} accepted=true personCount=${sample.count} density=${sample.density}`);
          }

          setCameras(prev => {
            if (prev.length === 0 && relevantCams.length > 0) {
              return relevantCams.map(mapCameraObj);
            }
            const existingIds = new Set(prev.map(c => c.id));
            const newCams = relevantCams.filter((rc: any) => !existingIds.has(rc.id)).map(mapCameraObj);
            const updated = prev.map(c => {
              const remoteCam = data.cameras.find((rc: any) => rc.id === c.id);
              if (remoteCam) {
                return {
                  ...c,
                  count: remoteCam.count !== undefined ? remoteCam.count : c.count,
                  density: remoteCam.density !== undefined ? remoteCam.density : c.density,
                  risk: remoteCam.risk || c.risk,
                  health: remoteCam.health || c.health,
                  enabled: remoteCam.enabled !== undefined ? remoteCam.enabled : c.enabled,
                  playbackStatus: remoteCam.playback_status || c.playbackStatus,
                  sourceFps: remoteCam.source_fps || c.sourceFps || 30.0,
                  processingFps: remoteCam.processing_fps || c.processingFps || 30.0,
                  isTelemetryValid: remoteCam.is_telemetry_valid !== undefined ? remoteCam.is_telemetry_valid : c.isTelemetryValid,
                  observationTimestamp: remoteCam.observation_timestamp || c.observationTimestamp,
                  frameSeq: remoteCam.frame_seq !== undefined ? remoteCam.frame_seq : c.frameSeq,
                  detectionAgeFrames: remoteCam.detection_age_frames !== undefined ? remoteCam.detection_age_frames : c.detectionAgeFrames
                };
              }
              return c;
            });
            return [...updated, ...newCams];
          });

          // Compute event-specific areaSummary if curEventId is set, preserving authoritative backend risk
          if (curEventId) {
            const activeCams = relevantCams.filter((c: any) => c.enabled && (c.playback_status === 'analyzing' || c.playback_status === 'playing'));
            const totalCount = activeCams.reduce((sum: number, c: any) => sum + (c.count || 0), 0);
            const avgDensity = activeCams.length > 0 
              ? Math.round((activeCams.reduce((sum: number, c: any) => sum + (c.density || 0), 0) / activeCams.length) * 10) / 10 
              : 0;
            const curZones = Array.isArray(data.zones) ? data.zones.filter((z: any) => z.event_id === curEventId) : [];
            const highRiskZones = curZones.filter((z: any) => ['high', 'critical'].includes(String(z.risk_level).toLowerCase())).length;
            const currentEvt = curEventId ? eventsRef.current.find(e => e.id === curEventId) : null;
            const zoneCapSum = curZones.reduce((sum: number, z: any) => sum + (z.capacity || 0), 0);
            const totalCapacity = (currentEvt?.capacity && currentEvt.capacity > 0)
              ? currentEvt.capacity
              : (zoneCapSum > 0
                ? zoneCapSum
                : (data.area_summary?.total_capacity && data.area_summary.total_capacity > 0
                  ? data.area_summary.total_capacity
                  : 5000));
            
            // Respect authoritative backend risk from area_summary / risk_category if present
            const backendRisk = (data.area_summary?.overall_risk || data.risk_category || '').toLowerCase();
            const authoritativeRisk: 'low' | 'medium' | 'high' | 'critical' = 
              ['low', 'medium', 'high', 'critical'].includes(backendRisk) 
                ? (backendRisk as any) 
                : (avgDensity > 80 ? 'critical' : avgDensity > 60 ? 'high' : avgDensity > 30 ? 'medium' : 'low');

            setAreaSummary({
              totalCount: totalCount,
              sensorDerivedCount: totalCount,
              estimatedAreaCount: totalCount,
              totalCapacity: totalCapacity,
              averageDensity: avgDensity,
              overallRisk: authoritativeRisk,
              highRiskZonesCount: highRiskZones,
              activeCamerasCount: activeCams.length
            });
          } else if (data.area_summary) {
            setAreaSummary({
              totalCount: data.area_summary.total_count ?? data.area_summary.totalCount ?? 0,
              totalCapacity: data.area_summary.total_capacity ?? data.area_summary.totalCapacity ?? 5000,
              averageDensity: data.area_summary.average_density ?? data.area_summary.averageDensity ?? 0,
              overallRisk: data.area_summary.overall_risk ?? data.area_summary.overallRisk ?? 'low',
              highRiskZonesCount: data.area_summary.high_risk_zones_count ?? data.area_summary.highRiskZonesCount ?? 0,
              activeCamerasCount: data.area_summary.active_cameras_count ?? data.area_summary.activeCamerasCount ?? 0
            });
          }
        }

        if (data.hardware_info) {
          setHardwareInfo(data.hardware_info);
        }

        if (Array.isArray(data.recommendations)) {
          const curRecs = curEventId 
            ? data.recommendations.filter((r: any) => !r.event_id || r.event_id === curEventId)
            : data.recommendations;
          if (curRecs.length > 0) {
            setRecommendations(curRecs.map((r: any) => ({
              id: r.id,
              title: r.title,
              priority: r.priority,
              reason: r.reason,
              confidence: r.confidence,
              zone: r.zone,
              officer: r.officer,
              status: r.status,
              overrideReason: r.override_reason,
              destination_zone: r.destination_zone,
              diversion_volume: r.diversion_volume,
              is_capacity_verified: r.is_capacity_verified,
              mitigation_capacity: r.mitigation_capacity,
              problemsDetected: [r.reason],
              suggestedAction: r.title
            })));
          }
        }
      }
    });

    wsClient.connect();
    return () => wsClient.disconnect();
  }, []);

  return (
    <CrowdSystemContext.Provider value={{
      user,
      token,
      login,
      logout,
      onboardingStatus,
      isOnboardingLoading,
      checkOnboardingStatus,
      zones,
      fetchZones,
      fetchCameras,
      fetchAlerts,
      fetchRecommendations,
      fetchEmergencyStatus,
      addZone,
      updateZone,
      deleteZone,
      areaSummary,
      hardwareInfo,
      fetchHardwareInfo,
      cameras,
      alerts,
      events,
      emergencyState,
      activeEmergencyEvent,
      activeEmergencyDispatches,
      activeEmergenciesCount,
      settings,
      recommendations,
      reservations,
      fetchReservations,
      recommendationError,
      clearRecommendationError,
      aiModules,
      guards,
      refreshStaff,
      addStaffMember,
      updateStaffMember,
      deactivateStaffMember,
      instructionLogs,
      coordinationMessages,
      refreshCoordinationMessages,
      sendCoordinationMessage,
      acknowledgeCoordinationMessage,
      venueMap,
      selectedEventId,
      setSelectedEventId,
      activeCameraId,
      setActiveCameraId,
      triggerEmergency,
      resolveEmergency,
      updateEmergencyEventStatus,
      approveEmergencyDispatch,
      updateEmergencyServices,
      resolveRecommendation,
      approveRecommendation,
      rejectRecommendation,
      dismissRecommendation,
      startDiversionInTransit,
      completeDiversion,
      cancelDiversion,
      reconcileCancellation,
      addCamera,
      addWebcamCamera,
      uploadVideoCamera,
      analyzeCamera,
      controlCameraPlayback,
      removeCamera,
      toggleCameraStatus,
      toggleCameraEnabled,
      toggleAIModule,
      updateSettings,
      addAlert,
      resolveAlert,
      sendInstruction,
      updateVenueMap,
      uploadVenueMapFile,
      deleteVenueMapFile,
      addVenuePin,
      deleteVenuePin,
      addEvent,
      updateEvent,
      deleteEvent,
      dispatchEmergencyService,
      updateUserProfile,
      currentTime,
      currentEvent,
      activeEventObj
    }}>
      {children}
    </CrowdSystemContext.Provider>
  );
};

export const useCrowdSystem = () => {
  const context = useContext(CrowdSystemContext);
  if (!context) {
    throw new Error('useCrowdSystem must be used within a CrowdSystemProvider');
  }
  return context;
};
