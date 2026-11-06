import React, { useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { CrowdSystemProvider, useCrowdSystem } from './context/CrowdSystemContext';
import { Sidebar } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { EventSetup } from './pages/EventSetup';
import { CameraSetup } from './pages/CameraSetup';
import { OfficerControlPanel } from './pages/OfficerControlPanel';
import { Dashboard } from './pages/Dashboard';
import { LiveMonitoring } from './pages/LiveMonitoring';
import { CrowdAnalytics } from './pages/CrowdAnalytics';
import { DecisionSupport } from './pages/DecisionSupport';
import { ResearchAnalytics } from './pages/ResearchAnalytics';
import { AlertsPage } from './pages/AlertsPage';
import { ReportsPage } from './pages/ReportsPage';
import { CameraManagement } from './pages/CameraManagement';
import { EmergencyDashboard } from './pages/EmergencyDashboard';
import { SettingsPage } from './pages/SettingsPage';
import { StaffCommunication } from './pages/StaffCommunication';
import { VenueArchitecture } from './pages/VenueArchitecture';
import { ProfilePage } from './pages/ProfilePage';
import { MyEventPage } from './pages/MyEventPage';
import { AccountSettingsPage } from './pages/AccountSettingsPage';
import { ManagePersonnelPage } from './pages/ManagePersonnelPage';
import { HeatmapPage } from './pages/HeatmapPage';
import { LandingPage } from './pages/LandingPage';
import { AnimatePresence, motion } from 'framer-motion';

const AppContent: React.FC = () => {
  const location = useLocation();
  const { emergencyState, settings, token, onboardingStatus, isOnboardingLoading } = useCrowdSystem();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const isLoginPage = location.pathname === '/login';
  const isRegisterPage = location.pathname === '/register';
  const isLandingPage = location.pathname === '/' || location.pathname === '/landing' || location.pathname === '/home';

  // 1. Unauthenticated users -> strictly allow public pages (Landing, Login, Register), otherwise redirect to /login
  if (!token && !isLoginPage && !isRegisterPage && !isLandingPage) {
    return <Navigate to="/login" replace />;
  }

  // 2. Render Public Pages in Public Layout (No Sidebar, No Topbar)
  if (isLandingPage) {
    return <LandingPage />;
  }

  if (isLoginPage || isRegisterPage) {
    if (token) {
      return <Navigate to="/dashboard" replace />;
    }
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // 3. Loading state: avoid premature navigation during authenticated sync
  if (token && isOnboardingLoading) {
    return (
      <div className="min-h-screen bg-[#060913] flex flex-col items-center justify-center space-y-4 font-mono text-cyan-400 select-none">
        <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        <div className="text-center space-y-1">
          <p className="text-xs font-bold uppercase tracking-widest text-slate-300">
            CROWD-AI SURVEILLANCE SYSTEM
          </p>
          <p className="text-[10px] text-slate-500">
            Synchronizing operation status & live surveillance feeds...
          </p>
        </div>
      </div>
    );
  }

  // 4. Conditional Onboarding Redirect Logic (Table in Spec):
  // | Manager status | Destination |
  // | Not authenticated | Login |
  // | Authenticated, no event configured | Event Setup |
  // | Event exists, required source setup incomplete | Camera Setup |
  // | Event and source setup complete | Existing Dashboard |
  if (token && onboardingStatus) {
    // Condition A: Authenticated, no event configured -> Event Setup
    if (!onboardingStatus.has_event) {
      if (location.pathname !== '/event-setup') {
        return <Navigate to="/event-setup" replace />;
      }
    }
    // Condition B: Event exists, source setup incomplete -> Camera Setup
    else if (!onboardingStatus.has_source) {
      if (location.pathname !== '/camera-setup' && location.pathname !== '/event-setup') {
        return <Navigate to="/camera-setup" replace />;
      }
    }
    // Condition C: Setup complete -> redirect away from setup if entered directly
    else {
      if (location.pathname === '/event-setup') {
        return <Navigate to="/dashboard" replace />;
      }
    }
  }

  const isLightTheme = settings.theme === 'light';
  const contrastClass = settings.highContrast ? 'high-contrast' : '';
  const fontClass = settings.fontSize === 'sm' ? 'font-scale-sm' : settings.fontSize === 'lg' ? 'font-scale-lg' : '';
  const motionClass = settings.reducedMotion ? 'reduced-motion' : '';

  return (
    <div className={`h-screen w-screen overflow-hidden flex relative transition-colors duration-300 ${
      isLightTheme 
        ? 'light bg-slate-100 text-slate-900' 
        : emergencyState.isTriggered 
          ? 'bg-[#120406] text-white' 
          : 'bg-[#0A0E1A] text-white'
    } ${contrastClass} ${fontClass} ${motionClass}`}>
      {/* Dynamic Background Mesh Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none z-0" />

      {/* Collapsible Sidebar (Stationary left anchor) */}
      <Sidebar collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />

      {/* Main Core Layout Shell (Independently scrollable) */}
      <div 
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 h-screen overflow-y-auto overflow-x-hidden relative z-10
          ${sidebarCollapsed ? 'pl-20' : 'pl-[270px]'}`}
      >
        <Topbar />
        
        {/* Animated Page Transitions wrapper */}
        <main className="flex-1 p-6 max-w-[1600px] mx-auto w-full">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="w-full h-full"
            >
              <Routes location={location}>
                {/* Onboarding Dedicated Pages */}
                <Route path="/event-setup" element={<EventSetup />} />
                <Route path="/camera-setup" element={<CameraSetup />} />

                {/* Profile, Event & Account Routes */}
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/my-event" element={<MyEventPage />} />
                <Route path="/events" element={<MyEventPage />} />
                <Route path="/manage-personnel" element={<ManagePersonnelPage />} />
                <Route path="/personnel" element={<ManagePersonnelPage />} />
                <Route path="/account-settings" element={<AccountSettingsPage />} />
                <Route path="/settings/account" element={<AccountSettingsPage />} />
                <Route path="/settings" element={<SettingsPage />} />

                {/* Surveillance & Command Routes */}
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/officer-control" element={<OfficerControlPanel />} />
                <Route path="/live" element={<LiveMonitoring />} />
                <Route path="/live-monitoring" element={<LiveMonitoring />} />
                <Route path="/cameras" element={<CameraManagement />} />
                <Route path="/venue-architecture" element={<VenueArchitecture />} />
                <Route path="/venue" element={<VenueArchitecture />} />
                <Route path="/venue-map" element={<VenueArchitecture />} />
                <Route path="/architecture" element={<VenueArchitecture />} />
                <Route path="/staff-communication" element={<StaffCommunication />} />
                <Route path="/analytics" element={<CrowdAnalytics />} />
                <Route path="/decision-support" element={<DecisionSupport />} />
                <Route path="/alerts" element={<AlertsPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/emergency" element={<EmergencyDashboard />} />

                {/* Academic Research & Mathematical Benchmark Routes */}
                <Route path="/research-analytics" element={<ResearchAnalytics />} />
                <Route path="/research-fca" element={<ResearchAnalytics />} />

                {/* Graceful redirects for legacy URLs */}
                <Route path="/heatmap" element={<HeatmapPage />} />
                <Route path="/heatmaps" element={<Navigate to="/heatmap" replace />} />
                <Route path="/manual-analysis" element={<Navigate to="/dashboard" replace />} />
                <Route path="/offline-ai" element={<Navigate to="/dashboard" replace />} />
                <Route path="/fca" element={<Navigate to="/dashboard" replace />} />

                {/* Default route redirect to configured landing page */}
                <Route path="/" element={<Navigate to={settings.defaultLandingPage || "/dashboard"} replace />} />
                <Route path="*" element={<Navigate to={settings.defaultLandingPage || "/dashboard"} replace />} />
              </Routes>
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <CrowdSystemProvider>
      <AppContent />
    </CrowdSystemProvider>
  );
};

export default App;
