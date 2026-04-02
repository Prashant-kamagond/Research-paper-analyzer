"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    """Yield a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_txt_file(tmp_dir):
    """Write a small plain-text 'paper' to a temp file."""
    content = (
        "Abstract\n\n"
        "This paper proposes a novel approach to natural language processing "
        "using transformer architectures. We demonstrate state-of-the-art "
        "results on multiple benchmarks.\n\n"
        "Introduction\n\n"
        "Recent advances in deep learning have led to significant improvements "
        "in natural language understanding tasks. In particular, attention "
        "mechanisms and large pre-trained models have revolutionised the field.\n\n"
        "Methods\n\n"
        "We fine-tune a BERT-based model on domain-specific data. "
        "The training procedure uses a learning rate of 2e-5 and batch size 32 "
        "for 10 epochs.\n\n"
        "Results\n\n"
        "Our approach achieves 94.3% accuracy on the test set, outperforming "
        "previous baselines by 3.2 percentage points.\n\n"
        "Conclusion\n\n"
        "We have shown that domain-specific fine-tuning significantly improves "
        "performance on specialised NLP tasks."
    )
    path = tmp_dir / "sample_paper.txt"
    path.write_text(content, encoding="utf-8")
    return path
