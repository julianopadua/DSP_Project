"""Auditoria leve do manuscrito e dos artefatos do artigo."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

from src.config import PAPER_PROCESSED_DIR, PROJECT_ROOT

ARTICLE_DIR = PROJECT_ROOT / "docs" / "paper" / "article"
FIGURE_DIR = ARTICLE_DIR / "figures"

FORBIDDEN_TEXT_PATTERNS = {
    "formulação proibida": re.compile(r"\b(Este artigo|Este trabalho|Neste trabalho)\b"),
    "travessão/en dash": re.compile(r"[—–]"),
    "autoria em legenda": re.compile(r"esquema autoral|figura própria", re.IGNORECASE),
}

GENERATED_LATEX = (
    "main.aux",
    "main.bbl",
    "main.blg",
    "main.fdb_latexmk",
    "main.fls",
    "main.log",
    "main.out",
    "main.pdf",
)

TRACKED_ARTICLE_SAMPLES = (
    "docs/paper/article/main.tex",
    "docs/paper/article/ref.bib",
    "docs/paper/article/arxiv.sty",
    "docs/paper/article/figures/fig_model_precision_recall.pdf",
    "docs/paper/article/figures/fig_confusion_matrices.pdf",
)

IGNORED_SAMPLES = (
    "llm-wiki/wiki/index.md",
    "data/processed/paper/metrics_ablation.csv",
    "docs/paper/article/main.pdf",
    "docs/paper/article/main.aux",
    "docs/paper/template_raw/abstract.tex",
    "docs/paper/ax.tar",
)


def tex_files() -> list[Path]:
    return sorted(ARTICLE_DIR.glob("*.tex"))


def strip_tex_commands(line: str) -> str:
    line = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", " ", line)
    line = re.sub(r"\$[^$]*\$", " ", line)
    return line


def collect_tex_inputs(main_tex: Path) -> list[str]:
    text = main_tex.read_text(encoding="utf-8")
    return re.findall(r"\\input\{([^}]+)\}", text)


def collect_includegraphics() -> list[str]:
    figures: list[str] = []
    for path in tex_files():
        text = path.read_text(encoding="utf-8")
        figures.extend(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text))
    return figures


def collect_citations() -> set[str]:
    citations: set[str] = set()
    cite_re = re.compile(r"\\cite(?:p|t|alp|alt)?(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}")
    for path in tex_files():
        for group in cite_re.findall(path.read_text(encoding="utf-8")):
            citations.update(key.strip() for key in group.split(",") if key.strip())
    return citations


def bib_keys() -> set[str]:
    bib = (ARTICLE_DIR / "ref.bib").read_text(encoding="utf-8")
    return set(re.findall(r"@\w+\{([^,]+),", bib))


def git_check_ignore(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode == 0


def audit_text() -> list[str]:
    issues: list[str] = []
    for path in tex_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for label, pattern in FORBIDDEN_TEXT_PATTERNS.items():
                if pattern.search(line):
                    issues.append(f"{path.relative_to(PROJECT_ROOT)}:{lineno}: {label}")
            stripped = strip_tex_commands(line)
            if ":" in stripped and not line.lstrip().startswith("%"):
                issues.append(f"{path.relative_to(PROJECT_ROOT)}:{lineno}: dois pontos em texto corrido")
    return issues


def audit_structure() -> list[str]:
    issues: list[str] = []
    main_tex = ARTICLE_DIR / "main.tex"
    if not main_tex.is_file():
        return ["docs/paper/article/main.tex ausente"]
    for name in collect_tex_inputs(main_tex):
        path = ARTICLE_DIR / f"{name}.tex"
        if not path.is_file():
            issues.append(f"input ausente: {path.relative_to(PROJECT_ROOT)}")
    for fig in collect_includegraphics():
        path = ARTICLE_DIR / fig
        if not path.is_file():
            issues.append(f"figura ausente: {path.relative_to(PROJECT_ROOT)}")
    missing_bib = collect_citations() - bib_keys()
    if missing_bib:
        issues.append(f"chaves BibTeX ausentes: {', '.join(sorted(missing_bib))}")
    return issues


def audit_git_policy() -> list[str]:
    issues: list[str] = []
    for sample in TRACKED_ARTICLE_SAMPLES:
        if git_check_ignore(sample):
            issues.append(f"deveria entrar no Git, mas esta ignorado: {sample}")
    for sample in IGNORED_SAMPLES:
        if not git_check_ignore(sample):
            issues.append(f"deveria permanecer ignorado: {sample}")
    for name in GENERATED_LATEX:
        path = ARTICLE_DIR / name
        if path.exists() and not git_check_ignore(str(path.relative_to(PROJECT_ROOT))):
            issues.append(f"artefato LaTeX gerado nao ignorado: {path.relative_to(PROJECT_ROOT)}")
    return issues


def audit_results_table() -> list[str]:
    metrics_path = PAPER_PROCESSED_DIR / "metrics_ablation.csv"
    results_path = ARTICLE_DIR / "results.tex"
    if not metrics_path.is_file() or not results_path.is_file():
        return []
    metrics = pd.read_csv(metrics_path)
    confusion_path = PAPER_PROCESSED_DIR / "confusion_matrices.csv"
    confusion = pd.read_csv(confusion_path) if confusion_path.is_file() else None
    table_text = re.sub(r"\s+", " ", results_path.read_text(encoding="utf-8"))
    detector_labels = {
        "svm_supervised": "SVM supervisionada",
        "one_class_svm": "One-Class SVM",
    }
    training_labels = {
        "svm_supervised": "normais + anômalos de DS1",
        "one_class_svm": "apenas normais de DS1",
    }
    issues: list[str] = []
    final_metrics = metrics[metrics["stage"] == "A3"]
    for row in final_metrics.itertuples(index=False):
        detector = detector_labels.get(str(row.detector), str(row.detector))
        training = training_labels.get(str(row.detector), "")
        expected = (
            f"{detector} & {training} & {int(row.n_features)} & "
            f"{row.pr_auc:.3f} & {row.roc_auc:.3f} & "
            f"{row.precision:.3f} & {row.recall:.3f} & {row.f1:.3f}"
        )
        if expected not in table_text:
            issues.append(f"linha de resultados ausente ou desatualizada: {expected}")
    if confusion is not None:
        final_confusion = confusion[confusion["stage"] == "A3"]
        for row in final_confusion.itertuples(index=False):
            detector = detector_labels.get(str(row.detector), str(row.detector))
            expected = (
                f"{detector} & {int(row.tn)} & {int(row.fp)} & "
                f"{int(row.fn)} & {int(row.tp)}"
            )
            if expected not in table_text:
                issues.append(f"linha de matriz de confusao ausente: {expected}")
    return issues


def main() -> int:
    checks = {
        "texto": audit_text(),
        "estrutura": audit_structure(),
        "git": audit_git_policy(),
        "resultados": audit_results_table(),
    }
    failed = False
    for name, issues in checks.items():
        if not issues:
            print(f"[ok] {name}")
            continue
        failed = True
        print(f"[falha] {name}")
        for issue in issues:
            print(f"  - {issue}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
