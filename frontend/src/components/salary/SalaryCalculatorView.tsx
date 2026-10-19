import React, { useState, useMemo } from 'react';
import { playKeyClick, playTogglePulse } from '../../utils/audio';

interface SkillPremium {
  id: string;
  name: string;
  category: string;
  premiumPct: number;
  description: string;
}

const TECH_PREMIUMS: SkillPremium[] = [
  { id: 'cuda', name: 'CUDA & GPU Kernels', category: 'Silicon & AI', premiumPct: 35, description: 'Direct warp-level parallel optimization & memory hierarchy' },
  { id: 'triton', name: 'Triton / CUTLASS', category: 'Silicon & AI', premiumPct: 38, description: 'Custom attention & high-throughput tensor core programming' },
  { id: 'rdma', name: 'RDMA & InfiniBand', category: 'Infrastructure', premiumPct: 32, description: 'Kernel-bypass zero-copy multi-node cluster networking' },
  { id: 'vulkan', name: 'Vulkan / DirectX 12', category: 'Graphics', premiumPct: 26, description: 'Explicit GPU pipeline & low-overhead command recording' },
  { id: 'physics', name: 'Physics & Simulation', category: 'Simulation', premiumPct: 28, description: 'Rigid body dynamics, spatial partitioning & collision' },
  { id: 'rtos', name: 'FreeRTOS & Embedded C', category: 'Edge AI', premiumPct: 22, description: 'Deterministic low-jitter firmware & hardware control' },
  { id: 'distributed', name: 'Distributed Consensus', category: 'Infrastructure', premiumPct: 25, description: 'Raft, Paxos & low-latency state synchronization' },
  { id: 'unreal', name: 'Unreal Engine Core C++', category: 'Graphics', premiumPct: 24, description: 'MassEntity, Chaos physics & custom engine pipelines' },
];

