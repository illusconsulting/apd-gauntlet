"""resume-plan — which agent steps of a run are already complete (read-only).

A resumed run should not pay to redo agent work that already finished. ``resume-plan``
inspects a run directory and reports, for each *first-attempt* agent step, whether its
outputs are present and valid, so the runner can skip the complete ones. Retries, lens
re-runs and report remediations are deliberately absent from ``RESUMABLE_STEPS``: they
exist because an earlier attempt failed, so they must always run.

A step is complete when every file of ANY ONE of its output sets is present and valid.
A file is valid when it is non-empty, and, where the validator has a schema for it
(``validate.schema_for_run_file``), parses and passes that schema. A lens interrupted
between its two files (valid findings, missing or truncated capabilities) is therefore
not complete and re-runs.

Nothing here writes to the run directory.

Labels are the workflow's first-attempt ``llmStep`` labels (``.claude/workflows/apd-gauntlet.js``).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator

from . import FRAMEWORK_VERSION, __version__
from . import resources as _resources
from .plan_run import _TIERS
from .validate import parse_intake_brief, schema_errors_for_file

_CONTEXT_BRIEF = "00-context/context-brief.md"
_REASON_ERROR_LIMIT = 200  # keep a step's reason one short line; the receipt carries it


@dataclass(frozen=True)
class ResumeStep:
    """One resumable agent step.

    ``alternatives`` are run-relative output sets: the step is complete when every
    file of any one set is present and valid.
    """

    label: str
    alternatives: tuple[tuple[str, ...], ...]


# Workflow order. See the module docstring for why retries and re-runs are absent.
RESUMABLE_STEPS: tuple[ResumeStep, ...] = (
    ResumeStep("intake", (("00-context/context-brief.md", "00-context/asset-inventory.yaml"),)),
    ResumeStep("code-recon", (
        (
            "00-context/code-evidence-index.yaml",
            "00-context/code-architecture-brief.md",
            "00-context/c4-recon.yaml",
        ),
        ("00-context/code-recon-skipped.md",),
    )),
    ResumeStep("threat-model-author", ((
        "00-context/threat-model-normalized.yaml",
        "00-context/threat-model-authored.md",
    ),)),
    ResumeStep("tm-recon", (("00-context/threat-model-supplied-normalized.yaml",),)),
    *(
        ResumeStep(lens, ((f"{tier}/{lens}.findings.yaml", f"{tier}/{lens}.capabilities.yaml"),))
        for tier, lenses in _TIERS
        for lens in lenses
    ),
    ResumeStep("adjudicate", (("40-synthesis/cluster-decisions.yaml",),)),
    ResumeStep("tmeval", ((
        "40-synthesis/threat-model-coverage.yaml",
        "40-synthesis/threat-model-coverage-report.md",
    ),)),
    ResumeStep("apath", ((
        "40-synthesis/attack-path.findings.yaml",
        "40-synthesis/attack-path-report.md",
    ),)),
    ResumeStep("report-writer-attempt-0", ((
        "40-synthesis/report-data.yaml",
        "40-synthesis/advisory-report.md",
    ),)),
    ResumeStep("domain-auditor", (("40-synthesis/domain-improvements.yaml",),)),
)


class RunConfigError(Exception):
    """``.apd-run.yaml`` is missing, unparseable, or fails run-config.schema.json."""


class EngineMismatch(Exception):
    """The run was created by a different framework major than this engine."""


def load_run_config(run_dir: Path) -> dict[str, Any]:
    """Return the run's validated ``.apd-run.yaml``, or raise ``RunConfigError``."""
    config_path = run_dir / ".apd-run.yaml"
    if not config_path.is_file():
        raise RunConfigError(f"resume-plan: No .apd-run.yaml under {run_dir}")
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as e:
        raise RunConfigError(f"resume-plan: cannot parse {config_path}: {e}") from e
    validator = Draft202012Validator(_resources.read_schema("run-config.schema.json"))
    problems = [err.message for err in validator.iter_errors(cfg)]
    if problems:
        raise RunConfigError(
            f"resume-plan: {config_path} fails run-config validation: {'; '.join(problems)}"
        )
    return cast("dict[str, Any]", cfg)


def check_engine_compat(run_dir: Path) -> None:
    """Raise ``EngineMismatch`` when the run's framework major is not this engine's.

    Raises ``RunConfigError`` first when the run config itself is unusable. Runs from an
    older release on the same major are accepted.
    """
    framework_version = str(load_run_config(run_dir)["framework_version"])
    run_major = int(framework_version.split(".")[0])
    if run_major != int(FRAMEWORK_VERSION.split(".")[0]):
        raise EngineMismatch(
            f"resume-plan: refusing to resume {run_dir}: it was created by framework "
            f"{framework_version} and this engine is {__version__} "
            f"(framework {FRAMEWORK_VERSION}). Resume it with an apd-gauntlet "
            f"{run_major}.x engine."
        )


def _one_line(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) > _REASON_ERROR_LIMIT:
        return collapsed[: _REASON_ERROR_LIMIT - 3] + "..."
    return collapsed


def _has_frontmatter(brief: Path) -> bool:
    try:
        frontmatter = parse_intake_brief(brief)
    except yaml.YAMLError:
        return False
    return isinstance(frontmatter, dict) and bool(frontmatter)


def _file_problem(run_dir: Path, rel: str) -> str | None:
    """Why ``rel`` is not a finished output, or None when it is present and valid."""
    path = run_dir / rel
    if not path.is_file():
        return f"missing {rel}"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"unreadable {rel}: {_one_line(str(e))}"
    if not text.strip():
        return f"empty {rel}"
    if rel == _CONTEXT_BRIEF and not _has_frontmatter(path):
        return f"no frontmatter in {rel}"
    if rel.endswith(".yaml"):
        errors = schema_errors_for_file(run_dir, rel)
        if errors:
            kind = "unparseable" if errors[0].startswith("YAML parse error") else "schema-invalid"
            return f"{kind} {rel}: {_one_line(errors[0])}"
    return None


def _outputs_problem(run_dir: Path, outputs: tuple[str, ...]) -> str | None:
    for rel in outputs:
        problem = _file_problem(run_dir, rel)
        if problem is not None:
            return problem
    return None


def step_status(run_dir: Path, step: ResumeStep) -> tuple[bool, str]:
    """Return ``(complete, reason)`` for one step.

    The reason is ``outputs present and valid`` when complete; otherwise it is the
    first failing file of the step's first alternative.
    """
    first_problem: str | None = None
    for outputs in step.alternatives:
        problem = _outputs_problem(run_dir, outputs)
        if problem is None:
            return True, "outputs present and valid"
        if first_problem is None:
            first_problem = problem
    return False, first_problem or "no outputs defined"


def build_resume_plan(run_dir: Path) -> dict[str, Any]:
    """The R1 shape: ``{"engine_version": str, "steps": [{label, complete, reason}]}``."""
    steps = []
    for step in RESUMABLE_STEPS:
        complete, reason = step_status(run_dir, step)
        steps.append({"label": step.label, "complete": complete, "reason": reason})
    return {"engine_version": __version__, "steps": steps}
