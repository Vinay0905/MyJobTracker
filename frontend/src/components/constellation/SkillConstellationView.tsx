import React, { useState, useMemo } from 'react';
import { playKeyClick, playTogglePulse } from '../../utils/audio';

export interface ConstellationNode {
  id: string;
  name: string;
  track: 'silicon' | 'graphics' | 'edge' | 'infra';
  level: 1 | 2 | 3 | 4; // 1: Foundation, 2: Core, 3: Advanced, 4: Apex Mastery
  x: number;
  y: number;
  prerequisites: string[];
  downstream: string[];
  description: string;
  premiumPct: number;
  topEmployers: string[];
}

const CONSTELLATION_NODES: ConstellationNode[] = [
  // Branch 1: Silicon & AI Acceleration
  {
    id: 'python',
    name: 'Python',
    track: 'silicon',
    level: 1,
    x: 80,
    y: 120,
    prerequisites: [],
    downstream: ['pytorch_core'],
    description: 'Scientific computing, NumPy, C-extensions bindings and prototyping',
    premiumPct: 10,
    topEmployers: ['NVIDIA', 'Cerebras', 'G42'],
  },
  {
    id: 'cpp',
    name: 'C++ Systems Core',
    track: 'silicon',
    level: 1,
    x: 80,
    y: 260,
    prerequisites: [],
    downstream: ['cuda', 'vulkan', 'rtos'],
    description: 'Memory models, RAII, pointers, cache awareness and zero-cost abstractions',
    premiumPct: 20,
    topEmployers: ['NVIDIA', 'PlayStation', 'Qualcomm', 'Arista'],
  },
  {
    id: 'pytorch_core',
    name: 'PyTorch Internals',
    track: 'silicon',
    level: 2,
    x: 280,
    y: 120,
    prerequisites: ['python'],
    downstream: ['cuda'],
    description: 'Autograd engine, torch.compile, ATen backend C++ operator dispatch',
    premiumPct: 25,
    topEmployers: ['Cerebras', 'G42', 'Roblox'],
  },
  {
    id: 'cuda',
    name: 'CUDA C/C++',
    track: 'silicon',
    level: 3,
    x: 480,
    y: 150,
    prerequisites: ['cpp', 'pytorch_core'],
    downstream: ['triton', 'flash_attention'],
    description: 'SIMT execution, shared memory coalescing, warp shuffle, streaming multiprocessors',
    premiumPct: 35,
    topEmployers: ['NVIDIA', 'Cerebras', 'G42'],
  },
  {
    id: 'triton',
    name: 'Triton & CUTLASS',
    track: 'silicon',
    level: 4,
    x: 700,
    y: 110,
    prerequisites: ['cuda'],
    downstream: ['flash_attention'],
    description: 'Blocked matrix multiplication, custom tensor core tiling, fused compiler passes',
    premiumPct: 38,
    topEmployers: ['NVIDIA', 'Cerebras'],
  },
  {
    id: 'flash_attention',
    name: 'FlashAttention & Kernel Fusion',
    track: 'silicon',
    level: 4,
    x: 900,
    y: 150,
    prerequisites: ['cuda', 'triton'],
    downstream: [],
    description: 'Exact attention with sub-quadratic memory IO, SRAM caching, online softmax',
    premiumPct: 42,
    topEmployers: ['NVIDIA', 'Cerebras', 'G42'],
  },

  // Branch 2: Game Engine & Real-Time Graphics
  {
    id: 'math_3d',
    name: '3D Math & Linear Algebra',
    track: 'graphics',
    level: 1,
    x: 80,
    y: 400,
    prerequisites: [],
    downstream: ['vulkan', 'physics_sim'],
    description: 'Quaternions, transform hierarchies, projective geometry, vector projection',
    premiumPct: 15,
    topEmployers: ['Epic Games', 'Rockstar', 'Roblox'],
  },
  {
    id: 'vulkan',
    name: 'Vulkan / DirectX 12',
    track: 'graphics',
    level: 2,
    x: 280,
    y: 360,
    prerequisites: ['cpp', 'math_3d'],
    downstream: ['compute_shaders'],
    description: 'Explicit memory allocation, pipeline barriers, descriptor heaps, render passes',
    premiumPct: 26,
    topEmployers: ['PlayStation', 'Epic Games', 'Rockstar'],
  },
  {
    id: 'compute_shaders',
    name: 'Compute Shaders & Ray Tracing',
    track: 'graphics',
    level: 3,
    x: 480,
    y: 350,
    prerequisites: ['vulkan'],
    downstream: ['unreal_chaos'],
    description: 'GPGPU workgroups, HLSL/GLSL compute, BVH traversal, hardware ray-tracing',
    premiumPct: 30,
    topEmployers: ['PlayStation', 'Epic Games', 'Rockstar'],
  },
  {
    id: 'physics_sim',
    name: 'Rigid Body Physics',
    track: 'graphics',
    level: 2,
    x: 280,
    y: 480,
    prerequisites: ['math_3d'],
    downstream: ['unreal_chaos'],
    description: 'GJK/EPA collision detection, spatial hashing, impulse solvers, constraints',
    premiumPct: 28,
    topEmployers: ['Roblox', 'Epic Games', 'Rockstar'],
  },
  {
    id: 'unreal_chaos',
    name: 'Unreal Chaos & MassEntity',
    track: 'graphics',
    level: 4,
    x: 740,
    y: 410,
    prerequisites: ['compute_shaders', 'physics_sim'],
    downstream: [],
    description: 'ECS-based gameplay simulation, destructive physics, custom engine subsystems',
    premiumPct: 32,
    topEmployers: ['Epic Games', 'Rockstar', 'PlayStation'],
  },

  // Branch 3: Edge AI, Embedded & Autonomous
  {
    id: 'c_lang',
    name: 'Low-Level C',
    track: 'edge',
    level: 1,
    x: 80,
    y: 620,
    prerequisites: [],
    downstream: ['rtos'],
    description: 'Pointer arithmetic, bit manipulation, volatile keywords, register-level memory',
    premiumPct: 15,
    topEmployers: ['Qualcomm', 'Arista', 'WeRide'],
  },
  {
    id: 'rtos',
    name: 'FreeRTOS & Embedded POSIX',
    track: 'edge',
    level: 2,
    x: 280,
    y: 620,
    prerequisites: ['c_lang', 'cpp'],
    downstream: ['device_drivers', 'tinyml'],
    description: 'Preemptive multitasking, ISR latency control, semaphore queues, task scheduling',
    premiumPct: 22,
    topEmployers: ['Qualcomm', 'Arista', 'WeRide'],
  },
  {
    id: 'device_drivers',
    name: 'Linux Kernel Drivers & DMA',
    track: 'edge',
    level: 3,
    x: 480,
    y: 590,
    prerequisites: ['rtos'],
    downstream: ['autonomous_stack'],
    description: 'Character drivers, ring buffers, DMA transfers, interrupt handlers, IOMMU',
    premiumPct: 30,
    topEmployers: ['Qualcomm', 'Canonical', 'Arista'],
  },
  {
    id: 'tinyml',
    name: 'Edge AI & Quantization',
    track: 'edge',
    level: 3,
    x: 480,
    y: 710,
    prerequisites: ['rtos'],
    downstream: ['autonomous_stack'],
    description: 'INT8/FP4 weight quantization, TensorRT-Edge, NPU acceleration, ONNX runtime',
    premiumPct: 28,
    topEmployers: ['Qualcomm', 'WeRide', 'G42'],
  },
  {
    id: 'autonomous_stack',
    name: 'Autonomous Vehicle Sensor Fusion',
    track: 'edge',
    level: 4,
    x: 780,
    y: 650,
    prerequisites: ['device_drivers', 'tinyml'],
    downstream: [],
    description: 'LiDAR/Camera fusion, ROS 2, Kalman filters, deterministic drive-by-wire control',
    premiumPct: 36,
    topEmployers: ['WeRide', 'Qualcomm'],
  },

  // Branch 4: AI Infrastructure & High-Performance Cloud
  {
    id: 'linux_sre',
    name: 'Linux Systems & Networking',
    track: 'infra',
    level: 1,
    x: 80,
    y: 830,
    prerequisites: [],
    downstream: ['dist_systems'],
    description: 'eBPF tracing, TCP/IP stack tuning, epoll, namespaces, memory cgroups',
    premiumPct: 18,
    topEmployers: ['Canonical', 'Arista', 'Careem'],
  },
  {
    id: 'dist_systems',
    name: 'Distributed Consensus & Sockets',
    track: 'infra',
    level: 2,
    x: 280,
    y: 830,
    prerequisites: ['linux_sre'],
    downstream: ['rdma_net', 'k8s_gpu'],
    description: 'Raft consensus, async IO, event loops, zero-copy protocol serialization',
    premiumPct: 25,
    topEmployers: ['Arista', 'Cerebras', 'Careem'],
  },
  {
    id: 'rdma_net',
    name: 'RDMA & InfiniBand Networks',
    track: 'infra',
    level: 3,
    x: 520,
    y: 830,
    prerequisites: ['dist_systems'],
    downstream: ['gpu_cluster_orchestration'],
    description: 'Kernel bypass RoCEv2, QP state machines, memory registration, IB verbs',
    premiumPct: 34,
    topEmployers: ['Arista', 'NVIDIA', 'G42'],
  },
  {
    id: 'k8s_gpu',
    name: 'Kubernetes & Container Runtimes',
    track: 'infra',
    level: 2,
    x: 380,
    y: 930,
    prerequisites: ['linux_sre'],
    downstream: ['gpu_cluster_orchestration'],
    description: 'NVIDIA container toolkit, device plugins, CRI-O, distributed operators',
    premiumPct: 22,
    topEmployers: ['G42', 'Careem', 'Canonical'],
  },
  {
    id: 'gpu_cluster_orchestration',
    name: 'Large-Scale AI Cluster Infra',
    track: 'infra',
    level: 4,
    x: 820,
    y: 880,
    prerequisites: ['rdma_net', 'k8s_gpu'],
    downstream: [],
    description: 'Multi-thousand GPU training clusters, Slurm, NCCL topology, fast checkpointing',
    premiumPct: 38,
    topEmployers: ['G42', 'Cerebras', 'NVIDIA', 'Arista'],
  },
];

