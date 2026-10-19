import re
from typing import List, Dict, Any, Optional

TAXONOMY_SPECS = [
    # Languages
    {
        "skill_id": "cpp",
        "skill_name": "C++",
        "category": "Languages",
        "pattern": r"\bc\+\+(?:11|14|17|20|23)?(?![a-zA-Z0-9#+])",
    },
    {
        "skill_id": "csharp",
        "skill_name": "C#",
        "category": "Languages",
        "pattern": r"(?:\bc#(?![a-zA-Z0-9#+])|\bc-sharp\b|\bcsharp\b|\b\.net core\b)",
    },
    {
        "skill_id": "c",
        "skill_name": "C",
        "category": "Languages",
        # Strictly require context: C/C++, C or C++, Embedded C, programming in C
        "pattern": r"\b(?:c\s*/\s*c\+\+|c\s+or\s+c\+\+|embedded\s+c|programming\s+in\s+c|ansi\s+c)\b",
    },
    {
        "skill_id": "python",
        "skill_name": "Python",
        "category": "Languages",
        "pattern": r"\bpython(?:3)?\b",
    },
    {
        "skill_id": "rust",
        "skill_name": "Rust",
        "category": "Languages",
        "pattern": r"\brust\b",
    },
    {
        "skill_id": "go",
        "skill_name": "Go",
        "category": "Languages",
        # Never match colloquial English verb "go"
        "pattern": r"\b(?:golang|programming\s+in\s+go|go\s*developer|go\s*backend|go\s*/\s*(?:python|c\+\+|rust)|(?:python|c\+\+|rust)\s*/\s*go)\b",
    },
    {
        "skill_id": "typescript",
        "skill_name": "TypeScript",
        "category": "Languages",
        "pattern": r"\btypescript\b",
    },
    {
        "skill_id": "sql",
        "skill_name": "SQL",
        "category": "Languages",
        "pattern": r"\b(?:sql|postgresql|postgres|mysql|sqlite)\b",
    },

    # GPU / Silicon / Performance
    {
        "skill_id": "cuda",
        "skill_name": "CUDA",
        "category": "GPU / Silicon",
        "pattern": r"\bcuda\b",
    },
    {
        "skill_id": "tensorrt",
        "skill_name": "TensorRT",
        "category": "GPU / Silicon",
        "pattern": r"\btensorrt\b",
    },
    {
        "skill_id": "triton",
        "skill_name": "Triton",
        "category": "GPU / Silicon",
        "pattern": r"\b(?:triton|openai triton)\b",
    },
    {
        "skill_id": "rtos",
        "skill_name": "RTOS",
        "category": "Embedded & Systems",
        "pattern": r"\b(?:rtos|freertos|qnx|zephyr|vxworks)\b",
    },
    {
        "skill_id": "firmware",
        "skill_name": "Firmware",
        "category": "Embedded & Systems",
        "pattern": r"\bfirmware\b",
    },
    {
        "skill_id": "linux_kernel",
        "skill_name": "Linux Kernel",
        "category": "Embedded & Systems",
        "pattern": r"\b(?:linux kernel|device drivers?|embedded linux|yocto|ebpf)\b",
    },
    {
        "skill_id": "arm",
        "skill_name": "ARM Architecture",
        "category": "Embedded & Systems",
        "pattern": r"\b(?:arm|aarch64|cortex-m|cortex-a)\b",
    },
    {
        "skill_id": "verilog",
        "skill_name": "Verilog/VHDL",
        "category": "GPU / Silicon",
        "pattern": r"\b(?:verilog|systemverilog|vhdl|asic|fpga)\b",
    },

    # Graphics & Game Engines
    {
        "skill_id": "unreal_engine",
        "skill_name": "Unreal Engine",
        "category": "Graphics & Games",
        "pattern": r"\b(?:unreal engine|ue4|ue5|unreal)\b",
    },
    {
        "skill_id": "unity",
        "skill_name": "Unity",
        "category": "Graphics & Games",
        "pattern": r"\b(?:unity3d|unity engine|unity)\b",
    },
    {
        "skill_id": "vulkan",
        "skill_name": "Vulkan",
        "category": "Graphics & Games",
        "pattern": r"\bvulkan\b",
    },
    {
        "skill_id": "directx",
        "skill_name": "DirectX / D3D12",
        "category": "Graphics & Games",
        "pattern": r"\b(?:directx|dx11|dx12|d3d11|d3d12)\b",
    },
    {
        "skill_id": "opengl",
        "skill_name": "OpenGL",
        "category": "Graphics & Games",
        "pattern": r"\bopengl(?:\s*es)?\b",
    },
    {
        "skill_id": "shaders",
        "skill_name": "HLSL / GLSL Shaders",
        "category": "Graphics & Games",
        "pattern": r"\b(?:hlsl|glsl|shader development|compute shaders?)\b",
    },

    # AI / ML
    {
        "skill_id": "pytorch",
        "skill_name": "PyTorch",
        "category": "AI / ML",
        "pattern": r"\bpytorch\b",
    },
    {
        "skill_id": "tensorflow",
        "skill_name": "TensorFlow",
        "category": "AI / ML",
        "pattern": r"\btensorflow\b",
    },
    {
        "skill_id": "jax",
        "skill_name": "JAX",
        "category": "AI / ML",
        "pattern": r"\bjax\b",
    },
    {
        "skill_id": "llm",
        "skill_name": "LLMs / Transformers",
        "category": "AI / ML",
        "pattern": r"\b(?:llm|large language models?|rag|transformers?|vllm|agentic)\b",
    },
    {
        "skill_id": "distributed_training",
        "skill_name": "Distributed Training",
        "category": "AI / ML",
        "pattern": r"\b(?:distributed training|megatron|deepspeed|fsdp|nccl)\b",
    },

    # Cloud & DevOps / Infra
    {
        "skill_id": "docker",
        "skill_name": "Docker",
        "category": "Deployment & Cloud",
        "pattern": r"\bdocker\b",
    },
    {
        "skill_id": "kubernetes",
        "skill_name": "Kubernetes",
        "category": "Deployment & Cloud",
        "pattern": r"\b(?:kubernetes|k8s|helm)\b",
    },
    {
        "skill_id": "aws",
        "skill_name": "AWS",
        "category": "Deployment & Cloud",
        "pattern": r"\b(?:aws|amazon web services)\b",
    },
    {
        "skill_id": "gcp",
        "skill_name": "Google Cloud",
        "category": "Deployment & Cloud",
        "pattern": r"\b(?:gcp|google cloud)\b",
    },
    {
        "skill_id": "ci_cd",
        "skill_name": "CI/CD",
        "category": "Deployment & Cloud",
        "pattern": r"\b(?:ci/cd|github actions|gitlab ci|jenkins)\b",
    },
    {
        "skill_id": "terraform",
        "skill_name": "Terraform",
        "category": "Deployment & Cloud",
        "pattern": r"\bterraform\b",
    },

    # AI NPC & Game AI
    {
        "skill_id": "npc_ai",
        "skill_name": "NPC AI / Game AI",
        "category": "AI & Game AI",
        "pattern": r"\b(?:npc ai|game ai|gameplay ai|ai characters?|virtual beings?)\b",
    },
    {
        "skill_id": "behavior_trees",
        "skill_name": "Behavior Trees",
        "category": "AI & Game AI",
        "pattern": r"\b(?:behavior trees?|bt)\b",
    },
    {
        "skill_id": "fsm",
        "skill_name": "Finite State Machines (FSM)",
        "category": "AI & Game AI",
        "pattern": r"\b(?:finite state machines?|fsm|hierarchical state machines?)\b",
    },
    {
        "skill_id": "goap",
        "skill_name": "GOAP",
        "category": "AI & Game AI",
        "pattern": r"\b(?:goap|goal-oriented action planning)\b",
    },
    {
        "skill_id": "utility_ai",
        "skill_name": "Utility AI",
        "category": "AI & Game AI",
        "pattern": r"\butility ai\b",
    },
    {
        "skill_id": "pathfinding",
        "skill_name": "Pathfinding / NavMesh",
        "category": "AI & Game AI",
        "pattern": r"\b(?:pathfinding|navmesh|navigation mesh|recast|a\*|a-star)\b",
    },
    {
        "skill_id": "crowd_simulation",
        "skill_name": "Crowd Simulation",
        "category": "AI & Game AI",
        "pattern": r"\b(?:crowd simulation|detour|boids|flocking|massentity|mass entity)\b",
    },
    {
        "skill_id": "reinforcement_learning",
        "skill_name": "Reinforcement Learning (RL)",
        "category": "AI & Game AI",
        "pattern": r"\b(?:reinforcement learning|deep rl|ppo|q-learning)\b",
    },
    {
        "skill_id": "agentic_ai",
        "skill_name": "Agentic AI / SLMs",
        "category": "AI & Game AI",
        "pattern": r"\b(?:agentic ai|autonomous agents?|small language models?|slms?|on-device inference|nvidia ace)\b",
    },
    {
        "skill_id": "eqs",
        "skill_name": "Environment Query System (EQS)",
        "category": "AI & Game AI",
        "pattern": r"\b(?:eqs|environment query system)\b",
    },

    # Physics & Simulation
    {
        "skill_id": "physics_engine",
        "skill_name": "Physics Engine & Dynamics",
        "category": "Physics & Simulation",
        "pattern": r"\b(?:physics engines?|rigid body(?: dynamics)?|multibody dynamics)\b",
    },
    {
        "skill_id": "collision_detection",
        "skill_name": "Collision Detection",
        "category": "Physics & Simulation",
        "pattern": r"\b(?:collision detection|gjk|epa|broadphase|narrowphase|spatial partitioning)\b",
    },
    {
        "skill_id": "ragdoll_physics",
        "skill_name": "Ragdoll & IK",
        "category": "Physics & Simulation",
        "pattern": r"\b(?:ragdoll|ragdoll physics|inverse kinematics|\bik\b|fabrik)\b",
    },
    {
        "skill_id": "procedural_animation",
        "skill_name": "Procedural Animation",
        "category": "Physics & Simulation",
        "pattern": r"\b(?:procedural animation|motion matching)\b",
    },
    {
        "skill_id": "physics_middleware",
        "skill_name": "Havok / PhysX / Chaos",
        "category": "Physics & Simulation",
        "pattern": r"\b(?:havok|physx|chaos physics)\b",
    },
    {
        "skill_id": "simd",
        "skill_name": "SIMD / Vector Math",
        "category": "Physics & Simulation",
        "pattern": r"\b(?:simd|avx|avx-512|neon|sse4)\b",
    },
    {
        "skill_id": "linear_algebra",
        "skill_name": "Linear Algebra & 3D Math",
        "category": "Physics & Simulation",
        "pattern": r"\b(?:linear algebra|3d math|quaternions?|matrix math)\b",
    },
    {
        "skill_id": "simulation_frameworks",
        "skill_name": "MuJoCo / Isaac Sim / Omniverse",
        "category": "Physics & Simulation",
        "pattern": r"\b(?:mujoco|isaac sim|isaac gym|nvidia isaac|omniverse|openusd|ros2|sensor fusion)\b",
    },

    # GPU / Accelerators / Silicon
    {
        "skill_id": "rocm",
        "skill_name": "ROCm / HIP",
        "category": "GPU / Silicon",
        "pattern": r"\b(?:rocm|hip)\b",
    },
    {
        "skill_id": "opencl",
        "skill_name": "OpenCL",
        "category": "GPU / Silicon",
        "pattern": r"\bopencl\b",
    },
    {
        "skill_id": "gpu_kernels",
        "skill_name": "GPU Kernels & Optimization",
        "category": "GPU / Silicon",
        "pattern": r"\b(?:gpu kernels?|compute kernels?|kernel optimization|nsight|warp-level)\b",
    },
    {
        "skill_id": "parallel_computing",
        "skill_name": "Parallel Computing",
        "category": "GPU / Silicon",
        "pattern": r"\b(?:parallel computing|multithreading|concurrency|openmp|mpi)\b",
    },

    # Edge AI & Embedded ECE
    {
        "skill_id": "freertos",
        "skill_name": "FreeRTOS / Zephyr / QNX",
        "category": "Embedded & Systems",
        "pattern": r"\b(?:freertos|zephyr|qnx)\b",
    },
    {
        "skill_id": "device_drivers",
        "skill_name": "Device Drivers & BSP",
        "category": "Embedded & Systems",
        "pattern": r"\b(?:device drivers?|bsp|board support package)\b",
    },
    {
        "skill_id": "microcontrollers",
        "skill_name": "Microcontrollers & Embedded Protocols",
        "category": "Embedded & Systems",
        "pattern": r"\b(?:microcontrollers?|mcu|stm32|esp32|uart|spi|i2c|can bus|can-bus)\b",
    },
    {
        "skill_id": "model_quantization",
        "skill_name": "Model Quantization & ONNX",
        "category": "Embedded & Systems",
        "pattern": r"\b(?:onnx|onnx runtime|model quantization|int8|int4|fp8|quantization|tensorrt-llm|tinyml)\b",
    },

    # AI Servers & Cloud Infra
    {
        "skill_id": "distributed_systems",
        "skill_name": "Distributed Systems",
        "category": "Deployment & Cloud",
        "pattern": r"\b(?:distributed systems|distributed storage|consensus|raft|grpc)\b",
    },
    {
        "skill_id": "rdma_networking",
        "skill_name": "RDMA & High-Speed Networking",
        "category": "Deployment & Cloud",
        "pattern": r"\b(?:rdma|roce|infiniband|tcp/ip|sockets?)\b",
    },
    {
        "skill_id": "sre",
        "skill_name": "SRE & Reliability",
        "category": "Deployment & Cloud",
        "pattern": r"\b(?:sre|site reliability|observability|prometheus|grafana)\b",
    },
]

