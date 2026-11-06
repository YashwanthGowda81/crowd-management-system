import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { useCrowdSystem } from '../context/CrowdSystemContext';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: string | number;
    isPositive: boolean;
  };
  glowColor?: 'cyan' | 'blue' | 'purple' | 'red' | 'green' | 'orange';
  subtext?: string;
  loading?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon: Icon,
  trend,
  glowColor = 'blue',
  subtext,
}) => {
  const { emergencyState } = useCrowdSystem();

  const glowClasses = {
    cyan: 'border-cyan-500/20 hover:border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.02)] hover:shadow-[0_0_15px_rgba(6,182,212,0.15)]',
    blue: 'border-blue-500/20 hover:border-blue-500/40 shadow-[0_0_15px_rgba(59,130,246,0.02)] hover:shadow-[0_0_15px_rgba(59,130,246,0.15)]',
    purple: 'border-purple-500/20 hover:border-purple-500/40 shadow-[0_0_15px_rgba(139,92,246,0.02)] hover:shadow-[0_0_15px_rgba(139,92,246,0.15)]',
    red: 'border-red-500/20 hover:border-red-500/40 shadow-[0_0_15px_rgba(239,68,68,0.02)] hover:shadow-[0_0_15px_rgba(239,68,68,0.15)]',
    green: 'border-green-500/20 hover:border-green-500/40 shadow-[0_0_15px_rgba(16,185,129,0.02)] hover:shadow-[0_0_15px_rgba(16,185,129,0.15)]',
    orange: 'border-orange-500/20 hover:border-orange-500/40 shadow-[0_0_15px_rgba(245,158,11,0.02)] hover:shadow-[0_0_15px_rgba(245,158,11,0.15)]',
  };

  const iconColorClasses = {
    cyan: 'text-cyan-400 bg-cyan-950/30 border-cyan-500/20',
    blue: 'text-blue-400 bg-blue-950/30 border-blue-500/20',
    purple: 'text-purple-400 bg-purple-950/30 border-purple-500/20',
    red: 'text-red-400 bg-red-950/30 border-red-500/20',
    green: 'text-green-400 bg-green-950/30 border-green-500/20',
    orange: 'text-orange-400 bg-orange-950/30 border-orange-500/20',
  };

  // If system emergency is active, force some visual elements to align
  const cardBorder = emergencyState.isTriggered && glowColor === 'red'
    ? 'border-red-500/50 shadow-[0_0_20px_rgba(239,68,68,0.25)] bg-red-950/10'
    : `cyber-glass ${glowClasses[glowColor]}`;

  return (
    <div className={`p-5 rounded-xl transition-all duration-300 relative overflow-hidden group ${cardBorder}`}>
      {/* Background corner glow */}
      <div className={`absolute -right-8 -bottom-8 w-24 h-24 rounded-full filter blur-2xl opacity-10 transition-opacity group-hover:opacity-20
        ${glowColor === 'cyan' && 'bg-cyan-500'}
        ${glowColor === 'blue' && 'bg-blue-500'}
        ${glowColor === 'purple' && 'bg-purple-500'}
        ${glowColor === 'red' && 'bg-red-500'}
        ${glowColor === 'green' && 'bg-green-500'}
        ${glowColor === 'orange' && 'bg-orange-500'}
      `} />

      <div className="flex items-center justify-between gap-4">
        {/* Metric Label and Value */}
        <div className="space-y-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            {title}
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-white font-mono">
              {value}
            </span>
            {trend && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center gap-0.5
                ${trend.isPositive 
                  ? 'bg-green-950/40 text-green-400 border border-green-500/20' 
                  : 'bg-red-950/40 text-red-400 border border-red-500/20'}`}
              >
                {trend.isPositive ? '↑' : '↓'} {trend.value}
              </span>
            )}
          </div>
        </div>

        {/* Icon Container */}
        <div className={`p-2.5 rounded-lg border transition-transform group-hover:scale-105 flex-shrink-0 ${iconColorClasses[glowColor]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      {subtext && (
        <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
          <span>{subtext}</span>
        </div>
      )}
    </div>
  );
};
