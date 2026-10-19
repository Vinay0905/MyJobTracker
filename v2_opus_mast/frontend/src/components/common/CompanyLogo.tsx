import React, { useState, useEffect } from 'react';

interface CompanyLogoProps {
  company: string;
  domain?: string | null;
  category: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const DOMAIN_MAP: Record<string, string> = {
  rockstargames: 'rockstargames.com',
  epicgames: 'epicgames.com',
  nvidia: 'nvidia.com',
  playstation: 'playstation.com',
  naughtydog: 'naughtydog.com',
  ea: 'ea.com',
  careem: 'careem.com',
  qualcomm: 'qualcomm.com',
  g42: 'g42.ai',
  roblox: 'roblox.com',
  canonical: 'canonical.com',
  cerebras: 'cerebras.ai',
  arista: 'arista.com',
  weride: 'weride.ai',
};

// Files present in /public/logos
const LOCAL_LOGOS = new Set([
  'arista', 'canonical', 'careem', 'cerebras', 'ea', 'epicgames', 'g42',
  'naughtydog', 'nvidia', 'playstation', 'qualcomm', 'roblox', 'rockstargames', 'weride',
]);

/** Accepts "https://www.nvidia.com/careers", "www.nvidia.com", or "nvidia.com" and returns "nvidia.com". */
const toHostname = (value?: string | null): string | null => {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  try {
    const host = new URL(trimmed.includes('://') ? trimmed : `https://${trimmed}`).hostname.toLowerCase();
    return host.replace(/^www\./, '') || null;
  } catch {
    return null;
  }
};

const getLogoSlug = (name: string): string => {
  const raw = (name || '').toLowerCase().trim();
  if (raw.includes('rockstar')) return 'rockstargames';
  if (raw.includes('epic')) return 'epicgames';
  if (raw.includes('nvidia')) return 'nvidia';
  if (raw.includes('naughty dog')) return 'naughtydog';
  if (raw.includes('playstation') || raw.includes('sony')) return 'playstation';
  if (raw.includes('electronic arts') || raw === 'ea' || raw.includes('respawn')) return 'ea';
  if (raw.includes('careem')) return 'careem';
  if (raw.includes('qualcomm')) return 'qualcomm';
  if (raw.includes('g42')) return 'g42';
  if (raw.includes('roblox')) return 'roblox';
  if (raw.includes('canonical') || raw.includes('ubuntu')) return 'canonical';
  if (raw.includes('cerebras')) return 'cerebras';
  if (raw.includes('arista')) return 'arista';
  if (raw.includes('weride')) return 'weride';
  return raw.replace(/[^a-z0-9]/g, '');
};

export const CompanyLogo: React.FC<CompanyLogoProps> = ({
  company,
  domain,
  category,
  size = 'md',
  className = '',
}) => {
  const [sourceIndex, setSourceIndex] = useState<number>(0);

  useEffect(() => {
    setSourceIndex(0);
  }, [company, domain]);

  const companySlug = getLogoSlug(company);
  const cleanDomain = toHostname(domain) || DOMAIN_MAP[companySlug] || `${companySlug}.com`;

  // Cascading sources:
  // 1. Local Curated Vector Asset (/logos/{slug}.svg), only when the file exists
  // 2. Google S2 Favicon API (retina 128px)
  // 3. Clearbit Logo API
  const sources = [
    ...(LOCAL_LOGOS.has(companySlug) ? [`/logos/${companySlug}.svg`] : []),
    `https://www.google.com/s2/favicons?domain=${encodeURIComponent(cleanDomain)}&sz=128`,
    `https://logo.clearbit.com/${encodeURIComponent(cleanDomain)}`,
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
