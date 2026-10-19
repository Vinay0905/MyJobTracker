import json
import pytest
from backend.extraction.pipeline import process_job_description
from backend.extraction.filter import is_engineering_role
from backend.extraction.taxonomy import extract_skills_with_evidence
from backend.extraction.normalizer import segment_description
from backend.extraction.experience import extract_experience_requirements

def test_go_verb_adversarial():
    # colloquial "go" should not trigger Go skill unless Golang/tech context is present
    bad_text = "You will go to the office and go through technical reviews. Write clean code in Python."
    res = process_job_description("Software Engineer", "Core", bad_text)
    skill_ids = [s["skill_id"] for s in res["skills"]]
    assert "go" not in skill_ids
    assert "python" in skill_ids

    # Real Golang/Go programming context should match
    good_text = "Building high-performance distributed engines with Golang and gRPC."
    res2 = process_job_description("Software Engineer", "Core", good_text)
    skill_ids2 = [s["skill_id"] for s in res2["skills"]]
    assert "go" in skill_ids2

def test_c_family_disambiguation():
    desc = """
    What you'll need:
    - 5+ years of C++ (modern C++20)
    - Experience in Embedded C programming
    Bonus Points:
    - Desktop UI development in C#
    """
    res = process_job_description("Senior Systems Engineer", "Embedded", desc)
    skill_map = {s["skill_id"]: s["requirement_type"] for s in res["skills"]}

    assert "cpp" in skill_map
    assert "c" in skill_map
    assert "csharp" in skill_map

    assert skill_map["cpp"] == "required"
    assert skill_map["c"] == "required"
    assert skill_map["csharp"] == "preferred"

def test_negation_detection():
    desc = """
    Requirements:
    - Proficiency with PyTorch and deep learning architectures
    - Prior experience with CUDA is not required for this position
    """
    res = process_job_description("Machine Learning Engineer", "AI", desc)
    skill_ids = [s["skill_id"] for s in res["skills"]]
    assert "pytorch" in skill_ids
    assert "cuda" not in skill_ids

def test_role_rejection_filter():
    is_eng, _ = is_engineering_role("HR Specialist", "People Ops", "Manage employee records")
    assert not is_eng

    is_eng, _ = is_engineering_role("Technical Recruiter", "Talent Acquisition", "Source software engineers")
    assert not is_eng

    is_eng, _ = is_engineering_role("2D Concept Artist", "Art", "Create character illustrations")
    assert not is_eng

    is_eng, _ = is_engineering_role("Staff Compiler Engineer", "Systems", "Develop LLVM backends")
    assert is_eng

def test_experience_scope_extraction():
    desc = """
    Qualifications:
    - 5+ years of software engineering experience
    - 3+ years of hands-on experience with C++ and CUDA
    - Bachelor's degree or 4 years equivalent practical experience
    """
    exp = extract_experience_requirements(desc)
    scopes = {e["experience_scope"]: e["min_years"] for e in exp}

    assert "overall_professional" in scopes
    assert scopes["overall_professional"] == 5

    assert "skill_specific" in scopes
    assert scopes["skill_specific"] == 3

    assert "degree_equivalent" in scopes
    assert scopes["degree_equivalent"] == 4
