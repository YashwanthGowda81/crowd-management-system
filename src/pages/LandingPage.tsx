import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Shield, 
  Video, 
  Users, 
  AlertTriangle, 
  Cpu, 
  FileText, 
  Radio, 
  ArrowRight, 
  CheckCircle2, 
  ChevronRight, 
  Menu, 
  X, 
  Layers, 
  Lock, 
  Sparkles,
  Server,
  Activity,
  PhoneCall,
  Sliders
} from 'lucide-react';
import { useCrowdSystem } from '../context/CrowdSystemContext';

export const LandingPage: React.FC = () => {
  const { token, user } = useCrowdSystem();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[#060913] text-slate-100 font-sans selection:bg-cyan-500/30 selection:text-cyan-200 relative overflow-x-hidden">
      {/* Background ambient mesh and glow */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-0 w-full h-full opacity-20 bg-[linear-gradient(rgba(18,24,38,0.3)_1px,transparent_1px),linear-gradient(90deg,rgba(18,24,38,0.3)_1px,transparent_1px)] bg-[size:32px_32px]" />
        <div className="absolute -top-40 left-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[120px]" />
        <div className="absolute top-1/3 -right-40 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[140px]" />
        <div className="absolute bottom-10 left-1/3 w-[500px] h-[500px] bg-emerald-500/5 rounded-full blur-[130px]" />
      </div>

      {/* =========================================================================
          SECTION A: PUBLIC NAVIGATION BAR
      ========================================================================= */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#060913]/80 border-b border-cyan-500/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          {/* Logo / Brand */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => scrollToSection('hero')}>
            <div className="p-2.5 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-400 relative shadow-[0_0_15px_rgba(6,182,212,0.25)]">
              <Shield className="w-6 h-6" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-slate-950 animate-pulse" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 font-mono">
                AGY SURVEILLANCE
              </span>
              <span className="text-base font-extrabold tracking-tight text-white flex items-center gap-1.5">
                CROWD-AI <span className="text-cyan-400 font-mono text-xs px-1.5 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/30">v2.4</span>
              </span>
            </div>
          </div>

          {/* Desktop Nav Links */}
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <button onClick={() => scrollToSection('hero')} className="hover:text-cyan-400 transition-colors">
              Home
            </button>
            <button onClick={() => scrollToSection('overview')} className="hover:text-cyan-400 transition-colors">
              Overview
            </button>
            <button onClick={() => scrollToSection('features')} className="hover:text-cyan-400 transition-colors">
              Features
            </button>
            <button onClick={() => scrollToSection('how-it-works')} className="hover:text-cyan-400 transition-colors">
              How It Works
            </button>
            <button onClick={() => scrollToSection('about')} className="hover:text-cyan-400 transition-colors">
              About
            </button>
          </nav>

          {/* Auth CTA Actions */}
          <div className="hidden md:flex items-center gap-3">
            {token ? (
              <Link
                to="/dashboard"
                className="px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all duration-200 shadow-[0_0_20px_rgba(6,182,212,0.3)] flex items-center gap-2"
              >
                <span>Launch Hub ({user?.name ? user.name.split(' ')[0] : 'Operator'})</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-900/60 border border-transparent hover:border-slate-800 transition-all"
                >
                  Operator Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all duration-200 shadow-[0_0_20px_rgba(6,182,212,0.3)] flex items-center gap-1.5"
                >
                  <span>Get Started</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 focus:outline-none"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-[#0A0E1A] border-b border-cyan-500/20 px-4 pt-2 pb-6 space-y-3">
            <div className="flex flex-col space-y-2 text-sm font-medium text-slate-300">
              <button onClick={() => scrollToSection('hero')} className="text-left py-2 hover:text-cyan-400">
                Home
              </button>
              <button onClick={() => scrollToSection('overview')} className="text-left py-2 hover:text-cyan-400">
                Overview
              </button>
              <button onClick={() => scrollToSection('features')} className="text-left py-2 hover:text-cyan-400">
                Features
              </button>
              <button onClick={() => scrollToSection('how-it-works')} className="text-left py-2 hover:text-cyan-400">
                How It Works
              </button>
              <button onClick={() => scrollToSection('about')} className="text-left py-2 hover:text-cyan-400">
                About
              </button>
            </div>
            <div className="pt-4 border-t border-slate-800 flex flex-col gap-2">
              {token ? (
                <Link
                  to="/dashboard"
                  className="w-full py-2.5 text-center rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs uppercase tracking-wider"
                >
                  Enter Surveillance Hub
                </Link>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="w-full py-2.5 text-center rounded-xl bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-200"
                  >
                    Operator Sign In
                  </Link>
                  <Link
                    to="/register"
                    className="w-full py-2.5 text-center rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs uppercase tracking-wider"
                  >
                    Get Started / Register
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* =========================================================================
          SECTION B: HERO SECTION
      ========================================================================= */}
      <section id="hero" className="relative z-10 pt-16 pb-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-4xl mx-auto space-y-6">
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 text-xs font-mono font-medium tracking-wide">
            <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
            <span>ENTERPRISE CROWD INTELLIGENCE & SAFETY PIPELINE</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-[1.15]">
            Real-Time AI Crowd Surveillance & <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-blue-400">
              Predictive Evacuation Safety
            </span>
          </h1>

          {/* Subtext */}
          <p className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto font-normal leading-relaxed">
            Empowering venue command teams and safety directors with low-latency YOLOv8 person detection, multi-camera density monitoring, automated risk awareness, and coordinated security dispatch.
          </p>

          {/* CTAs */}
          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/register"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 hover:from-cyan-400 hover:to-teal-300 text-slate-950 font-extrabold text-sm uppercase tracking-wider transition-all duration-200 shadow-[0_0_25px_rgba(6,182,212,0.35)] flex items-center justify-center gap-2"
            >
              <span>Get Started / Register</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 font-semibold text-sm transition-all duration-200 border border-slate-700/80 hover:border-cyan-500/40 flex items-center justify-center gap-2"
            >
              <Lock className="w-4 h-4 text-cyan-400" />
              <span>Operator Login</span>
            </Link>
          </div>
        </div>

        {/* Visual Presentation / Dashboard Preview Mockup */}
        <div className="mt-16 relative max-w-5xl mx-auto">
          <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-3xl blur-xl opacity-20" />
          <div className="relative rounded-2xl bg-[#080D1A] border border-cyan-500/30 overflow-hidden shadow-2xl">
            {/* Mock Window Top Bar */}
            <div className="bg-[#050811] px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
                <span className="ml-2 text-xs font-mono text-slate-400">
                  AGY-Surveillance-Console :: Live-Feed-Telemetry
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs font-mono text-cyan-400">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  YOLOv8n ON-AIR
                </span>
                <span className="hidden sm:inline text-slate-500">|</span>
                <span className="hidden sm:inline text-slate-400">Round-Robin Fair Scheduler</span>
              </div>
            </div>

            {/* Mock Dashboard Grid */}
            <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Surveillance Stream Preview Illustration */}
              <div className="md:col-span-2 rounded-xl bg-slate-950 border border-slate-800/80 p-4 relative overflow-hidden flex flex-col justify-between min-h-[300px]">
                {/* Simulated Camera View Overlay */}
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(6,182,212,0.05),transparent_70%)]" />
                <div className="relative z-10 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-red-950/80 border border-red-500/40 text-[10px] font-bold text-red-400 font-mono flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
                      CAM-01 [MAIN GATE CONCOURSE]
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">1080p @ 24 FPS</span>
                  </div>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                    IoU Tracker Active
                  </span>
                </div>

                {/* Bounding Box Illustration Preview */}
                <div className="relative my-8 h-36 flex items-center justify-center">
                  <div className="grid grid-cols-3 gap-6 w-full max-w-md">
                    <div className="border border-emerald-400/80 rounded bg-emerald-500/10 p-2 text-center relative animate-pulse">
                      <span className="absolute -top-2 left-1 bg-emerald-500 text-[8px] font-mono font-bold text-slate-950 px-1 rounded">
                        ID:04 · 98%
                      </span>
                      <Users className="w-6 h-6 mx-auto text-emerald-400 mb-1" />
                      <span className="text-[9px] font-mono text-emerald-300">Pedestrian</span>
                    </div>
                    <div className="border border-cyan-400/80 rounded bg-cyan-500/10 p-2 text-center relative">
                      <span className="absolute -top-2 left-1 bg-cyan-500 text-[8px] font-mono font-bold text-slate-950 px-1 rounded">
                        ID:12 · 95%
                      </span>
                      <Users className="w-6 h-6 mx-auto text-cyan-400 mb-1" />
                      <span className="text-[9px] font-mono text-cyan-300">Pedestrian</span>
                    </div>
                    <div className="border border-amber-400/80 rounded bg-amber-500/10 p-2 text-center relative">
                      <span className="absolute -top-2 left-1 bg-amber-500 text-[8px] font-mono font-bold text-slate-950 px-1 rounded">
                        ID:19 · 92%
                      </span>
                      <Users className="w-6 h-6 mx-auto text-amber-400 mb-1" />
                      <span className="text-[9px] font-mono text-amber-300">Density Cluster</span>
                    </div>
                  </div>
                </div>

                <div className="relative z-10 flex items-center justify-between text-[11px] font-mono text-slate-400 border-t border-slate-900 pt-3">
                  <span>Inference Latency: 42ms</span>
                  <span>Active Camera Isolation: Verified</span>
                </div>
              </div>

              {/* Real Operational Stats Card Preview */}
              <div className="space-y-4">
                <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>VENUE CAPACITY MONITOR</span>
                    <Activity className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-2xl font-bold text-white font-mono">1,842 / 2,500</div>
                  <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                    <div className="bg-gradient-to-r from-emerald-500 to-amber-500 h-full w-[73%]" />
                  </div>
                  <div className="flex justify-between text-[10px] font-mono text-slate-400">
                    <span>Density: 73.6%</span>
                    <span className="text-amber-400 font-bold">STATUS: MODERATE</span>
                  </div>
                </div>

                <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>TACTICAL DISPATCH ROSTER</span>
                    <PhoneCall className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-xl font-bold text-emerald-400 font-mono">32 Guards On Duty</div>
                  <p className="text-[11px] text-slate-400">
                    Connected across North Concourse, South Gates & Evacuation Corridors.
                  </p>
                </div>

                <div className="rounded-xl bg-slate-950 border border-cyan-500/20 p-3 flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-cyan-400 shrink-0" />
                  <span className="text-xs text-slate-300 font-mono">
                    Zero Cross-Camera Mixing Guaranteed
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION C: PROJECT OVERVIEW
      ========================================================================= */}
      <section id="overview" className="relative z-10 py-20 bg-[#080D1A]/60 border-y border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-cyan-400">
              MISSION & ARCHITECTURE
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Built for High-Stakes Venue Intelligence & Safety Operations
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              AGY Surveillance provides authorized operators with a unified, real-time command dashboard designed to eliminate blind spots, detect crowd bottlenecks before stampedes occur, and coordinate response teams with mathematical certainty.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800 hover:border-cyan-500/40 transition-all space-y-4">
              <div className="w-12 h-12 rounded-xl bg-cyan-950/60 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                <Video className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Multi-Camera Feed Ingestion</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Connect and process arbitrary IP cameras, webcam inputs, or uploaded high-definition MP4 surveillance video feeds concurrently without frame mixing.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800 hover:border-cyan-500/40 transition-all space-y-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-950/60 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Users className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Continuous Density Evaluation</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Automated crowd counting compared against safe venue limits. Instant classification into Low, Medium, High, and Critical risk tiers with clear visual indicators.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800 hover:border-cyan-500/40 transition-all space-y-4">
              <div className="w-12 h-12 rounded-xl bg-blue-950/60 border border-blue-500/30 flex items-center justify-center text-blue-400">
                <Shield className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Event & Permission Isolation</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Strict multi-tenant security architecture ensuring venue managers and command officers only access feeds, guards, and analytics permitted for their event.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION D: FEATURES SECTION
      ========================================================================= */}
      <section id="features" className="relative z-10 py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-cyan-400">
            ENTERPRISE CAPABILITIES
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Comprehensive Surveillance Modules
          </h2>
          <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
            Every feature is backed by production-grade computer vision, FastAPI services, and SQLAlchemy databases.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Feature 1 */}
          <div className="p-6 rounded-2xl bg-[#080D1A] border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3">
            <div className="flex items-center justify-between">
              <Cpu className="w-6 h-6 text-cyan-400" />
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                ACTIVE
              </span>
            </div>
            <h4 className="text-base font-bold text-white">YOLOv8 Person Detection</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Real-time person bounding box overlays with temporal smoothing and IoU association to eliminate flicker.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="p-6 rounded-2xl bg-[#080D1A] border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3">
            <div className="flex items-center justify-between">
              <Server className="w-6 h-6 text-emerald-400" />
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>
            <h4 className="text-base font-bold text-white">Dynamic Multi-Video Processing</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Fair round-robin inference scheduling supporting arbitrary feeds with independent playback and camera workers.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="p-6 rounded-2xl bg-[#080D1A] border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3">
            <div className="flex items-center justify-between">
              <Layers className="w-6 h-6 text-blue-400" />
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-950 text-blue-300 border border-blue-500/30">
                ACTIVE
              </span>
            </div>
            <h4 className="text-base font-bold text-white">Venue Architecture & Mapping</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Interactive 2D architectural venue blueprints with drag-and-drop camera pins and live zone risk overlays.
            </p>
          </div>

          {/* Feature 4 */}
          <div className="p-6 rounded-2xl bg-[#080D1A] border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3">
            <div className="flex items-center justify-between">
              <AlertTriangle className="w-6 h-6 text-amber-400" />
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-500/30">
                ACTIVE
              </span>
            </div>
            <h4 className="text-base font-bold text-white">Instant Threshold Alerts & Logs</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Automated trigger generation when crowd counts cross safe limits, with audio chime alerts and incident logs.
            </p>
          </div>

          {/* Feature 5 */}
          <div className="p-6 rounded-2xl bg-[#080D1A] border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3">
            <div className="flex items-center justify-between">
              <PhoneCall className="w-6 h-6 text-purple-400" />
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-950 text-purple-300 border border-purple-500/30">
                ACTIVE
              </span>
            </div>
            <h4 className="text-base font-bold text-white">Security Staff Dispatch</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Real-time guard radio roster with assigned patrol zones, availability states, and direct directive messaging.
            </p>
          </div>

          {/* Feature 6 */}
          <div className="p-6 rounded-2xl bg-[#080D1A] border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3">
            <div className="flex items-center justify-between">
              <FileText className="w-6 h-6 text-teal-400" />
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-teal-950 text-teal-300 border border-teal-500/30">
                ACTIVE
              </span>
            </div>
            <h4 className="text-base font-bold text-white">Crowd Analytics & Reports</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Historical crowd flow graphs, peak bottleneck tracking, and downloadable audit reports for venue compliance.
            </p>
          </div>

          {/* Feature 7 */}
          <div className="p-6 rounded-2xl bg-[#080D1A] border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3">
            <div className="flex items-center justify-between">
              <Sliders className="w-6 h-6 text-cyan-400" />
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                ACTIVE
              </span>
            </div>
            <h4 className="text-base font-bold text-white">Officer Control Panel</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Dedicated tactical control page for officers with stream playback, AI module toggles, and live command directives.
            </p>
          </div>

          {/* Feature 8 (Research / Predictive module) */}
          <div className="p-6 rounded-2xl bg-[#080D1A] border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3">
            <div className="flex items-center justify-between">
              <Sparkles className="w-6 h-6 text-indigo-400" />
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-500/30">
                RESEARCH / EXPERIMENTAL
              </span>
            </div>
            <h4 className="text-base font-bold text-white">Decision Support & FCA Evacuation</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Formal Concept Analysis (FCA) mathematical models for predictive evacuation routing and multi-corridor load balancing.
            </p>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION E: HOW IT WORKS
      ========================================================================= */}
      <section id="how-it-works" className="relative z-10 py-20 bg-[#080D1A]/70 border-y border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-cyan-400">
              OPERATIONAL WORKFLOW
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              From Stream Ingestion to Evacuation Action
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              A transparent, end-to-end overview of how AGY Surveillance executes in live deployments.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Step 1 */}
            <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 relative">
              <div className="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 font-mono font-bold flex items-center justify-center border border-cyan-500/30 text-sm">
                01
              </div>
              <h4 className="text-sm font-bold text-white">Authentication</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Authorized operators log in with cryptographic credentials and role validation.
              </p>
            </div>

            {/* Step 2 */}
            <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 relative">
              <div className="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 font-mono font-bold flex items-center justify-center border border-cyan-500/30 text-sm">
                02
              </div>
              <h4 className="text-sm font-bold text-white">Event Provisioning</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Venue managers configure capacity thresholds, assign zones, and connect IP/video cameras.
              </p>
            </div>

            {/* Step 3 */}
            <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 relative">
              <div className="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 font-mono font-bold flex items-center justify-center border border-cyan-500/30 text-sm">
                03
              </div>
              <h4 className="text-sm font-bold text-white">AI Inference</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                YOLOv8 processes camera frames with temporal tracking and round-robin scheduler dispatch.
              </p>
            </div>

            {/* Step 4 */}
            <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 relative">
              <div className="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 font-mono font-bold flex items-center justify-center border border-cyan-500/30 text-sm">
                04
              </div>
              <h4 className="text-sm font-bold text-white">Density Evaluation</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Real-time counts are mapped to zone capacities to produce live risk levels and alert states.
              </p>
            </div>

            {/* Step 5 */}
            <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 relative">
              <div className="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 font-mono font-bold flex items-center justify-center border border-cyan-500/30 text-sm">
                05
              </div>
              <h4 className="text-sm font-bold text-white">Command Response</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Commanders dispatch on-duty personnel, route crowds, or initiate emergency procedures.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION F: ABOUT THE PROJECT
      ========================================================================= */}
      <section id="about" className="relative z-10 py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-cyan-400">
              ABOUT AGY SURVEILLANCE
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Ethical, Safe & Transparent Crowd Intelligence
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              AGY Surveillance — CROWD-AI v2.4 was developed to provide event organizers, stadium operators, and public safety teams with actionable situational awareness without infringing upon individual privacy.
            </p>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-300">
                  <strong className="text-white">Privacy-Preserving Geometry:</strong> Only generic pedestrian bounding boxes and density figures are calculated. No facial recognition or biometric profiling is executed.
                </p>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-300">
                  <strong className="text-white">Local Pipeline Execution:</strong> Computer vision and database operations run within dedicated infrastructure, ensuring sensitive operational video never leaves authorized bounds.
                </p>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-300">
                  <strong className="text-white">Strict Role-Based Authorization:</strong> Least-privileged operational controls safeguard sensitive event feeds and venue floorplans.
                </p>
              </div>
            </div>
          </div>

          <div className="p-8 rounded-3xl bg-[#080D1A] border border-cyan-500/20 relative space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <span className="text-xs font-mono font-bold text-slate-400">PROJECT SPECIFICATIONS</span>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-500/30">
                PRODUCTION v2.4.0
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-900">
                <span className="text-[10px] text-slate-500 block">AI INFERENCE</span>
                <span className="text-slate-200 font-bold">Ultralytics YOLOv8n</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-900">
                <span className="text-[10px] text-slate-500 block">EXECUTION</span>
                <span className="text-slate-200 font-bold">PyTorch + OpenCV</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-900">
                <span className="text-[10px] text-slate-500 block">BACKEND</span>
                <span className="text-slate-200 font-bold">FastAPI + Asyncio</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-900">
                <span className="text-[10px] text-slate-500 block">PERSISTENCE</span>
                <span className="text-slate-200 font-bold">SQLAlchemy ORM</span>
              </div>
            </div>

            <div className="pt-2">
              <Link
                to="/register"
                className="w-full py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2"
              >
                <span>Deploy Surveillance Hub</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION G: FOOTER
      ========================================================================= */}
      <footer className="relative z-10 bg-[#04060E] border-t border-slate-800/80 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            {/* Col 1 */}
            <div className="space-y-3 md:col-span-2">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
                  <Shield className="w-5 h-5" />
                </div>
                <span className="font-extrabold text-sm text-white tracking-tight">
                  AGY Surveillance — CROWD-AI v2.4
                </span>
              </div>
              <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
                Real-Time AI-Based Crowd Surveillance System with Predictive Analytics and Smart Evacuation. Built for venue commanders and municipal safety teams.
              </p>
              <div className="pt-2 flex items-center gap-2 text-[10px] font-mono text-slate-500">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Core Services Operational · Engine Ready</span>
              </div>
            </div>

            {/* Col 2 */}
            <div className="space-y-2">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">Platform</h5>
              <ul className="space-y-1.5 text-xs text-slate-400">
                <li><button onClick={() => scrollToSection('overview')} className="hover:text-cyan-400">Overview</button></li>
                <li><button onClick={() => scrollToSection('features')} className="hover:text-cyan-400">Surveillance Features</button></li>
                <li><button onClick={() => scrollToSection('how-it-works')} className="hover:text-cyan-400">System Workflow</button></li>
                <li><button onClick={() => scrollToSection('about')} className="hover:text-cyan-400">Safety & Ethics</button></li>
              </ul>
            </div>

            {/* Col 3 */}
            <div className="space-y-2">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">Access</h5>
              <ul className="space-y-1.5 text-xs text-slate-400">
                <li><Link to="/login" className="hover:text-cyan-400">Operator Sign In</Link></li>
                <li><Link to="/register" className="hover:text-cyan-400">Register New Account</Link></li>
                <li><Link to="/login" className="hover:text-cyan-400">Terminal Authentication</Link></li>
              </ul>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-900 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
            <p>© {new Date().getFullYear()} AGY Surveillance — CROWD-AI v2.4. All rights reserved.</p>
            <p className="font-mono text-[11px] text-slate-500">
              Enterprise Crowd Surveillance & Evacuation System
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};
