import re
from selectolax.parser import HTMLParser

# 1. STRICT ROLE FILTERING
INCLUDE_ROLE_KEYWORDS = [
    "engineer", "developer", "programmer", "devops", "sre", "deployment",
    "infrastructure", "cloud", "backend", "frontend", "fullstack", "full-stack",
    "systems", "embedded", "firmware", "kernel", "gpu", "cuda", "graphics",
    "rendering", "ai", "machine learning", "ml", "deep learning", "data scientist",
    "nlp", "computer vision", "robotics", "security", "network", "platform",
    "gameplay", "engine", "tools programmer", "technical", "architect", "qa automation"
]

EXCLUDE_ROLE_KEYWORDS = [
    "hr", "human resources", "recruiter", "talent acquisition", "finance",
    "accountant", "accounting", "sales", "marketing", "legal", "counsel",
    "illustrator", "animator", "concept artist", "character artist", "environment artist",
    "lighting artist", "sound designer", "writer", "narrative", "pr ", "communications",
    "office manager", "executive assistant", "payroll", "facilities"
]

# 2. CURATED SKILL TAXONOMY (Categorized for fast, 0ms extraction)
SKILL_PATTERNS = {
    # Languages
    "C++": r"\bc\+\+(?:14|17|20|23)?\b",
    "C": r"\bc\b(?!\+\+|#)",
    "Python": r"\bpython\b",
    "Rust": r"\brust\b",
    "Go": r"\b(?:golang|go)\b",
    "C#": r"\bc#\b",
    "TypeScript": r"\btypescript\b",
    "SQL": r"\b(?:sql|postgresql|mysql)\b",
    "Bash/Shell": r"\b(?:bash|shell scripting)\b",

    # GPU / Silicon / Embedded (NVIDIA, Qualcomm, etc.)
    "CUDA": r"\bcuda\b",
    "TensorRT": r"\btensorrt\b",
    "OpenCL": r"\bopencl\b",
    "RTOS": r"\b(?:rtos|freertos|qnx|zephyr)\b",
    "ARM": r"\b(?:arm|aarch64|cortex)\b",
    "Linux Kernel": r"\b(?:linux kernel|device drivers|embedded linux|yocto)\b",
    "Verilog/SystemVerilog": r"\b(?:verilog|systemverilog|vhdl|asic|fpga)\b",

    # Game Engines & Graphics (Rockstar, AAA Studios)
    "Unreal Engine": r"\b(?:unreal engine|ue4|ue5)\b",
    "Unity": r"\bunity\b",
    "Vulkan": r"\bvulkan\b",
    "DirectX": r"\b(?:directx|dx11|dx12|d3d12)\b",
    "OpenGL": r"\bopengl\b",
    "HLSL/GLSL Shaders": r"\b(?:hlsl|glsl|shaders)\b",
    "Physics/Math": r"\b(?:linear algebra|3d math|havok|physx)\b",

    # AI / ML
    "PyTorch": r"\bpytorch\b",
    "JAX": r"\bjax\b",
    "TensorFlow": r"\btensorflow\b",
    "LLMs / GenAI": r"\b(?:llm|large language models|rag|transformers|vllm|agentic)\b",

    # Deployment / DevOps / Cloud
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\b(?:kubernetes|k8s|helm)\b",
    "AWS": r"\baws\b",
    "GCP": r"\b(?:gcp|google cloud)\b",
    "Azure": r"\bazure\b",
    "CI/CD": r"\b(?:ci/cd|jenkins|github actions|gitlab ci)\b",
    "Terraform": r"\bterraform\b",
    "Kafka/Redis": r"\b(?:kafka|redis|rabbitmq)\b"
}

def is_engineering_or_deployment_role(title: str, department: str = "") -> bool:
    """Returns True ONLY if the role is strictly related to Dev, Engineering, or Deployment."""
    combined = f"{title} {department}".lower()
    
    # Immediately reject excluded departments/titles (HR, Sales, Art, etc.)
    if any(ex in combined for ex in EXCLUDE_ROLE_KEYWORDS):
        return False
        
    # Must match at least one engineering/deployment keyword
    return any(inc in combined for inc in INCLUDE_ROLE_KEYWORDS)

def clean_html(raw_html: str) -> str:
    """Strips HTML tags from career page descriptions."""
    if not raw_html:
        return ""
    tree = HTMLParser(raw_html)
    return tree.text(separator=" ")

def extract_skills_and_exp(raw_description: str) -> dict:
    """Extracts matched technical skills and minimum years of experience."""
    text = clean_html(raw_description)
    found_skills = []

    for skill_name, pattern in SKILL_PATTERNS.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            found_skills.append(skill_name)

    # Extract years of experience (e.g., "3+ years", "5-7 years")
    exp_match = re.search(r"(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s+(?:of\s+)?experience", text, re.IGNORECASE)
    min_years = int(exp_match.group(1)) if exp_match else None

    return {
        "skills": found_skills,
        "min_experience_years": min_years
    }
