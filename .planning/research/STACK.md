# Technology Stack: Testing, Dependency Management & Refactoring

**Project:** TrendRadar Tech Debt Milestone
**Researched:** 2026-04-13
**Overall Confidence:** HIGH (versions verified against PyPI)

## Recommended Stack

### Testing Framework (Core)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | >=9.0,<10 | Test runner | Already in use (>=8.0). Upgrade to 9.x for improved assertion introspection, better parametrize performance, and Python 3.14 support. 9.0.3 is current stable. | HIGH |
| pytest-cov | >=7.0,<8 | Coverage reporting | Wraps coverage.py with pytest integration. 7.1.0 is current. Generates terminal, HTML, and XML reports. Integrates with `--cov-fail-under=80` for CI enforcement. | HIGH |
| coverage | >=7.13,<8 | Coverage engine | Transitive via pytest-cov. 7.13.5 is current. Supports Python 3.10-3.15. Branch coverage, context tracking, and JSON export. | HIGH |

### Mocking & Test Fixtures

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| unittest.mock | stdlib | General mocking | Already in use across 16 test files. No reason to switch -- it is the stdlib standard and avoids adding dependencies. pytest-mock (3.15.1) adds convenience (`mocker` fixture) but is not justified here because the codebase already has consistent `from unittest.mock import patch, MagicMock` patterns. Switching would create inconsistency for zero functional gain. | HIGH |
| responses | >=0.25,<1 | HTTP request mocking | Mocks the `requests` library specifically. TrendRadar uses `requests` for all crawlers. `responses` intercepts at the transport layer -- no test code changes needed. 0.26.0 is current stable. Preferred over `pytest-httpserver` (spins up real server, heavier) and `respx` (for httpx only, not requests). | HIGH |
| pytest-freezer | >=0.4.9,<1 | Time freezing | Tests for push window logic, rate limiter, and circuit breaker need deterministic time. Current tests patch `time.monotonic` manually -- fragile and verbose. pytest-freezer provides a `freezer` fixture. Lightweight (no heavy deps). 0.4.9 is current. | MEDIUM |

### Static Analysis & Formatting

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ruff | >=0.15,<1 | Linter + formatter | Replaces flake8, isort, black, pyflakes, and more in a single tool. 100x faster than alternatives (Rust-based). 0.15.10 is current. Configures entirely in pyproject.toml. No reason to use multiple slower tools. | HIGH |
| mypy | >=1.20,<2 | Type checking | 1.20.1 is current. The Pydantic models already exist; mypy catches type errors at the boundary between typed config and untyped dict usage. Essential for safe refactoring of the god object. Use `--strict` on new code, `--ignore-missing-imports` initially for legacy. | HIGH |

### Dependency Management

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| uv | >=0.11,<1 | Package/project manager | 10-100x faster than pip. Supports PEP 735 dependency-groups natively. Generates lockfiles for reproducible builds. Drop-in replacement for pip -- `uv pip install -r requirements.txt` works. 0.11.6 is current. | HIGH |
| pip-audit | >=2.10,<3 | Vulnerability scanning | Scans installed packages against known CVE databases. 2.10.0 is current. Run in CI to catch dependency vulnerabilities. | MEDIUM |

### CI Quality Gates

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pre-commit | >=4.5,<5 | Git hook manager | Runs ruff, mypy, and tests before commits. 4.5.1 is current. Prevents regressions from entering the codebase. | MEDIUM |

### Refactoring Support

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| dataclasses | stdlib | Data Transfer Objects | `@dataclass(frozen=True)` for inter-component contracts (CrawlOutput, AnalysisOutput). Already used throughout the codebase (`FetchedItem`, `CrawlResult`, `NewsData`, `RSSData`). Zero-dependency. Immutability prevents mutation bugs at component boundaries. | HIGH |

## What NOT to Use

| Tool | Why Not |
|------|---------|
| **pytest-mock** | The codebase already uses `unittest.mock` consistently across 16 test files. pytest-mock is a thin wrapper that adds a `mocker` fixture. Mixing two mock styles creates inconsistency. The stdlib mock is well-understood and sufficient. |
| **tox** | Overkill for a single-Python-version project. TrendRadar targets Python 3.10+ only. `uv run pytest` and CI matrix handle this. tox adds complexity without value here. |
| **nox** | Same reasoning as tox. Single target runtime. |
| **pytest-httpserver** | Spins up a real HTTP server for each test. Slower and heavier than `responses`. TrendRadar only uses `requests`, so `responses` is the exact right tool. |
| **respx** | For `httpx` mocking. TrendRadar uses `requests`, not `httpx`. Wrong tool. |
| **VCR.py / pytest-recording** | Records real HTTP responses to cassettes. Good for API integration tests but bad for this project: crawlers hit 20+ platforms that change constantly. Cassettes would be immediately stale. Mock at the transport layer instead. |
| **black + isort + flake8** | ruff replaces all three in one tool, runs 100x faster, and configures in one place (pyproject.toml). No reason to use three tools when one does it better. |
| **poetry** | TrendRadar already uses hatchling as its build backend with PEP 621 pyproject.toml. Switching build backends is high risk for zero gain. uv works with the existing pyproject.toml. |
| **factory_boy** | Useful for Django ORM model factories. TrendRadar uses SQLite directly (not ORM). Test data is simple dicts. factory_boy adds complexity without value. |
| **hypothesis** | Property-based testing library. Not justified for this milestone's scope (debt reduction, not new feature development). The test gaps are in basic coverage, not edge case exploration. |
| **pytest-xdist** | Parallel test execution. With ~16 test files and likely <200 tests after expansion, test suite will run in seconds. Parallelism adds complexity (test isolation issues) without meaningful speed benefit at this scale. Revisit if suite exceeds 500 tests. |
| **dependency_injector** | DI container library. Only ~5 services to wire. `AppContext` already acts as service locator. Adding a DI framework creates magic and learning curve for trivial wiring. Manual constructor injection is the right level of abstraction. |
| **Event bus / signal libraries** | Linear pipeline, single consumer per stage. Events add indirection with zero benefit for this architecture. |
| **Pydantic for DTOs** | Pydantic exists in the project but for config validation with complex validators. DTOs between pipeline stages are simple containers. `@dataclass(frozen=True)` is lighter, has no validation overhead, and is consistent with existing data models. |
| **rope** | Python refactoring library. Not needed for this decomposition since the changes are architectural (moving methods between classes), not mechanical (renaming across hundreds of files). | LOW |

