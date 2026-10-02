from __future__ import annotations

import pytest

from backend.tools.paper_tools import clear_papers, register_paper


@pytest.fixture
def minimal_valid_paper():
    paper = {
        "paper_id": "minimal-valid-paper",
        "title": "Minimal Valid Paper",
        "abstract": "We propose a method that improves performance on a benchmark dataset.",
        "sections": [
            {"name": "Abstract", "page": 1, "text": "We propose a method that improves performance on a benchmark dataset."},
            {"name": "Introduction", "page": 2, "text": "This paper introduces a lightweight method for multi-task learning. We describe the problem setting and the motivation for our approach."},
            {"name": "Related Work", "page": 3, "text": "Prior work on multi-task learning and domain adaptation is discussed. We compare against a representative baseline and explain why the proposed model is different."},
            {"name": "Methodology", "page": 4, "text": "We use a two-stage encoder and a linear head. The method is trained with Adam for 50 epochs on the benchmark dataset. We report the implementation details and hyperparameters."},
            {"name": "Experiments", "page": 5, "text": "We compare against a strong baseline and report accuracy, F1, and runtime. The gains are statistically significant and the setup is reproducible."},
            {"name": "Results", "page": 6, "text": "The model achieves 92.4% accuracy and improves F1 over the baseline. The gains remain consistent across tasks."},
            {"name": "Discussion", "page": 7, "text": "We explain the contributions and limitations of the proposed approach. The approach is robust and interpretable."},
            {"name": "Conclusion", "page": 8, "text": "The method provides a useful contribution to the benchmark setting and clarifies the design choices."},
            {"name": "References", "page": 9, "text": "[1] Doe et al. (2021). [2] Smith et al. (2022). [3] Chen et al. (2024)."},
        ],
        "pages": [
            {"page": 1, "text": "We propose a method that improves performance on a benchmark dataset."},
            {"page": 2, "text": "This paper introduces a lightweight method for multi-task learning. We describe the problem setting and the motivation for our approach."},
            {"page": 3, "text": "Prior work on multi-task learning and domain adaptation is discussed. We compare against a representative baseline and explain why the proposed model is different."},
            {"page": 4, "text": "We use a two-stage encoder and a linear head. The method is trained with Adam for 50 epochs on the benchmark dataset. We report the implementation details and hyperparameters."},
            {"page": 5, "text": "We compare against a strong baseline and report accuracy, F1, and runtime. The gains are statistically significant and the setup is reproducible."},
            {"page": 6, "text": "The model achieves 92.4% accuracy and improves F1 over the baseline. The gains remain consistent across tasks."},
            {"page": 7, "text": "We explain the contributions and limitations of the proposed approach. The approach is robust and interpretable."},
            {"page": 8, "text": "The method provides a useful contribution to the benchmark setting and clarifies the design choices."},
            {"page": 9, "text": "[1] Doe et al. (2021). [2] Smith et al. (2022). [3] Chen et al. (2024)."},
        ],
        "references": [
            {"title": "Doe et al. (2021)", "year": 2021},
            {"title": "Smith et al. (2022)", "year": 2022},
            {"title": "Chen et al. (2024)", "year": 2024},
        ],
        "figures": [{"figure_number": 1, "caption": "Architecture summary"}],
        "tables": [{"table_number": 1, "caption": "Main benchmark results"}],
    }
    register_paper(paper["paper_id"], paper)
    return paper


@pytest.fixture
def strong_paper(minimal_valid_paper):
    return minimal_valid_paper