PREFERRED_CLUES = [
    r"nice\s+to\s+have",
    r"is\s+a\s+plus",
    r"bonus\s+points",
    r"preferred",
    r"advantageous",
    r"would\s+be\s+an\s+asset",
    r"desirable",
]

def _compact(value: str) -> str:
    return re.sub(r"[\s_\-]", "", value.lower())

def resolve_skill(text: str, taxonomy: List[Dict[str, Any]] = TAXONOMY_SPECS) -> Optional[Dict[str, Any]]:
    """
    Maps free-typed skill text ("C++", "c#", "k8s") to a taxonomy entry.
    Returns None for anything the taxonomy does not know.
    """
    query = (text or "").strip()
    if not query:
        return None
    lower = query.lower()
    compact = _compact(query)

    for spec in taxonomy:
        name = spec["skill_name"].lower()
        if lower in (spec["skill_id"], name) or compact in (_compact(spec["skill_id"]), _compact(name)):
            return spec

    matches = [spec for spec in taxonomy if re.search(spec["pattern"], lower, flags=re.IGNORECASE)]
    if len(matches) == 1:
        return matches[0]
    full_matches = [spec for spec in matches if re.fullmatch(spec["pattern"], lower, flags=re.IGNORECASE)]
    if full_matches:
        return full_matches[0]
    return None

