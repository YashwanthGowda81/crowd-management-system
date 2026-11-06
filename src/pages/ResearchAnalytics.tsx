import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCrowdSystem } from '../context/CrowdSystemContext';
import { apiService } from '../services/api';
import { 
  Cpu, 
  GitBranch, 
  Compass, 
  ArrowRight, 
  Activity, 
  RotateCcw, 
  FileText,
  AlertTriangle,
  ChevronLeft
} from 'lucide-react';

export const ResearchAnalytics: React.FC = () => {
  const navigate = useNavigate();
  const { cameras, selectedEventId } = useCrowdSystem();
  const [activeTab, setActiveTab] = useState<'algorithms' | 'lattices'>('algorithms');
  const [researchData, setResearchData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const analyzingCams = cameras.filter(c => c.enabled && (c.playbackStatus === 'analyzing' || c.playbackStatus === 'playing'));

  const fetchResearchData = async () => {
    setIsLoading(true);
    try {
      const data = await apiService.getFCAResearchLattice(selectedEventId || undefined);
      setResearchData(data);
    } catch (err) {
      console.warn("Could not fetch research FCA lattice data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchResearchData();
    const interval = setInterval(fetchResearchData, 15000);
    return () => clearInterval(interval);
  }, [selectedEventId]);

  const crowdedAreas = researchData?.crowded_areas || [];
  const preventionPlans = researchData?.prevention_plans || [];
  const crowdLattice = researchData?.crowd_lattice;
  const areaLattice = researchData?.area_lattice;
  const fuzzySummary = researchData?.fuzzy_context_summary || {};

  return (
    <div className="space-y-6 pb-12 font-mono">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border pb-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs mb-1">
            <Cpu className="w-4 h-4" />
            <span>ACADEMIC RESEARCH & FORMAL CONCEPT ANALYSIS BENCHMARK</span>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            Algorithm 1, Algorithm 2 & Concept Lattices (Lc / La)
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            IEEE Access 2025 research evaluation interface: Formal Concept Analysis (FCA) mathematical lattices,
            Fuzzy Formal Context Kc (Table 2), Algorithm 1 crowded-area derivations, and Algorithm 2 prevention subplans.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/decision-support')}
            className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-cyan-400 font-bold flex items-center gap-1.5 transition-all"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Return to Operational Directives</span>
          </button>
          <div className="px-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="text-slate-500">Active Streams: </span>
            <span className="text-cyan-400 font-extrabold text-sm ml-1">{analyzingCams.length}</span>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('algorithms')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'algorithms'
                ? 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-300'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <Compass className="w-4 h-4" />
            <span>Algorithms 1 & 2 Execution ({crowdedAreas.length} CA / {preventionPlans.length} Plans)</span>
          </button>

          <button
            onClick={() => setActiveTab('lattices')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'lattices'
                ? 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-300'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <GitBranch className="w-4 h-4" />
            <span>Formal Concept Lattices (Lc & La)</span>
          </button>
        </div>

        <button
          onClick={fetchResearchData}
          disabled={isLoading}
          className="text-[10px] text-cyan-400 hover:text-cyan-300 font-bold uppercase flex items-center gap-1 transition-colors px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800"
        >
          <RotateCcw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} /> Refresh Mathematics
        </button>
      </div>

      {/* SUB-VIEW 1: ALGORITHMS 1 & 2 RESEARCH EXECUTION */}
      {activeTab === 'algorithms' && (
        <div className="space-y-6">
          {/* Algorithm 1 Panel */}
          <div className="cyber-glass p-6 rounded-2xl border border-cyan-500/20 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold text-cyan-400 tracking-wider uppercase block">
                  IEEE Access 2025 — Algorithm 1
                </span>
                <h3 className="text-lg font-extrabold text-white">
                  Extraction of Crowded Areas (Threshold T = 0.70)
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Identified High-Crowd Areas:</span>
                <span className="px-2.5 py-1 rounded-lg bg-red-950/60 border border-red-500/30 text-red-400 font-extrabold text-xs">
                  {crowdedAreas.length} Areas
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-400">
              Evaluates multi-criteria fuzzy membership degrees across Density (D, weight=4), Protocol Risk (P, weight=3), 
              Movement (M, weight=3), Emergency (E, weight=4), and Speed Anomaly (S, weight=2).
              Areas satisfying weighted fuzzy crowd degree c &gt; 0.70 are categorized into set <code className="text-cyan-300">CA</code>.
            </p>

            {/* Table 2: Fuzzy Formal Context Kc (Paper Section V, Table 2) */}
            {Object.keys(fuzzySummary).length > 0 && (
              <div className="rounded-xl bg-slate-900/60 border border-slate-800/80 p-4 space-y-2">
                <span className="text-xs font-bold text-cyan-400 flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5" />
                  <span>Table 2 — Fuzzy Formal Context Kc of Monitored Areas (Paper Section V, Table 2)</span>
                </span>
                <div className="overflow-x-auto pt-2">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 text-[10px]">
                        <th className="py-1.5 px-2">Monitored Area</th>
                        <th className="py-1.5 px-2 text-center">D (Density, w=4)</th>
                        <th className="py-1.5 px-2 text-center">P (Protocol, w=3)</th>
                        <th className="py-1.5 px-2 text-center">M (Movement, w=3)</th>
                        <th className="py-1.5 px-2 text-center">E (Emergency, w=4)</th>
                        <th className="py-1.5 px-2 text-center">S (Speed Anomaly, w=2)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40">
                      {Object.entries(fuzzySummary).map(([areaName, attrs]: [string, any]) => (
                        <tr key={areaName} className="hover:bg-slate-800/20">
                          <td className="py-1.5 px-2 font-bold text-slate-300">{areaName}</td>
                          <td className="py-1.5 px-2 text-center font-mono">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${attrs.D >= 0.7 ? 'bg-red-950 text-red-400 font-bold' : 'text-slate-400'}`}>
                              {(attrs.D || 0).toFixed(2)}
                            </span>
                          </td>
                          <td className="py-1.5 px-2 text-center font-mono">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${attrs.P >= 0.7 ? 'bg-red-950 text-red-400 font-bold' : 'text-slate-400'}`}>
                              {(attrs.P || 0).toFixed(2)}
                            </span>
                          </td>
                          <td className="py-1.5 px-2 text-center font-mono">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${attrs.M >= 0.7 ? 'bg-orange-950 text-orange-400 font-bold' : 'text-slate-400'}`}>
                              {(attrs.M || 0).toFixed(2)}
                            </span>
                          </td>
                          <td className="py-1.5 px-2 text-center font-mono">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${attrs.E >= 0.7 ? 'bg-red-950 text-red-400 font-bold' : 'text-slate-400'}`}>
                              {(attrs.E || 0).toFixed(2)}
                            </span>
                          </td>
                          <td className="py-1.5 px-2 text-center font-mono">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${attrs.S >= 0.7 ? 'bg-amber-950 text-amber-400 font-bold' : 'text-slate-400'}`}>
                              {(attrs.S || 0).toFixed(2)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Crowded Areas Mathematical Breakdown */}
            {crowdedAreas.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-xs border border-slate-900 rounded-xl">
                No high-crowd areas extracted. All monitored areas have crowd level c &le; 0.70.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {crowdedAreas.map((ca: any, idx: number) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-950/80 border border-red-500/20 space-y-2.5">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-sm font-bold text-white block">{ca.area}</span>
                        <span className="text-[10px] text-cyan-400 font-mono">Concept ID: {ca.concept_id}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-red-900/40 text-red-300 font-bold text-xs border border-red-500/30">
                        Score c = {ca.crowd_score} &gt; 0.70
                      </span>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] text-slate-500 font-bold block uppercase">Satisfied Crowd Intent:</span>
                      <div className="flex flex-wrap gap-1">
                        {ca.satisfied_intent?.map((attr: string, i: number) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/20 text-cyan-300 text-[10px]">
                            {attr === 'D' && 'Density (D)'}
                            {attr === 'P' && 'Protocol (P)'}
                            {attr === 'M' && 'Movement (M)'}
                            {attr === 'E' && 'Emergency (E)'}
                            {attr === 'S' && 'Speed Anomaly (S)'}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-5 gap-1 pt-2 border-t border-slate-900 text-center">
                      {['D', 'P', 'M', 'E', 'S'].map((k) => (
                        <div key={k} className="p-1 rounded bg-slate-900/60 border border-slate-800">
                          <span className="text-[9px] text-slate-500 block">{k}</span>
                          <span className={`text-[10px] font-bold ${
                            (ca.attribute_scores?.[k] || 0) >= 0.7 ? 'text-red-400' : 'text-slate-300'
                          }`}>
                            {(ca.attribute_scores?.[k] || 0).toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>

                    <p className="text-[11px] text-slate-400 pt-1 leading-normal italic">
                      {ca.reason}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Algorithm 2 Panel */}
          <div className="cyber-glass p-6 rounded-2xl border border-purple-500/20 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold text-purple-400 tracking-wider uppercase block">
                  IEEE Access 2025 — Algorithm 2
                </span>
                <h3 className="text-lg font-extrabold text-white">
                  Crowd-Prevention Plan Generation & Area Lattice Coverage
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Generated Prevention Subplans:</span>
                <span className="px-2.5 py-1 rounded-lg bg-purple-950/60 border border-purple-500/30 text-purple-300 font-extrabold text-xs">
                  {preventionPlans.length} Plans
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-400">
              Parses the Area Lattice <code className="text-purple-300">La</code> to evaluate physical migration corridors.
              The safeguard function <code className="text-purple-300">cover(A', cpt.Intent)</code> guarantees
              that destination corridors are non-crowded, unblocked, and have capacity headroom verified before plan generation.
            </p>

            {preventionPlans.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-xs border border-slate-900 rounded-xl">
                No prevention subplans currently active. Either no areas exceed crowding threshold, or all areas are balanced.
              </div>
            ) : (
              <div className="space-y-4">
                {preventionPlans.map((plan: any, idx: number) => (
                  <div key={idx} className="p-5 rounded-xl bg-slate-950/80 border border-purple-500/20 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-purple-900/40 text-purple-300 font-bold text-xs border border-purple-500/30">
                          {plan.plan_id}
                        </span>
                        <span className="text-xs font-bold text-white">
                          Area Lattice Concept: {plan.concept_id}
                        </span>
                      </div>
                      <span className="text-[10px] text-amber-400 font-bold bg-amber-950/40 border border-amber-500/20 px-2 py-0.5 rounded">
                        STATUS: PENDING HUMAN APPROVAL
                      </span>
                    </div>

                    <div className="flex flex-col sm:flex-row items-center gap-4 p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                      <div className="flex-1 text-center sm:text-left">
                        <span className="text-[10px] text-red-400 uppercase font-bold block">Overcrowded Source (A')</span>
                        <strong className="text-sm text-white">{plan.crowded_sources?.join(', ')}</strong>
                      </div>
                      <ArrowRight className="w-5 h-5 text-purple-400 hidden sm:block" />
                      <div className="flex-1 text-center sm:text-left">
                        <span className="text-[10px] text-emerald-400 uppercase font-bold block">Safe Divert Target (cpt.Intent)</span>
                        <strong className="text-sm text-white">{plan.recommended_destinations?.join(', ')}</strong>
                      </div>
                      <div className="text-center sm:text-right border-t sm:border-t-0 sm:border-l border-slate-800 pt-2 sm:pt-0 sm:pl-4">
                        <span className="text-[10px] text-slate-500 block">Absorption Capacity</span>
                        <span className="text-xs font-bold text-cyan-400">{plan.mitigation_capacity} persons</span>
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-300 leading-normal">
                      {plan.reason}
                    </p>

                    <div className="p-2.5 rounded bg-amber-950/20 border border-amber-500/20 text-[10px] text-amber-300 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                      <span>{plan.warning || "Candidate prevention plan requires operational review before executing physical crowd diversion."}</span>
                    </div>

                    <div className="p-2.5 rounded bg-slate-900/40 border border-slate-800/60 text-[10px] text-slate-400 space-y-1">
                      <div><strong>Lattice Concept:</strong> {plan.concept_id}</div>
                      <div><strong>Source Extent (A'):</strong> [{plan.crowded_sources?.join(', ')}]</div>
                      <div><strong>Target Intent (cpt.Intent):</strong> [{plan.recommended_destinations?.join(', ')}]</div>
                      <div><strong>Absorption Headroom:</strong> {plan.mitigation_capacity} slots</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: CONCEPT LATTICES (Lc and La) */}
      {activeTab === 'lattices' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Crowd Lattice Lc */}
            <div className="cyber-glass p-5 rounded-2xl border border-cyan-500/20 space-y-4">
              <div className="border-b border-slate-800 pb-2">
                <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider block">
                  Definition 7 — Crowd Lattice (Lc)
                </span>
                <h4 className="text-base font-bold text-white">Crowd Characteristics Hierarchy</h4>
              </div>

              <p className="text-[11px] text-slate-400">
                Derived from Crowd Fuzzy Context <code className="text-cyan-300">Kc = (A, F, R)</code>. 
                Groups areas that share common crowd criteria (D, P, M, E, S) via Galois closure.
              </p>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-900 max-h-[460px] overflow-y-auto space-y-2">
                {crowdLattice?.nodes?.map((node: any, i: number) => (
                  <div key={i} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-cyan-300">{node.id}</span>
                      <span className="text-[10px] text-slate-500">{node.label}</span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                      <strong>Extent:</strong> [{node.extent?.join(', ')}]
                    </div>
                    <div className="text-[10px] text-cyan-400">
                      <strong>Intent:</strong> [{node.intent?.join(', ')}]
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Area Lattice La */}
            <div className="cyber-glass p-5 rounded-2xl border border-purple-500/20 space-y-4">
              <div className="border-b border-slate-800 pb-2">
                <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider block">
                  Definition 6 — Area Lattice (La)
                </span>
                <h4 className="text-base font-bold text-white">Physical Connectivity Hierarchy</h4>
              </div>

              <p className="text-[11px] text-slate-400">
                Derived from Area Formal Context <code className="text-purple-300">Ka = (A, A, R)</code>. 
                Extent groups areas connected to all areas in the Intent, identifying migration hubs.
              </p>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-900 max-h-[460px] overflow-y-auto space-y-2">
                {areaLattice?.nodes?.map((node: any, i: number) => (
                  <div key={i} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-purple-300">{node.id}</span>
                      <span className="text-[10px] text-slate-500">{node.label}</span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                      <strong>Connected Extent:</strong> [{node.extent?.join(', ')}]
                    </div>
                    <div className="text-[10px] text-purple-400">
                      <strong>Shared Targets:</strong> [{node.intent?.join(', ')}]
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
