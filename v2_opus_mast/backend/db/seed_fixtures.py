"""
DevRadar Demo Fixture Management CLI
Allows deterministic seeding and resetting of demo/synthetic fixtures with is_demo=True,
guaranteeing strict isolation from live career portal observations.

Usage:
    python -m backend.db.seed_fixtures --seed-demo
    python -m backend.db.seed_fixtures --seed-demo --include-unsupported
    python -m backend.db.seed_fixtures --reset-demo

Demo fixtures seed against registered sources even when live polling is disabled (EA, Qualcomm, G42).
Pass --include-unsupported only to seed jobs whose source_id is not in the registry.
"""
import sys
import argparse
import asyncio
import uuid
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from backend.db.session import async_session_factory, init_db
from backend.extraction.attributes import parse_seniority
from backend.db.models import (
    Source,
    Job,
    JobSnapshot,
    ExtractionRun,
    JobSkillEvidence,
    JobExperienceRequirement,
    JobLifecycleEvent,
    LifecycleStatus,
)

DEMO_JOBS = [
    {
        "posting_id": "demo-nv-01",
        "source_id": "nvidia_workday",
        "requisition_id": "JR199001",
        "internal_job_id": "INT-NV-01",
        "title": "Senior CUDA Systems Architect",
        "canonical_category": "Silicon & AI",
        "department": "Compute Architecture",
        "location": "Santa Clara, CA / Remote",
        "work_arrangement": "hybrid",
        "apply_url": "https://www.nvidia.com/careers/demo/cuda-architect",
        "min_yoe": 5,
        "skills": [
            ("cuda", "required", "5+ years developing high-throughput GPU kernels with CUDA and TensorRT."),
            ("cpp", "required", "Expert-level modern C++ (C++17/C++20) programming and memory optimization."),
            ("tensorrt", "preferred", "Hands-on experience optimizing inference graphs with TensorRT."),
            ("python", "preferred", "Python scripting for automated hardware validation harnesses."),
        ],
        "description": "NVIDIA is looking for a Senior CUDA Systems Architect to design next-generation accelerated computing kernels. Minimum 5 years of experience in low-level GPU acceleration, CUDA, and modern C++."
    },
    {
        "posting_id": "demo-nv-02",
        "source_id": "nvidia_workday",
        "requisition_id": "JR199002",
        "internal_job_id": "INT-NV-02",
        "title": "Deep Learning Compiler Engineer",
        "canonical_category": "Silicon & AI",
        "department": "AI Software Infrastructure",
        "location": "Austin, TX",
        "work_arrangement": "onsite",
        "apply_url": "https://www.nvidia.com/careers/demo/dl-compiler",
        "min_yoe": 4,
        "skills": [
            ("cpp", "required", "Deep expertise in C++ compiler backends, LLVM, or MLIR."),
            ("pytorch", "required", "Strong knowledge of PyTorch execution graph compilation."),
            ("triton", "preferred", "Experience authoring OpenAI Triton kernels or custom GPU dialects."),
        ],
        "description": "We are seeking a Compiler Engineer to build specialized compilation passes for deep learning models. Requires 4+ years of C++ compiler development and PyTorch internals."
    },
    {
        "posting_id": "demo-epic-01",
        "source_id": "epic_greenhouse",
        "requisition_id": "EPIC-REQ-8801",
        "internal_job_id": "INT-EPIC-01",
        "title": "Principal Unreal Engine Systems Programmer",
        "canonical_category": "Game Studio",
        "department": "Engine Core",
        "location": "Cary, NC / Remote",
        "work_arrangement": "hybrid",
        "apply_url": "https://www.epicgames.com/careers/demo/unreal-systems",
        "min_yoe": 6,
        "skills": [
            ("unreal_engine", "required", "Deep mastery of Unreal Engine 5 source code and architecture."),
            ("cpp", "required", "Extensive production experience writing performance-critical C++."),
            ("shaders", "preferred", "Familiarity with HLSL compute shaders and rendering pipelines."),
        ],
        "description": "Epic Games is searching for a Principal Unreal Engine Systems Programmer to architect core engine runtime systems. 6+ years in game development with Unreal Engine and C++."
    },
    {
        "posting_id": "demo-epic-02",
        "source_id": "epic_greenhouse",
        "requisition_id": "EPIC-REQ-8802",
        "internal_job_id": "INT-EPIC-02",
        "title": "Senior Vulkan Graphics Programmer",
        "canonical_category": "Game Studio",
        "department": "Rendering Team",
        "location": "Seattle, WA",
        "work_arrangement": "onsite",
        "apply_url": "https://www.epicgames.com/careers/demo/vulkan-graphics",
        "min_yoe": 4,
        "skills": [
            ("vulkan", "required", "Strong practical experience with low-level Vulkan and DirectX 12 APIs."),
            ("cpp", "required", "High-performance C++ rendering code and GPU profiling."),
            ("shaders", "required", "HLSL/GLSL shader authoring and optimization."),
        ],
        "description": "Join Epic Games to advance our cross-platform rendering engine using Vulkan and modern graphics hardware. Requires 4+ years in modern rendering APIs and C++."
    },
    {
        "posting_id": "demo-rockstar-01",
        "source_id": "rockstar_greenhouse",
        "requisition_id": "RS-REQ-701",
        "internal_job_id": "INT-RS-01",
        "title": "Lead Physics & Simulation Programmer",
        "canonical_category": "Game Studio",
        "department": "Physics Core",
        "location": "Edinburgh, UK",
        "work_arrangement": "onsite",
        "apply_url": "https://www.rockstargames.com/careers/demo/physics-programmer",
        "min_yoe": 5,
        "skills": [
            ("cpp", "required", "Expert C++ skills with deep understanding of multi-threaded physics solvers."),
            ("c", "preferred", "Low-level C systems programming and memory profiling."),
            ("directx", "preferred", "Experience debugging GPU compute physics via DirectX 12."),
        ],
        "description": "Rockstar North is looking for a Lead Physics & Simulation Programmer to build cutting-edge destruction and simulation tech in C++. Requires 5+ years experience in AAA physics."
    },
    {
        "posting_id": "demo-rockstar-02",
        "source_id": "rockstar_greenhouse",
        "requisition_id": "RS-REQ-702",
        "internal_job_id": "INT-RS-02",
        "title": "Core Engine Systems Engineer",
        "canonical_category": "Game Studio",
        "department": "Core Tech",
        "location": "New York, NY",
        "work_arrangement": "hybrid",
        "apply_url": "https://www.rockstargames.com/careers/demo/engine-systems",
        "min_yoe": 3,
        "skills": [
            ("cpp", "required", "Modern C++ and low-level cache-conscious systems architecture."),
            ("linux_kernel", "preferred", "Cross-platform OS runtime abstractions and profiling."),
        ],
        "description": "Rockstar Games is seeking an Engine Systems Engineer to optimize core streaming and asset pipelines. Minimum 3 years C++ experience in interactive entertainment."
    },
    {
        "posting_id": "demo-careem-01",
        "source_id": "careem_greenhouse",
        "requisition_id": "CAR-REQ-501",
        "internal_job_id": "INT-CAR-01",
        "title": "Staff Distributed Systems Engineer",
        "canonical_category": "UAE & Middle East",
        "department": "SuperApp Core",
        "location": "Dubai, UAE",
        "work_arrangement": "hybrid",
        "apply_url": "https://www.careem.com/careers/demo/distributed-systems",
        "min_yoe": 5,
        "skills": [
            ("go", "required", "Production experience with Go and high-concurrency microservices."),
            ("kubernetes", "required", "Kubernetes cluster operations and container orchestration."),
            ("aws", "preferred", "AWS cloud architecture and event-driven infrastructure."),
            ("sql", "required", "Advanced PostgreSQL / SQL data modeling and tuning."),
        ],
        "description": "Careem is looking for a Staff Distributed Systems Engineer in Dubai to build reliable event-driven backends. Requires 5+ years of Go, Kubernetes, and distributed architecture."
    },
    {
        "posting_id": "demo-careem-02",
        "source_id": "careem_greenhouse",
        "requisition_id": "CAR-REQ-502",
        "internal_job_id": "INT-CAR-02",
        "title": "Principal SRE & Platform Engineer",
        "canonical_category": "UAE & Middle East",
        "department": "Platform Reliability",
        "location": "Dubai, UAE / Remote",
        "work_arrangement": "remote",
        "apply_url": "https://www.careem.com/careers/demo/sre-platform",
        "min_yoe": 6,
        "skills": [
            ("terraform", "required", "Infrastructure as Code via Terraform across multi-region deployments."),
            ("kubernetes", "required", "Large-scale Kubernetes workload management."),
            ("docker", "required", "Container hardening and CI/CD pipelines."),
            ("python", "preferred", "Python automation and internal observability tooling."),
        ],
        "description": "Lead the SRE team at Careem to ensure 99.99% availability for millions of daily active users. Minimum 6 years of experience in Terraform, Kubernetes, and cloud infrastructure."
    },
    {
        "posting_id": "demo-qualcomm-01",
        "source_id": "qualcomm_eightfold",
        "requisition_id": "QC-REQ-901",
        "internal_job_id": "INT-QC-01",
        "title": "Staff Embedded RTOS Firmware Engineer",
        "canonical_category": "Silicon & AI",
        "department": "Modem Software",
        "location": "San Diego, CA",
        "work_arrangement": "onsite",
        "apply_url": "https://careers.qualcomm.com/demo/rtos-firmware",
        "min_yoe": 5,
        "skills": [
            ("c", "required", "Deep expertise in embedded C and bare-metal microcontroller programming."),
            ("rtos", "required", "Extensive experience with FreeRTOS or Zephyr real-time operating systems."),
            ("firmware", "required", "Hardware bring-up, JTAG debugging, and peripheral drivers."),
            ("arm", "preferred", "ARM Cortex-M / Cortex-A architecture profiling."),
        ],
        "description": "Qualcomm is seeking a Staff Firmware Engineer for our next-generation cellular modem chipsets. Requires 5+ years embedded C, RTOS, and board bring-up."
    },
    {
        "posting_id": "demo-g42-01",
        "source_id": "g42_phenom",
        "requisition_id": "G42-REQ-301",
        "internal_job_id": "INT-G42-01",
        "title": "Principal AI Cluster Infrastructure Engineer",
        "canonical_category": "UAE & Middle East",
        "department": "Inception AI",
        "location": "Abu Dhabi, UAE",
        "work_arrangement": "onsite",
        "apply_url": "https://careers.g42.ai/demo/ai-infra",
        "min_yoe": 6,
        "skills": [
            ("pytorch", "required", "PyTorch distributed training across multi-node GPU superclusters."),
            ("cuda", "required", "GPU acceleration and inter-node InfiniBand NCCL communication."),
            ("kubernetes", "required", "Slurm and Kubernetes AI scheduling pipelines."),
            ("python", "required", "Python AI orchestration tooling."),
        ],
        "description": "G42 is scaling supercomputing infrastructure for foundational LLM training in Abu Dhabi. Requires 6+ years in distributed training, CUDA, and high-performance computing."
    },
    {
        "posting_id": "demo-ea-01",
        "source_id": "ea_gr8people",
        "requisition_id": "EA-REQ-901",
        "internal_job_id": "INT-EA-01",
        "title": "Senior Frostbite Engine Programmer",
        "canonical_category": "Game Studio",
        "department": "Frostbite Core Tech",
        "location": "Stockholm, Sweden / Vancouver, BC",
        "work_arrangement": "hybrid",
        "apply_url": "https://www.ea.com/careers/demo/frostbite-engine",
        "min_yoe": 5,
        "skills": [
            ("cpp", "required", "Expert C++ programming and cache-conscious multi-core game engine architecture."),
            ("directx", "required", "DirectX 12 / D3D12 and Vulkan modern low-level graphics pipeline."),
            ("shaders", "preferred", "HLSL compute shaders and real-time raytracing optimization."),
        ],
        "description": "Join EA's Frostbite engine team to engineer low-level rendering and runtime systems powering EA SPORTS, Battlefield, and Need for Speed. Requires 5+ years in AAA game engine architecture and modern C++."
    },
    {
        "posting_id": "demo-ea-02",
        "source_id": "ea_gr8people",
        "requisition_id": "EA-REQ-902",
        "internal_job_id": "INT-EA-02",
        "title": "Gameplay Systems & Physics Engineer",
        "canonical_category": "Game Studio",
        "department": "Respawn Entertainment",
        "location": "Los Angeles, CA",
        "work_arrangement": "onsite",
        "apply_url": "https://www.ea.com/careers/demo/gameplay-physics",
        "min_yoe": 4,
        "skills": [
            ("cpp", "required", "Strong C++ gameplay systems architecture and deterministic networking."),
            ("physics_engine", "required", "Rigid body dynamics, character controllers, and vehicle physics simulation."),
            ("python", "preferred", "Python tools for rapid gameplay prototyping and telemetry."),
        ],
        "description": "Respawn Entertainment / EA is seeking a Gameplay Systems and Physics Engineer to architect next-generation player movement mechanics and physics solvers. Requires 4+ years in C++ gameplay and physics development."
    },
    {
        "posting_id": "demo-ps-01",
        "source_id": "naughtydog_greenhouse",
        "requisition_id": "ND-REQ-601",
        "internal_job_id": "INT-ND-01",
        "title": "Lead Gameplay & Systems Programmer",
        "canonical_category": "Game Studio",
        "department": "Gameplay Core",
        "location": "Santa Monica, CA",
        "work_arrangement": "onsite",
        "apply_url": "https://www.naughtydog.com/careers/demo/gameplay-programmer",
        "min_yoe": 5,
        "skills": [
            ("cpp", "required", "Deep modern C++ systems programming and memory optimization for PlayStation 5 hardware."),
            ("npc_ai", "required", "Combat AI, behavior trees, and procedural animation state machines."),
            ("simd", "preferred", "SIMD vector math optimization and cache-conscious data-oriented design."),
        ],
        "description": "Naughty Dog is looking for a Lead Gameplay & Systems Programmer to architect core gameplay and AI systems for our next franchise. Requires 5+ years C++ game development."
    }
]