## Dependency Actions

### Fix requirements.txt Drift

The `requirements.txt` is missing `structlog` and `pydantic` compared to `pyproject.toml`. Two options:

**Recommended: Delete requirements.txt entirely.** The project uses `pyproject.toml` with hatchling as the canonical dependency source. `requirements.txt` is a redundant second source of truth that will always drift. Users should install via `pip install .` or `uv pip install .` which reads pyproject.toml. For Docker, change `pip install -r requirements.txt` to `pip install .` in the Dockerfile.

If backwards compatibility with `requirements.txt` is mandatory (some users may rely on it), generate it from pyproject.toml:
```bash
uv pip compile pyproject.toml -o requirements.txt
```

### Unpin tenacity

Current: `tenacity==8.5.0` (exact pin)
Latest: `tenacity 9.1.4` (Feb 2026)

Change to: `tenacity>=9.0,<10` -- major version bump from 8 to 9 requires checking the changelog, but 9.x has been stable since late 2024. The exact pin at 8.5.0 prevents receiving bug fixes and can cause resolution conflicts with other packages.

### Make boto3 Optional

Current: `boto3>=1.35.0,<2.0.0` in core dependencies (always installed)
boto3 pulls in botocore (~100MB). Most users do not use S3 storage.

Move to optional dependency:
```toml
[project.optional-dependencies]
s3 = ["boto3>=1.35.0,<2.0.0"]
```

Guard imports in code:
```python
try:
    import boto3
except ImportError:
    boto3 = None
```

## Updated pyproject.toml Configuration

```toml
[project]
name = "trendradar"
version = "5.5.3"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.32.5,<3",
    "pytz>=2025.2,<2026",
    "PyYAML>=6.0.3,<7",
    "fastmcp>=2.14,<3",
    "websockets>=15.0.1,<16",
    "feedparser>=6.0,<7",
    "litellm>=1.57,<2",
    "tenacity>=9.0,<10",
    "flask>=3.0,<4",
    "mcp>=1.23,<2",
    "structlog>=24.0,<26",
    "pydantic>=2.0,<3",
]

[project.optional-dependencies]
s3 = ["boto3>=1.35,<2"]

[dependency-groups]
dev = [
    "pytest>=9.0,<10",
    "pytest-cov>=7.0,<8",
    "responses>=0.25,<1",
    "pytest-freezer>=0.4.9,<1",
    "mypy>=1.20,<2",
    "ruff>=0.15,<1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = [".git", ".venv", "output", "_image"]
addopts = [
    "--cov=trendradar",
    "--cov=mcp_server",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=80",
    "-v",
]

[tool.coverage.run]
branch = true
source = ["trendradar", "mcp_server"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
show_missing = true

[tool.ruff]
target-version = "py310"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

## Installation Commands

```bash
# Install uv (if not present)
pip install uv

# Install project with dev dependencies
uv sync --group dev

# Or with pip (no uv)
pip install -e ".[s3]"
pip install pytest>=9.0 pytest-cov>=7.0 responses>=0.25 pytest-freezer>=0.4.9 mypy>=1.20 ruff>=0.15

# Run tests with coverage
pytest

# Run linter
ruff check .

# Run formatter
ruff format .

# Run type checker
mypy trendradar/ mcp_server/

# Run vulnerability scan
pip-audit
```

## Sources

- pytest 9.0.3: https://pypi.org/project/pytest/ (verified 2026-04-13)
- pytest-cov 7.1.0: https://pypi.org/project/pytest-cov/ (verified 2026-04-13)
- coverage 7.13.5: https://pypi.org/project/coverage/ (verified 2026-04-13)
- responses 0.26.0: https://pypi.org/project/responses/ (verified 2026-04-13)
- pytest-freezer 0.4.9: https://pypi.org/project/pytest-freezer/ (verified 2026-04-13)
- ruff 0.15.10: https://pypi.org/project/ruff/ (verified 2026-04-13)
- mypy 1.20.1: https://pypi.org/project/mypy/ (verified 2026-04-13)
- uv 0.11.6: https://pypi.org/project/uv/ (verified 2026-04-13)
- tenacity 9.1.4: https://pypi.org/project/tenacity/ (verified 2026-04-13)
- pip-audit 2.10.0: https://pypi.org/project/pip-audit/ (verified 2026-04-13)
- pre-commit 4.5.1: https://pypi.org/project/pre-commit/ (verified 2026-04-13)
- pytest-mock 3.15.1: https://pypi.org/project/pytest-mock/ (verified 2026-04-13)
- uv dependency-groups docs: https://docs.astral.sh/uv/concepts/projects/dependencies/
