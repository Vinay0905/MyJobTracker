import React, { useState } from 'react';

interface CompanyLogoProps {
  company: string;
  domain?: string | null;
  category: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const CompanyLogo: React.FC<CompanyLogoProps> = ({
  company,
  domain,
  category,
  size = 'md',
  className = '',
}) => {
  const [sourceIndex, setSourceIndex] = useState<number>(0);

  // Normalize company slug for local curated static SVGs
  const companySlug = company
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');

  const cleanDomain = domain || `${companySlug}.com`;

  // Cascading sources:
  // 1. Local Curated Vector Asset (/logos/{slug}.svg)
  // 2. Clearbit Logo API
  // 3. Google S2 Favicon API (retina 128px)
  const sources = [
    `/logos/${companySlug}.svg`,
    `https://logo.clearbit.com/${cleanDomain}`,
    `https://www.google.com/s2/favicons?domain=${cleanDomain}&sz=128`,
  ];

  const sizeClasses = {
    sm: 'w-7 h-7 text-[10px]',
    md: 'w-10 h-10 text-xs',
    lg: 'w-14 h-14 text-sm font-bold',
  }[size];

  // Mathematical HSL hash for deterministic, aesthetic neon gradients
  const getAvatarGradient = (str: string) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h1 = Math.abs(hash % 360);
    const h2 = (h1 + 45) % 360;
    return `linear-gradient(135deg, hsl(${h1}, 75%, 18%) 0%, hsl(${h2}, 85%, 10%) 100%)`;
  };

  const getBorderGlow = () => {
    const cat = (category || '').toLowerCase();
    if (cat.includes('silicon') || cat.includes('ai')) {
      return 'border-cyan-500/40 shadow-[0_0_12px_rgba(6,182,212,0.18)]';
    }
    if (cat.includes('game')) {
      return 'border-purple-500/40 shadow-[0_0_12px_rgba(168,85,247,0.18)]';
    }
    return 'border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.18)]';
  };

  const initials = company
    .split(' ')
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase() || '??';

  // If all image sources fail, render the deterministic neon avatar
  if (sourceIndex >= sources.length) {
    return (
      <div
        className={`${sizeClasses} rounded-xl border flex items-center justify-center font-mono font-bold text-white shrink-0 transition-transform select-none ${getBorderGlow()} ${className}`}
        style={{ background: getAvatarGradient(company) }}
        title={company}
      >
        {initials}
      </div>
    );
  }

  return (
    <div
      className={`${sizeClasses} rounded-xl border border-outline-variant/60 bg-surface-container-highest/90 flex items-center justify-center overflow-hidden shrink-0 transition-all group-hover:scale-105 shadow-sm ${className}`}
    >
      <img
        src={sources[sourceIndex]}
        alt={`${company} logo`}
        className="w-full h-full object-contain p-1.5 rounded-xl"
        loading="lazy"
        decoding="async"
        onError={() => setSourceIndex((prev) => prev + 1)}
      />
    </div>
  );
};