interface SkillConstellationViewProps {
  onSelectSkillFilter: (skillId: string) => void;
}

export const SkillConstellationView: React.FC<SkillConstellationViewProps> = ({
  onSelectSkillFilter,
}) => {
  const [selectedTrack, setSelectedTrack] = useState<string>('all');
  const [hoveredNode, setHoveredNode] = useState<ConstellationNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<ConstellationNode | null>(
    CONSTELLATION_NODES.find((n) => n.id === 'cuda') || CONSTELLATION_NODES[0]
  );

  const filteredNodes = useMemo(() => {
    if (selectedTrack === 'all') return CONSTELLATION_NODES;
    return CONSTELLATION_NODES.filter((n) => n.track === selectedTrack);
  }, [selectedTrack]);

  // Track color themes
  const getTrackColor = (track: string) => {
    switch (track) {
      case 'silicon':
        return '#00E5FF'; // Cyan
      case 'graphics':
        return '#A855F7'; // Purple
      case 'edge':
        return '#10B981'; // Emerald
      case 'infra':
        return '#F59E0B'; // Amber
      default:
        return '#38BDF8';
    }
  };

  const activeFocusNode = hoveredNode || selectedNode;

  // Build edge connections between filtered nodes
  const edges = useMemo(() => {
    const list: Array<{ from: ConstellationNode; to: ConstellationNode; isHighlighted: boolean }> = [];
    filteredNodes.forEach((node) => {
      node.downstream.forEach((targetId) => {
        const targetNode = filteredNodes.find((n) => n.id === targetId);
        if (targetNode) {
          const isHighlighted = Boolean(
            activeFocusNode?.id === node.id ||
            activeFocusNode?.id === targetNode.id ||
            (activeFocusNode?.prerequisites.includes(node.id) && activeFocusNode?.id === targetNode.id)
          );
          list.push({ from: node, to: targetNode, isHighlighted });
        }
      });
    });
    return list;
  }, [filteredNodes, activeFocusNode]);

  return (
    <div className="flex flex-col gap-space-md max-w-7xl mx-auto w-full pb-12">
      {/* HUD Header */}
      <div className="p-space-lg rounded-2xl bg-surface-container-low border border-outline-variant flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-lg bg-secondary/20 text-secondary font-mono text-sm font-bold flex items-center justify-center">
              <span className="material-symbols-outlined text-base">hub</span>
            </span>
            <span className="font-mono text-xs text-secondary font-bold tracking-wider uppercase">
              Deep-Tech Dependency Constellation
            </span>
          </div>
          <h2 className="text-xl font-bold text-on-surface mt-1.5">
            Low-Level Systems & AI Acceleration Tech Tree
          </h2>
          <p className="text-xs text-on-surface-variant mt-1">
            Visual hierarchy of prerequisite and downstream dependencies. Click any node to inspect market leverage and filter matching engineering roles.
          </p>
        </div>

        {/* Track Filters */}
        <div className="flex flex-wrap items-center gap-1.5 font-mono text-xs">
          {[
            { id: 'all', label: 'All Trees' },
            { id: 'silicon', label: 'Silicon & AI', color: 'text-cyan-400' },
            { id: 'graphics', label: 'Game Engine', color: 'text-purple-400' },
            { id: 'edge', label: 'Edge & Embedded', color: 'text-emerald-400' },
            { id: 'infra', label: 'Cloud & RDMA', color: 'text-amber-400' },
          ].map((track) => (
            <button
              key={track.id}
              onClick={() => {
                playTogglePulse();
                setSelectedTrack(track.id);
              }}
              className={`px-3 py-1.5 rounded-xl border transition-all ${
                selectedTrack === track.id
                  ? 'bg-surface-container-highest border-primary text-white font-bold shadow-sm'
                  : 'bg-surface-container-low border-outline-variant/60 text-outline hover:text-on-surface hover:border-outline'
              }`}
            >
              {track.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-space-md">
        {/* Constellation Canvas Viewport */}
        <div className="lg:col-span-3 rounded-2xl bg-[#080B10] border border-outline-variant/80 p-4 relative overflow-hidden flex flex-col min-h-[580px] shadow-2xl">
          {/* Subtle Grid / Scanline overlay */}
          <div
            className="absolute inset-0 pointer-events-none opacity-[0.04]"
            style={{
              backgroundImage: 'radial-gradient(circle at 1px 1px, #ffffff 1px, transparent 0)',
              backgroundSize: '24px 24px',
            }}
          />

          <div className="flex items-center justify-between z-10 font-mono text-[11px] text-outline px-2 pb-2 border-b border-outline-variant/20">
            <span>ZOOM: 100% (INTERACTIVE GRAPH)</span>
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>{filteredNodes.length} SPECIALIZATION NODES</span>
            </span>
          </div>

          <div className="flex-1 w-full h-full relative overflow-x-auto overflow-y-auto">
            <svg
              className="w-full min-w-[980px] h-[1020px]"
              viewBox="0 0 1020 1020"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                {/* Glow Filter */}
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Edge Links */}
              {edges.map((edge, idx) => {
                const color = getTrackColor(edge.from.track);
                return (
                  <g key={`edge-${idx}`}>
                    <line
                      x1={edge.from.x + 60}
                      y1={edge.from.y + 20}
                      x2={edge.to.x}
                      y2={edge.to.y + 20}
                      stroke={edge.isHighlighted ? color : '#1E293B'}
                      strokeWidth={edge.isHighlighted ? 2.5 : 1.2}
                      strokeDasharray={edge.isHighlighted ? 'none' : '4 3'}
                      opacity={edge.isHighlighted ? 0.9 : 0.4}
                      className="transition-all duration-300"
                    />
                    {edge.isHighlighted && (
                      <circle
                        r={2.5}
                        fill={color}
                        opacity={0.8}
                      >
                        <animateMotion
                          path={`M${edge.from.x + 60},${edge.from.y + 20} L${edge.to.x},${edge.to.y + 20}`}
                          dur="1.8s"
                          repeatCount="indefinite"
                        />
                      </circle>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {filteredNodes.map((node) => {
                const isSelected = selectedNode?.id === node.id;
                const isHovered = hoveredNode?.id === node.id;
                const isRelated =
                  activeFocusNode?.prerequisites.includes(node.id) ||
                  activeFocusNode?.downstream.includes(node.id);
                const color = getTrackColor(node.track);

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    className="cursor-pointer"
                    onMouseEnter={() => setHoveredNode(node)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onClick={() => {
                      playKeyClick();
                      setSelectedNode(node);
                    }}
                  >
                    {/* Outer Glow on Selected/Hovered */}
                    {(isSelected || isHovered) && (
                      <rect
                        x="-4"
                        y="-4"
                        width="148"
                        height="48"
                        rx="14"
                        fill={color}
                        opacity={0.15}
                        filter="url(#glow)"
                      />
                    )}

                    {/* Node Box */}
                    <rect
                      x="0"
                      y="0"
                      width="140"
                      height="40"
                      rx="10"
                      fill="#0F172A"
                      stroke={isSelected ? color : isHovered ? '#FFFFFF' : isRelated ? color : '#334155'}
                      strokeWidth={isSelected ? 2 : 1}
                      className="transition-all duration-200"
                    />

                    {/* Left Accent Bar */}
                    <rect
                      x="0"
                      y="0"
                      width="4"
                      height="40"
                      rx="2"
                      fill={color}
                    />

                    {/* Node Text */}
                    <text
                      x="12"
                      y="18"
                      fontFamily="monospace"
                      fontSize="10"
                      fontWeight="bold"
                      fill={isSelected || isHovered ? '#FFFFFF' : '#E2E8F0'}
                    >
                      {node.name.length > 17 ? node.name.slice(0, 16) + '…' : node.name}
                    </text>

                    {/* Level / Premium Badge */}
                    <text
                      x="12"
                      y="32"
                      fontFamily="monospace"
                      fontSize="9"
                      fill={color}
                      fontWeight="600"
                    >
                      Tier {node.level} • +{node.premiumPct}% Val
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Node Deep Inspection Panel */}
        <aside className="rounded-2xl bg-surface-container-low border border-outline-variant p-space-md flex flex-col justify-between shadow-xl">
          {activeFocusNode ? (
            <div className="flex flex-col gap-space-md font-mono">
              <div className="border-b border-outline-variant/60 pb-3">
                <span className="text-[10px] text-outline uppercase tracking-wider block font-semibold">
                  Node Telemetry Inspection
                </span>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: getTrackColor(activeFocusNode.track) }}
                  />
                  <h3 className="text-base font-bold text-on-surface">
                    {activeFocusNode.name}
                  </h3>
                </div>
                <span className="text-[11px] text-secondary font-semibold block mt-0.5">
                  Tier {activeFocusNode.level} Specialization • +{activeFocusNode.premiumPct}% Market Leverage
                </span>
              </div>

              <div className="flex flex-col gap-1 text-xs">
                <span className="text-outline text-[11px] font-semibold uppercase">Scope & Architectural Focus:</span>
                <p className="text-on-surface-variant font-sans text-xs leading-relaxed bg-surface-container p-2.5 rounded-xl border border-outline-variant/40">
                  {activeFocusNode.description}
                </p>
              </div>

              {/* Prerequisites */}
              <div className="flex flex-col gap-1">
                <span className="text-outline text-[10px] font-semibold uppercase">Prerequisites:</span>
                {activeFocusNode.prerequisites.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {activeFocusNode.prerequisites.map((p) => {
                      const reqNode = CONSTELLATION_NODES.find((n) => n.id === p);
                      return (
                        <span
                          key={p}
                          className="px-2 py-0.5 rounded bg-surface-container-highest text-cyan-400 text-[10px] border border-cyan-500/20"
                        >
                          {reqNode?.name || p}
                        </span>
                      );
                    })}
                  </div>
                ) : (
                  <span className="text-[10px] text-outline">None (Foundational Pillar)</span>
                )}
              </div>

              {/* Downstream Unlocks */}
              <div className="flex flex-col gap-1">
                <span className="text-outline text-[10px] font-semibold uppercase">Directly Unlocks:</span>
                {activeFocusNode.downstream.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {activeFocusNode.downstream.map((d) => {
                      const downNode = CONSTELLATION_NODES.find((n) => n.id === d);
                      return (
                        <span
                          key={d}
                          className="px-2 py-0.5 rounded bg-surface-container-highest text-secondary text-[10px] border border-secondary/20"
                        >
                          {downNode?.name || d}
                        </span>
                      );
                    })}
                  </div>
                ) : (
                  <span className="text-[10px] text-outline">Apex Node (Domain Master)</span>
                )}
              </div>

              {/* Core Ingested Employers */}
              <div className="flex flex-col gap-1">
                <span className="text-outline text-[10px] font-semibold uppercase">Demanded by Portals:</span>
                <div className="flex flex-wrap gap-1">
                  {activeFocusNode.topEmployers.map((emp) => (
                    <span
                      key={emp}
                      className="px-2 py-0.5 rounded bg-surface-container text-on-surface text-[10px] border border-outline-variant/40"
                    >
                      {emp}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-outline text-xs font-mono">
              Hover or click any node to inspect tech tree dependencies.
            </div>
          )}

          {activeFocusNode && (
            <div className="pt-4 border-t border-outline-variant/60 flex flex-col gap-2">
              <button
                onClick={() => {
                  playKeyClick();
                  onSelectSkillFilter(activeFocusNode.id);
                }}
                className="w-full py-2.5 px-3 rounded-xl bg-primary text-on-primary font-mono text-xs font-bold hover:bg-primary/90 transition-all flex items-center justify-center gap-1.5 shadow-md shadow-primary/20"
              >
                <span className="material-symbols-outlined text-sm">filter_alt</span>
                <span>Lock Radar to {activeFocusNode.name}</span>
              </button>
              <span className="text-[10px] font-mono text-outline text-center block">
                Navigates to Radar with this skill active
              </span>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
};
