import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Shield, Eye, EyeOff, Radio, Lock, Mail, CheckCircle2, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';

import { useCrowdSystem } from '../context/CrowdSystemContext';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useCrowdSystem();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Success message passed from registration page or other redirects
  const successMsg = location.state?.message;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    try {
      const statusData = await login({ email, password });
      if (statusData && statusData.next_route) {
        navigate(statusData.next_route, { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-screen bg-[#060913] flex items-center justify-center p-4 overflow-hidden">
      {/* Animated Matrix-like Background Particles */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-0 left-0 w-full h-full opacity-20 bg-[linear-gradient(rgba(18,24,38,0.3)_1px,transparent_1px),linear-gradient(90deg,rgba(18,24,38,0.3)_1px,transparent_1px)] bg-[size:24px_24px]" />
        
        {/* Floating Ambient Blobs */}
        <motion.div 
          animate={{ x: [0, 80, 0], y: [0, -80, 0] }}
          transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-blue-900/10 filter blur-3xl"
        />
        <motion.div 
          animate={{ x: [0, -60, 0], y: [0, 60, 0] }}
          transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-cyan-950/15 filter blur-3xl"
        />
      </div>

      {/* Main Glass Login Card */}
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="w-full max-w-[460px] cyber-glass-glow p-8 rounded-2xl border border-blue-500/20 relative z-10 space-y-6"
      >
        {/* Back Link to Home */}
        <div className="flex justify-start -mt-2 -mb-2">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 transition-colors font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Public Home</span>
          </Link>
        </div>

        {/* Cyber Brand Logo */}
        <div className="flex flex-col items-center text-center space-y-2 select-none">
          <div className="p-3.5 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 text-cyan-400 relative">
            <Shield className="w-8 h-8" />
            <span className="absolute top-0 right-0 w-2.5 h-2.5 rounded-full bg-green-400 border-2 border-slate-950 animate-pulse" />
          </div>
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">SURVEILLANCE CONTROL PANEL</span>
            <h1 className="text-xl font-bold text-white tracking-tight leading-tight">
              AI-Based Real-Time Crowd Management & Safety System
            </h1>
            <p className="text-[10px] text-cyan-400/90 max-w-[340px] mx-auto leading-normal">
              Real-Time Computer Vision · Predictive Analytics · Decision Support
            </p>
          </div>
        </div>

        {/* Success message banner */}
        {successMsg && !errorMsg && (
          <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs flex items-center gap-2 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Error message banner */}
        {errorMsg && (
          <div className="p-3 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs text-center font-medium animate-shake">
            {errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {/* Email input */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
              Operator Email Address
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Mail className="w-4 h-4" />
              </span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
                placeholder="ops@surveillance.gov"
              />
            </div>
          </div>

          {/* Password input */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                Security Password
              </label>
              <span className="text-[10px] text-cyan-500/80 hover:text-cyan-400 cursor-pointer font-semibold">
                Forgot?
              </span>
            </div>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Lock className="w-4 h-4" />
              </span>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
                placeholder="••••••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Remember me */}
          <div className="flex items-center justify-between text-xs pt-1 select-none">
            <label className="flex items-center gap-2 cursor-pointer text-slate-400 hover:text-slate-300">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={() => setRememberMe(!rememberMe)}
                className="rounded bg-slate-950 border-slate-800 text-cyan-600 focus:ring-cyan-500 focus:ring-offset-slate-950 w-4 h-4"
              />
              <span>Remember this terminal</span>
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:bg-cyan-800/50 text-white font-bold text-xs uppercase tracking-wider transition-all duration-300 border border-cyan-500/20 active:scale-[0.98] flex justify-center items-center gap-2 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
          >
            {loading ? (
              <>
                <Radio className="w-4 h-4 animate-spin text-white" />
                <span>Decrypting Tokens...</span>
              </>
            ) : (
              <span>Authenticate & Enter Hub</span>
            )}
          </button>
        </form>

        {/* Register Account Navigation */}
        <div className="text-center pt-2">
          <p className="text-xs text-slate-400">
            Don't have an operator account?{' '}
            <Link
              to="/register"
              className="text-cyan-400 hover:text-cyan-300 font-semibold hover:underline transition-colors"
            >
              Register New Account
            </Link>
          </p>
        </div>

        <div className="pt-2 text-center border-t border-slate-900">
          <span className="text-[9px] text-slate-500 uppercase tracking-widest font-mono">
            SECURE CONNECTION · ISO 27001 COMPLIANT
          </span>
        </div>
      </motion.div>
    </div>
  );
};
