import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Eye, EyeOff, Radio, Lock, Mail, User, CheckCircle2, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';
import { apiService } from '../services/api';

export const Register: React.FC = () => {
  const navigate = useNavigate();

  // Form State - strictly empty initially (no prefilled credentials)
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Password Visibility
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Status & Validation
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    // Client-side validations
    const trimmedName = name.trim();
    if (!trimmedName || trimmedName.length < 2) {
      setErrorMsg('Full name must be at least 2 characters long.');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setErrorMsg('Please provide a valid operator email address.');
      return;
    }

    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match. Please verify and re-enter.');
      return;
    }

    setLoading(true);

    try {
      await apiService.register({
        name: trimmedName,
        email: email.trim().toLowerCase(),
        password,
        confirm_password: confirmPassword
      });

      // Redirect to login with success feedback
      navigate('/login', {
        state: {
          message: 'Account registered successfully! Please sign in with your credentials.'
        },
        replace: true
      });
    } catch (err: any) {
      setErrorMsg(err.message || 'Registration failed. Please check your information and try again.');
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

      {/* Main Glass Register Card */}
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="w-full max-w-[480px] cyber-glass-glow p-8 rounded-2xl border border-blue-500/20 relative z-10 space-y-5"
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
            <span className="absolute top-0 right-0 w-2.5 h-2.5 rounded-full bg-cyan-400 border-2 border-slate-950 animate-pulse" />
          </div>
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">OPERATOR PROVISIONING</span>
            <h1 className="text-xl font-bold text-white tracking-tight leading-tight">
              Create Surveillance Account
            </h1>
            <p className="text-[10px] text-cyan-400/90 max-w-[340px] mx-auto leading-normal">
              Register as an authorized surveillance operator / event manager.
            </p>
          </div>
        </div>

        {/* Error message banner */}
        {errorMsg && (
          <div className="p-3 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs text-center font-medium animate-shake">
            {errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5 pt-1">
          {/* Full Name input */}
          <div className="space-y-1">
            <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
              Full Name
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <User className="w-4 h-4" />
              </span>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-cyber-border text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
                placeholder="Officer John Doe"
                disabled={loading}
              />
            </div>
          </div>

          {/* Email input */}
          <div className="space-y-1">
            <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
              Email Address
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
                placeholder="officer.doe@smartcity.gov"
                disabled={loading}
              />
            </div>
          </div>

          {/* Password input */}
          <div className="space-y-1">
            <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
              Password <span className="text-slate-500 lowercase font-normal">(min 8 characters)</span>
            </label>
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
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Confirm Password input */}
          <div className="space-y-1">
            <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
              Confirm Password
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Lock className="w-4 h-4" />
              </span>
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-950 border text-xs text-white placeholder-slate-600 focus:outline-none transition-colors ${
                  confirmPassword && confirmPassword !== password 
                    ? 'border-red-500/60 focus:border-red-500' 
                    : confirmPassword && confirmPassword === password 
                      ? 'border-green-500/60 focus:border-green-500'
                      : 'border-cyber-border focus:border-cyan-500/50'
                }`}
                placeholder="••••••••••••"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300"
                tabIndex={-1}
              >
                {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {confirmPassword && confirmPassword === password && (
              <p className="text-[10px] text-green-400 flex items-center gap-1 font-mono pt-0.5">
                <CheckCircle2 className="w-3 h-3 text-green-400" />
                <span>Passwords match</span>
              </p>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-3 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:bg-cyan-800/50 text-white font-bold text-xs uppercase tracking-wider transition-all duration-300 border border-cyan-500/20 active:scale-[0.98] flex justify-center items-center gap-2 shadow-[0_0_15px_rgba(6,182,212,0.2)] cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Radio className="w-4 h-4 animate-spin text-white" />
                <span>Registering Account...</span>
              </>
            ) : (
              <span>Create Account & Continue</span>
            )}
          </button>
        </form>

        {/* Link back to Login */}
        <div className="pt-2 text-center border-t border-slate-900 flex flex-col items-center gap-2">
          <p className="text-xs text-slate-400">
            Already have an operator account?{' '}
            <Link to="/login" className="text-cyan-400 hover:text-cyan-300 font-bold hover:underline">
              Sign In Here
            </Link>
          </p>
          <span className="text-[9px] text-slate-500 uppercase tracking-widest font-mono">
            SECURE CONNECTION · ISO 27001 COMPLIANT
          </span>
        </div>
      </motion.div>
    </div>
  );
};