async def seed_demo_fixtures(include_unsupported: bool = False):
    """Seeds deterministic demo fixtures marked with is_demo=True."""
    await init_db()
    now = datetime.now(timezone.utc)
    seeded_count = 0
    skipped_sources = set()

    async with async_session_factory() as session:
        for d in DEMO_JOBS:
            composite_id = f"{d['source_id']}:{d['posting_id']}"
            existing = await session.get(Job, composite_id)

            if existing:
                continue

            source = await session.get(Source, d["source_id"])
            if source is None:
                if not include_unsupported:
                    skipped_sources.add(d["source_id"])
                continue

            desc_hash = hashlib.sha256(d["description"].encode()).hexdigest()

            job = Job(
                job_id=composite_id,
                source_id=d["source_id"],
                provider_posting_id=d["posting_id"],
                requisition_id=d["requisition_id"],
                internal_job_id=d["internal_job_id"],
                is_demo=True,
                title=d["title"],
                canonical_category=d["canonical_category"],
                department=d["department"],
                location=d["location"],
                work_arrangement=d["work_arrangement"],
                seniority=parse_seniority(d["title"]),
                required_yoe=d["min_yoe"],
                apply_url=d["apply_url"],
                source_url=d["apply_url"],
                first_seen_at=now,
                last_seen_at=now,
                last_successfully_observed_at=now,
                consecutive_missing_syncs=0,
                lifecycle_status=LifecycleStatus.ACTIVE.value,
                normalized_description=d["description"],
                description_hash=desc_hash,
            )
            session.add(job)
            await session.flush()

            snapshot = JobSnapshot(
                job_id=job.job_id,
                observed_at=now,
                raw_payload_json="{}",
                normalized_text=d["description"],
                description_hash=desc_hash,
            )
            session.add(snapshot)
            await session.flush()

            ext_sig = hashlib.sha256((d["description"] + "1.0:1.0:1.0:deterministic").encode()).hexdigest()
            ext_run = ExtractionRun(
                run_id=str(uuid.uuid4()),
                job_id=job.job_id,
                snapshot_id=snapshot.snapshot_id,
                normalization_version="1.0",
                taxonomy_version="1.0",
                pipeline_version="1.0",
                extraction_method="deterministic",
                extraction_signature=ext_sig,
                created_at=now,
            )
            session.add(ext_run)
            await session.flush()

            event = JobLifecycleEvent(
                job_id=job.job_id,
                timestamp=now,
                previous_status="NONE",
                new_status=LifecycleStatus.ACTIVE.value,
                reason="Demo fixture seed",
            )
            session.add(event)

            for skill_id, req_type, quote in d["skills"]:
                session.add(JobSkillEvidence(
                    job_id=job.job_id,
                    snapshot_id=snapshot.snapshot_id,
                    extraction_run_id=ext_run.run_id,
                    skill_id=skill_id,
                    requirement_type=req_type,
                    evidence_text=quote,
                    extraction_method="deterministic",
                ))

            session.add(JobExperienceRequirement(
                job_id=job.job_id,
                snapshot_id=snapshot.snapshot_id,
                extraction_run_id=ext_run.run_id,
                min_years=d["min_yoe"],
                experience_scope="overall_professional",
                evidence_text=f"Requires {d['min_yoe']}+ years of professional engineering experience.",
            ))

            seeded_count += 1

        await session.commit()
    print(f"Successfully seeded {seeded_count} demo jobs (is_demo=True).")
    if skipped_sources:
        print(f"Skipped fixtures for unknown sources: {', '.join(sorted(skipped_sources))} (use --include-unsupported to seed them anyway).")

async def reset_demo_fixtures():
    """Removes all demo jobs and cascaded snapshots, extraction runs, and skills."""
    async with async_session_factory() as session:
        stmt = select(Job).where(Job.is_demo == True)
        demo_jobs = (await session.execute(stmt)).scalars().all()
        count = len(demo_jobs)

        for j in demo_jobs:
            await session.delete(j)

        await session.commit()
    print(f"Successfully removed {count} demo jobs (is_demo=True) and associated snapshots.")

def main():
    parser = argparse.ArgumentParser(description="DevRadar Demo Fixture Management")
    parser.add_argument("--seed-demo", action="store_true", help="Seed deterministic demo jobs (is_demo=True)")
    parser.add_argument("--reset-demo", action="store_true", help="Delete all demo fixtures (is_demo=True)")
    parser.add_argument("--include-unsupported", action="store_true", help="Also seed fixtures for disabled sources with no public feed")

    args = parser.parse_args()

    if args.seed_demo:
        asyncio.run(seed_demo_fixtures(include_unsupported=args.include_unsupported))
    elif args.reset_demo:
        asyncio.run(reset_demo_fixtures())
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
