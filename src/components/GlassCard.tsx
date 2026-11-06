import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glow?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({ children, className = '', glow = false }) => {
  return (
    <div className={`rounded-xl ${glow ? 'cyber-glass-glow' : 'cyber-glass'} transition-all duration-300 ${className}`}>
      {children}
    </div>
  );
};