def split_into_sentences(text: str) -> List[str]:
    """Splits text into clean sentence units using punctuation, newlines, and bullet points."""
    raw = re.split(r"(?<=[.!?])\s+|\n+|[-•*]\s+", text)
    return [s.strip() for s in raw if s.strip()]

def is_skill_negated(sentence: str, skill_pattern: str) -> bool:
    """Checks if a skill mention is explicitly negated within its sentence."""
    lower = sentence.lower()
    # Pattern 1: skill ... is not required
    if re.search(rf"{skill_pattern}\s+(?:is\s+)?not\s+(?:required|needed|mandatory|essential)", lower):
        return True
    # Pattern 2: not required / no experience in ... skill
    if re.search(rf"(?:not\s+(?:required|needed)|no\s+(?:prior\s+)?experience\s+(?:with|in))\s+.*?{skill_pattern}", lower):
        return True
    return False

def extract_skills_with_evidence(
    sections: Dict[str, List[str]],
    taxonomy: List[Dict[str, Any]] = TAXONOMY_SPECS,
) -> List[Dict[str, Any]]:
    """
    Extracts skills from segmented job sections with verbatim evidence text and requirement level.
    """
    results: Dict[str, Dict[str, Any]] = {}

    for sec_name, lines in sections.items():
        # Iterate line by line to preserve precise sentence and bullet isolation
        for line in lines:
            sentences = split_into_sentences(line)

            for sent in sentences:
                lower_sent = sent.lower()

                for spec in taxonomy:
                    skill_id = spec["skill_id"]
                    pat = spec["pattern"]

                    if re.search(pat, lower_sent, flags=re.IGNORECASE):
                        # Check for scoped negation
                        if is_skill_negated(sent, pat):
                            continue

                        # Determine requirement type
                        req_type = "mentioned"
                        if sec_name == "REQUIRED_SECTION":
                            req_type = "required"
                        elif sec_name == "PREFERRED_SECTION":
                            req_type = "preferred"
                        elif sec_name == "COMPANY_BOILERPLATE":
                            req_type = "mentioned"
                        else:
                            # Inspect sentence clues
                            if any(re.search(clue, lower_sent) for clue in PREFERRED_CLUES):
                                req_type = "preferred"
                            elif re.search(r"\b(?:must have|required|proficient in|essential)\b", lower_sent):
                                req_type = "required"

                        # If already seen, prioritize 'required' > 'preferred' > 'mentioned'
                        if skill_id in results:
                            existing_type = results[skill_id]["requirement_type"]
                            if req_type == "required" or (req_type == "preferred" and existing_type == "mentioned"):
                                results[skill_id]["requirement_type"] = req_type
                                results[skill_id]["evidence_text"] = sent
                        else:
                            results[skill_id] = {
                                "skill_id": skill_id,
                                "skill_name": spec["skill_name"],
                                "category": spec["category"],
                                "requirement_type": req_type,
                                "evidence_text": sent,
                                "extraction_method": "deterministic",
                                "taxonomy_version": "1.0",
                                "pipeline_version": "1.0",
                            }

    return list(results.values())