@pytest.fixture
def weak_paper():
    paper = {
        "paper_id": "weak-paper",
        "title": "A Curious Method for Everything",
        "abstract": "We propose a completely new method that is obviously better than everything before it.",
        "sections": [
            {"name": "Abstract", "page": 1, "text": "We propose a completely new method that is obviously better than everything before it."},
            {"name": "Introduction", "page": 2, "text": "Our system contains three modules. We propose the first universal framework for all tasks. The model uses TAM without definition. The method is clearly better."},
            {"name": "Methodology", "page": 3, "text": "Our system contains four modules. The method is trained with the step size 0.001, but we also mention 0.01 elsewhere. We omit details of the optimizer and evaluation setting."},
            {"name": "Experiments", "page": 4, "text": "We outperform every baseline by a huge margin. No statistical test, baseline specification, or CI is reported. The method improves accuracy by 0.4%."},
            {"name": "Results", "page": 5, "text": "We show significant improvement. The model does better than the baseline and all other approaches. We ignore prior work and claim full novelty."},
            {"name": "Discussion", "page": 6, "text": "Our approach is significantly better and clearly more novel than all previous work. We do not clarify why this is true."},
            {"name": "Conclusion", "page": 7, "text": "This is the best paper ever written."},
            {"name": "References", "page": 8, "text": "[1] Smith et al. (2023). [2] Smith et al. (2023). [3] Alpha et al. (2024)."},
        ],
        "pages": [
            {"page": 1, "text": "We propose a completely new method that is obviously better than everything before it."},
            {"page": 2, "text": "Our system contains three modules. We propose the first universal framework for all tasks. The model uses TAM without definition. The method is clearly better."},
            {"page": 3, "text": "Our system contains four modules. The method is trained with the step size 0.001, but we also mention 0.01 elsewhere. We omit details of the optimizer and evaluation setting."},
            {"page": 4, "text": "We outperform every baseline by a huge margin. No statistical test, baseline specification, or CI is reported. The method improves accuracy by 0.4%."},
            {"page": 5, "text": "We show significant improvement. The model does better than the baseline and all other approaches. We ignore prior work and claim full novelty."},
            {"page": 6, "text": "Our approach is significantly better and clearly more novel than all previous work. We do not clarify why this is true."},
            {"page": 7, "text": "This is the best paper ever written."},
            {"page": 8, "text": "[1] Smith et al. (2023). [2] Smith et al. (2023). [3] Alpha et al. (2024)."},
        ],
        "references": [
            {"title": "Smith et al. (2023)", "year": 2023},
            {"title": "Smith et al. (2023)", "year": 2023},
            {"title": "Alpha et al. (2024)", "year": 2024},
        ],
        "figures": [{"figure_number": 2, "caption": "Architectural overview"}],
        "tables": [{"table_number": 2, "caption": "Performance summary"}],
    }
    register_paper(paper["paper_id"], paper)
    return paper


@pytest.fixture
def conflicting_review_outputs():
    return {
        "rigor": {
            "reviewer": "rigor",
            "summary": "Methodological evidence is weak.",
            "issues": [{
                "id": "RIGOR-1",
                "section": "Experiments",
                "page": 7,
                "severity": "High",
                "type": "experimental_claim",
                "issue": "The paper lacks a baseline comparison and significance testing.",
                "explanation": "The claim is not supported by the experiment setup.",
                "evidence": [{"page": 7, "section": "Experiments", "text": "No baseline analysis was provided."}],
                "recommendation": "Add proper baselines and significance tests.",
                "tools_used": ["read_paper", "locate_evidence"],
            }],
        },
        "novelty": {
            "reviewer": "novelty",
            "summary": "No strong novelty concern after literature review.",
            "issues": [{
                "id": "NOVELTY-1",
                "section": "Introduction",
                "page": 2,
                "severity": "Low",
                "type": "novelty_gap",
                "issue": "The paper's contribution is modest but not clearly unsupported.",
                "explanation": "No direct overlap was identified.",
                "evidence": [{"page": 2, "section": "Introduction", "text": "The claim is framed as a contribution."}],
                "recommendation": "Clarify the positioning relative to related work.",
                "tools_used": ["search_literature"],
            }],
        },
        "clarity": {
            "reviewer": "clarity",
            "summary": "Mostly clear but some terms should be defined.",
            "issues": [{
                "id": "CLARITY-1",
                "section": "Introduction",
                "page": 2,
                "severity": "Low",
                "type": "undefined_term",
                "issue": "The acronym TAM is used before it is defined.",
                "explanation": "The acronym is introduced without a definition.",
                "evidence": [{"page": 2, "section": "Introduction", "text": "The model uses TAM without definition."}],
                "recommendation": "Define the acronym on first use.",
                "tools_used": ["read_paper", "check_terminology"],
            }],
        },
    }


@pytest.fixture
def approval_feedback():
    return [{
        "issue_id": "RIGOR-1",
        "decision": "approve",
        "reason": "The evidence confirms this issue.",
    }]


@pytest.fixture
def dispute_feedback():
    return [{
        "issue_id": "RIGOR-1",
        "decision": "dispute",
        "reason": "The reviewer misunderstood the experiment section.",
    }]


@pytest.fixture(autouse=True)
def clear_store():
    clear_papers()
    yield
    clear_papers()
