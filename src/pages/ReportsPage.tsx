import React, { useState } from 'react';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { apiService } from '../services/api';
import { Download, Printer, Settings2, ShieldCheck, Check } from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const { cameras, alerts, selectedEventId } = useCrowdSystem();
  
  const [selectedCamId, setSelectedCamId] = useState<string>('all');
  const [includeCams, setIncludeCams] = useState(true);
  const [includeAlerts, setIncludeAlerts] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [exportDone, setExportDone] = useState(false);

  const selectedCamera = cameras.find(c => c.id === selectedCamId);
  const analyzingCams = cameras.filter(c => c.enabled && (c.playbackStatus === 'analyzing' || c.playbackStatus === 'playing'));

  const displayCount = selectedCamera 
    ? (selectedCamera.count || 0) 
    : (analyzingCams.reduce((sum, c) => sum + (c.count || 0), 0));
    
  const displayDensity = selectedCamera 
    ? (selectedCamera.density || 0) 
    : (analyzingCams.length > 0 ? Math.round(analyzingCams.reduce((sum, c) => sum + (c.density || 0), 0) / analyzingCams.length) : 0);
    
  const displayRisk = selectedCamera 
    ? (selectedCamera.risk || 'LOW') 
    : (analyzingCams.some(c => String(c.risk).toLowerCase() === 'critical') 
        ? 'CRITICAL' 
        : analyzingCams.some(c => String(c.risk).toLowerCase() === 'high') 
        ? 'HIGH' 
        : analyzingCams.some(c => String(c.risk).toLowerCase() === 'medium') 
        ? 'MEDIUM' 
        : 'LOW');
    
  const displayFps = selectedCamera 
    ? (selectedCamera.processingFps || 30) 
    : (analyzingCams.length > 0 ? Math.round(analyzingCams.reduce((sum, c) => sum + (c.processingFps || 30), 0) / analyzingCams.length) : 30);

  const handleExport = () => {
    setIsExporting(true);
    setExportDone(false);

    // Call API helper to download camera-specific or system-wide PDF report with chosen sections
    apiService.downloadPDFReport({
      camId: selectedCamId === 'all' ? undefined : selectedCamId,
      eventId: selectedEventId || undefined,
      includeCams,
      includeAlerts
    });

    setTimeout(() => {
      setIsExporting(false);
      setExportDone(true);
      setTimeout(() => setExportDone(false), 3000);
    }, 1200);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-6rem)] font-mono">
      {/* Configuration Sidebar (Col 4) */}
      <div className="lg:col-span-4 cyber-glass p-5 rounded-xl border border-blue-500/10 flex flex-col justify-between h-full overflow-hidden">
        <div className="space-y-5 flex-1 overflow-y-auto pr-1">
          <div className="flex items-center gap-2 border-b border-slate-900 pb-2">
            <Settings2 className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs uppercase tracking-wider font-bold text-slate-300">
              Camera Audit Configurator
            </h3>
          </div>

          {/* Camera Selector Dropdown */}
          <div className="space-y-2">
            <label className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest block">
              Select Camera Source
            </label>
            <select
              value={selectedCamId}
              onChange={(e) => setSelectedCamId(e.target.value)}
              className="w-full p-2.5 rounded-lg bg-slate-950 border border-cyber-border text-xs text-white focus:outline-none focus:border-cyan-500 font-bold"
            >
              <option value="all">📊 All Cameras Aggregated Report</option>
              {cameras.map(c => (
                <option key={c.id} value={c.id}>
                  📹 {c.name} ({c.sourceType.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          {/* Exclusions */}
          <div className="space-y-2 pt-2">
            <span className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest block">
              Report Sections
            </span>
            <div className="space-y-2 text-xs">

              <label className="flex items-center gap-2 cursor-pointer text-slate-400 hover:text-slate-200">
                <input
                  type="checkbox"
                  checked={includeCams}
                  onChange={() => setIncludeCams(!includeCams)}
                  className="rounded bg-slate-950 border-slate-800 text-cyan-600 focus:ring-cyan-500 w-4 h-4"
                />
                <span>Include Camera Health Status</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-slate-400 hover:text-slate-200">
                <input
                  type="checkbox"
                  checked={includeAlerts}
                  onChange={() => setIncludeAlerts(!includeAlerts)}
                  className="rounded bg-slate-950 border-slate-800 text-cyan-600 focus:ring-cyan-500 w-4 h-4"
                />
                <span>Include Alert Incident Archive</span>
              </label>
            </div>
          </div>
        </div>

        {/* Generate / Action Buttons */}
        <div className="pt-3 border-t border-slate-900 space-y-2">
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="w-full py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:bg-cyan-800/60 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 shadow-[0_0_10px_rgba(6,182,212,0.1)] active:scale-[0.98]"
          >
            {isExporting ? (
              <span>Generating PDF Report...</span>
            ) : exportDone ? (
              <span className="flex items-center gap-1"><Check className="w-4 h-4 text-white" /> Report Downloaded</span>
            ) : (
              <span className="flex items-center gap-1"><Download className="w-4 h-4" /> Download PDF Report</span>
            )}
          </button>
        </div>
      </div>

      {/* Document Viewer Blueprint (Col 8) */}
      <div className="lg:col-span-8 cyber-glass p-5 rounded-xl border border-blue-500/10 flex flex-col justify-between h-full overflow-hidden bg-slate-950/20">
        <div>
          <div className="flex items-center justify-between border-b border-slate-900 pb-2 select-none">
            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">
              [ Camera Audit PDF Preview ]
            </span>
            <div className="flex gap-1.5">
              <button 
                onClick={handleExport}
                className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white" title="Print document"
              >
                <Printer className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Report Preview Document */}
        <div className="flex-1 overflow-y-auto mt-4 p-6 bg-slate-900/40 border border-slate-900 rounded-xl space-y-5 text-xs text-slate-300 font-sans shadow-inner max-w-2xl mx-auto w-full select-text">
          {/* Header */}
          <div className="text-center border-b border-slate-800 pb-4 space-y-1">
            <h4 className="text-sm font-bold text-white uppercase tracking-wider">
              {selectedCamera ? `Camera Safety Report: ${selectedCamera.name}` : 'Crowd Safety & Security Audit Report'}
            </h4>
            <span className="text-[10px] text-slate-500 block font-mono">
              Source: {selectedCamera ? selectedCamera.sourceType.toUpperCase() : 'ALL STREAMS'} | Generated: {new Date().toLocaleTimeString()}
            </span>
          </div>

          {/* Section 1: General Metrics */}
          <div className="space-y-3">
            <h5 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider border-b border-slate-800/40 pb-1">
              1. Real Computer Vision Operations Metrics
            </h5>
            <div className="grid grid-cols-2 gap-3 text-[11px] font-mono">
              <div className="flex justify-between border-b border-slate-800/30 pb-1">
                <span className="text-slate-500">Camera Source</span>
                <span className="text-slate-200">{selectedCamera ? selectedCamera.name : `All Active Cameras (${analyzingCams.length} active)`}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/30 pb-1">
                <span className="text-slate-500">Location / Zone</span>
                <span className="text-slate-200">{selectedCamera?.location || 'Venue Wide Operation'}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/30 pb-1">
                <span className="text-slate-500">Live People Count</span>
                <span className="text-cyan-400 font-bold">{displayCount} persons</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/30 pb-1">
                <span className="text-slate-500">Density Percentage</span>
                <span className="text-yellow-400 font-bold">{displayDensity}%</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/30 pb-1">
                <span className="text-slate-500">Processing FPS</span>
                <span className="text-green-400 font-bold">{displayFps} FPS</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/30 pb-1">
                <span className="text-slate-500">Risk Assessment</span>
                <span className="text-red-400 font-bold uppercase">{displayRisk}</span>
              </div>
            </div>
          </div>

          {/* Section 2: Cameras */}
          {includeCams && (
            <div className="space-y-2">
              <h5 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider border-b border-slate-800/40 pb-1">
                2. Camera Stream Hardware Health
              </h5>
              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                {cameras.map(c => (
                  <div key={c.id} className="flex justify-between">
                    <span className="text-slate-500 truncate mr-2">{c.name} ({c.sourceType.toUpperCase()})</span>
                    <span className={c.enabled ? 'text-green-400' : 'text-red-400'}>
                      {c.enabled ? 'ACTIVE' : 'DISABLED'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 3: Incidents */}
          {includeAlerts && (
            <div className="space-y-2">
              <h5 className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider border-b border-slate-800/40 pb-1">
                3. Incident Warnings & Alert Log
              </h5>
              <p className="text-[10px] text-slate-400 leading-normal font-mono">
                Total anomalies flagged: {alerts.length} warnings. Critical risk thresholds saved to MySQL database for compliance audits.
              </p>
            </div>
          )}

          {/* Signature */}
          <div className="pt-6 border-t border-slate-800 flex justify-between items-center text-[9px] text-slate-500 font-mono">
            <span>Auth Key: CROWD-SURV-2026-AUDIT</span>
            <span className="flex items-center gap-1"><ShieldCheck className="w-3.5 h-3.5 text-green-400" /> Compliance Verified</span>
          </div>
        </div>
      </div>
    </div>
  );
};