export const SalaryCalculatorView: React.FC = () => {
  // Base compensation settings
  const [baseMarketComp, setBaseMarketComp] = useState<number>(145000);
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>(['cuda', 'triton']);

  // UAE Tax-Free Calculator Settings
  const [aedMonthly, setAedMonthly] = useState<number>(45000); // 45,000 AED/mo is common senior tech salary in UAE
  const [usdExchangeRate] = useState<number>(3.6725); // Fixed AED to USD peg

  const toggleSkill = (id: string) => {
    playTogglePulse();
    setSelectedSkillIds((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  // Compute stack multiplier
  const totalPremiumPct = useMemo(() => {
    const selected = TECH_PREMIUMS.filter((p) => selectedSkillIds.includes(p.id));
    // Diminishing returns formula: max single + 50% of secondary premiums
    if (selected.length === 0) return 0;
    const sorted = [...selected].map((s) => s.premiumPct).sort((a, b) => b - a);
    let total = sorted[0];
    for (let i = 1; i < sorted.length; i++) {
      total += sorted[i] * 0.45;
    }
    return Math.min(Math.round(total), 65); // Cap stack premium at +65%
  }, [selectedSkillIds]);

  const estimatedMarketComp = Math.round(baseMarketComp * (1 + totalPremiumPct / 100));
  const estimatedMin = Math.round(estimatedMarketComp * 0.9);
  const estimatedMax = Math.round(estimatedMarketComp * 1.15);

  // UAE Tax-Free Computations
  const annualAed = aedMonthly * 12;
  const annualUsdNet = Math.round(annualAed / usdExchangeRate);
  
  // Tax equivalent estimates (what pre-tax gross you would need in US/UK to take home this exact net)
  // California: Effective tax ~37% for this income band
  const californiaGrossEq = Math.round(annualUsdNet / (1 - 0.37));
  // New York City: Effective tax ~39.5%
  const newYorkGrossEq = Math.round(annualUsdNet / (1 - 0.395));
  // London / UK: Effective tax ~42%
  const londonGrossEq = Math.round(annualUsdNet / (1 - 0.42));

  return (
    <div className="flex flex-col gap-space-lg max-w-6xl mx-auto w-full pb-12">
      {/* Header Banner */}
      <div className="p-space-lg rounded-2xl bg-surface-container-low border border-outline-variant flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-lg bg-primary/20 text-primary font-mono text-sm font-bold flex items-center justify-center">
              <span className="material-symbols-outlined text-base">payments</span>
            </span>
            <span className="font-mono text-xs text-primary font-bold tracking-wider uppercase">
              Reverse Compensation & Global Net Terminal
            </span>
          </div>
          <h2 className="text-xl font-bold text-on-surface mt-1.5">
            Tech Stack Scarcity Multiplier & UAE Tax-Free Model
          </h2>
          <p className="text-xs text-on-surface-variant mt-1">
            Real-time scarcity premium estimation for low-level systems, GPU kernels, and tax-free Middle East relocation equivalence.
          </p>
        </div>

        <div className="flex items-center gap-3 self-stretch md:self-auto justify-end">
          <div className="p-3 rounded-xl bg-surface-container border border-outline-variant/60 font-mono text-right">
            <span className="text-[10px] text-outline block">COMPUTED STACK PREMIUM</span>
            <span className="text-2xl font-bold text-secondary">+{totalPremiumPct}%</span>
          </div>
        </div>
      </div>

      {/* Illustrative Disclosure Banner */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-2.5 flex items-center gap-3 text-amber-300 font-mono text-xs">
        <span className="material-symbols-outlined text-base text-amber-400 shrink-0">info</span>
        <span>
          <strong>Illustrative Scenario Calculator:</strong> Figures reflect hypothetical modeling, candidate assumptions, and public market benchmarks; not verified employer compensation offers or binding guarantees.
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-lg">
        {/* Module 1: Tech Stack Scarcity Multiplier */}
        <section className="p-space-lg rounded-2xl bg-surface-container-low border border-outline-variant flex flex-col gap-space-md">
          <div className="flex items-center justify-between border-b border-outline-variant/60 pb-3">
            <div>
              <h3 className="text-sm font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-base text-secondary">memory</span>
                <span>Tech Stack Scarcity Sandbox</span>
              </h3>
              <p className="text-[11px] text-outline mt-0.5">Toggle skills to estimate your stack market leverage</p>
            </div>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-secondary/10 text-secondary border border-secondary/20">
              {selectedSkillIds.length} Active Multipliers
            </span>
          </div>

          {/* Base Market Baseline Slider */}
          <div className="flex flex-col gap-1.5 bg-surface-container p-3 rounded-xl border border-outline-variant/40">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-on-surface-variant font-medium">Standard SWE Baseline:</span>
              <span className="font-bold text-primary">${baseMarketComp.toLocaleString()} USD / yr</span>
            </div>
            <input
              type="range"
              min="100000"
              max="220000"
              step="5000"
              value={baseMarketComp}
              onChange={(e) => {
                playKeyClick();
                setBaseMarketComp(Number(e.target.value));
              }}
              className="w-full accent-primary h-1.5 bg-surface-container-highest rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] font-mono text-outline">
              <span>$100k (Mid Market)</span>
              <span>$160k (Tier 1)</span>
              <span>$220k (Staff Baseline)</span>
            </div>
          </div>

          {/* Skill Multipliers Grid */}
          <div className="flex flex-col gap-2">
            <span className="font-mono text-[11px] text-outline font-semibold uppercase">
              Select High-Scarcity Core Technologies:
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {TECH_PREMIUMS.map((skill) => {
                const isSelected = selectedSkillIds.includes(skill.id);
                return (
                  <button
                    key={skill.id}
                    onClick={() => toggleSkill(skill.id)}
                    className={`p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all ${
                      isSelected
                        ? 'bg-secondary/15 border-secondary text-on-surface shadow-sm shadow-secondary/10'
                        : 'bg-surface-container border-outline-variant/60 text-on-surface-variant hover:border-outline hover:text-on-surface'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-mono text-xs font-bold truncate">{skill.name}</span>
                      <span className={`font-mono text-[11px] font-semibold px-1.5 py-0.5 rounded ${isSelected ? 'bg-secondary text-surface-container-lowest' : 'bg-surface-container-highest text-secondary'}`}>
                        +{skill.premiumPct}%
                      </span>
                    </div>
                    <span className="text-[10px] text-outline mt-1 line-clamp-1">
                      {skill.description}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Estimated Compensation Readout */}
          <div className="p-4 rounded-xl bg-surface-container-lowest border border-secondary/30 flex flex-col gap-1.5 font-mono">
            <span className="text-[10px] text-outline uppercase tracking-wider font-semibold">
              Estimated Total Cash Compensation Band
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-secondary">
                ${estimatedMin.toLocaleString()} – ${estimatedMax.toLocaleString()}
              </span>
              <span className="text-xs text-outline">USD / year</span>
            </div>
            <div className="text-[11px] text-on-surface-variant mt-1 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm text-secondary">trending_up</span>
              <span>
                Your chosen stack yields a <strong>+{totalPremiumPct}% premium</strong> (~${(estimatedMarketComp - baseMarketComp).toLocaleString()} extra annual base) over general software roles.
              </span>
            </div>
          </div>
        </section>

        {/* Module 2: UAE Tax-Free & Global Net Equalizer */}
        <section className="p-space-lg rounded-2xl bg-surface-container-low border border-outline-variant flex flex-col gap-space-md">
          <div className="flex items-center justify-between border-b border-outline-variant/60 pb-3">
            <div>
              <h3 className="text-sm font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-base text-primary">currency_exchange</span>
                <span>UAE Tax-Free Net Equivalent Terminal</span>
              </h3>
              <p className="text-[11px] text-outline mt-0.5">Middle East (Dubai / Abu Dhabi) 0% Income Tax vs US / UK</p>
            </div>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              0% Income Tax
            </span>
          </div>

          {/* Monthly UAE Salary Input */}
          <div className="flex flex-col gap-2 bg-surface-container p-3.5 rounded-xl border border-outline-variant/40">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-on-surface-variant font-medium">Monthly Compensation in UAE:</span>
              <span className="font-bold text-primary">{aedMonthly.toLocaleString()} AED / month</span>
            </div>
            <input
              type="range"
              min="20000"
              max="90000"
              step="2500"
              value={aedMonthly}
              onChange={(e) => {
                playKeyClick();
                setAedMonthly(Number(e.target.value));
              }}
              className="w-full accent-primary h-1.5 bg-surface-container-highest rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] font-mono text-outline">
              <span>20,000 AED ($65k net)</span>
              <span>45,000 AED ($147k net)</span>
              <span>90,000 AED ($294k net)</span>
            </div>
          </div>

          {/* Take-Home Summary Card */}
          <div className="grid grid-cols-2 gap-2 font-mono">
            <div className="p-3 rounded-xl bg-surface-container border border-outline-variant/50">
              <span className="text-[10px] text-outline block">ANNUAL TAX-FREE NET</span>
              <span className="text-xl font-bold text-emerald-400">${annualUsdNet.toLocaleString()}</span>
              <span className="text-[10px] text-outline block mt-0.5">{annualAed.toLocaleString()} AED</span>
            </div>
            <div className="p-3 rounded-xl bg-surface-container border border-outline-variant/50">
              <span className="text-[10px] text-outline block">MONTHLY TAKE-HOME</span>
              <span className="text-xl font-bold text-on-surface">${Math.round(annualUsdNet / 12).toLocaleString()}</span>
              <span className="text-[10px] text-outline block mt-0.5">100% Retained</span>
            </div>
          </div>

          {/* US / UK Gross Required Equivalents */}
          <div className="flex flex-col gap-2">
            <span className="font-mono text-[11px] text-outline font-semibold uppercase">
              Pre-Tax Gross Salary Needed in Other Tech Capitals to Match This:
            </span>

            <div className="flex flex-col gap-2 font-mono text-xs">
              <div className="p-2.5 rounded-xl bg-surface-container border border-outline-variant/40 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  <span className="font-bold text-on-surface">San Francisco / Silicon Valley (California)</span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-cyan-400">${californiaGrossEq.toLocaleString()} USD</span>
                  <span className="text-[10px] text-outline block">~37% Combined Tax</span>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-surface-container border border-outline-variant/40 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-400" />
                  <span className="font-bold text-on-surface">New York City (NY State + City Tax)</span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-blue-400">${newYorkGrossEq.toLocaleString()} USD</span>
                  <span className="text-[10px] text-outline block">~39.5% Combined Tax</span>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-surface-container border border-outline-variant/40 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-400" />
                  <span className="font-bold text-on-surface">London (United Kingdom)</span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-purple-400">${londonGrossEq.toLocaleString()} USD</span>
                  <span className="text-[10px] text-outline block">~42% Higher Rate Tax</span>
                </div>
              </div>
            </div>
          </div>

          {/* UAE Tech Employers Direct Link Callout */}
          <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-base">domain</span>
              <span className="text-on-surface">
                <strong>UAE Tech Hub Roles:</strong> G42 Cloud, Careem, WeRide Autonomous
              </span>
            </div>
            <span className="text-primary font-bold">Tax-Free Ingestion Active</span>
          </div>
        </section>
      </div>
    </div>
  );
};
