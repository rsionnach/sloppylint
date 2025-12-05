<!-- TODO: Add CLI demo GIF here -->

<div align="center">
  <h1>🐷 Sloppy</h1>
  <p><strong>Detect AI-generated code anti-patterns in your Python codebase.</strong></p>
</div>

[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge)](https://github.com/rsionnach/sloppy)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

## ⚡ Quick Start

```bash
# Install from GitHub
pip install git+https://github.com/rsionnach/sloppy.git

# Or clone and install locally
git clone https://github.com/rsionnach/sloppy.git
cd sloppy
pip install -e .

# Run it
sloppy .

# Output:
# CRITICAL (2 issues)
# ============================================================
#   src/api.py:23  mutable_default_arg
#     Mutable default argument - use None instead
#     > def process(items=[]):
#
#   src/db.py:15  bare_except
#     Bare except catches everything including SystemExit
#     > except:
#
# SLOPPY INDEX
# ══════════════════════════════════════════════════
# Information Utility (Noise)    : 24 pts
# Information Quality (Lies)     : 105 pts
# Style / Taste (Soul)           : 31 pts
# Structural Issues              : 45 pts
# ──────────────────────────────────────────────────
# TOTAL SLOP SCORE               : 205 pts
#
# Verdict: SLOPPY
```

---

## 🎯 What It Catches

### The Three Axes of AI Slop

| Axis | What It Detects | Examples |
|------|-----------------|----------|
| 📢 **Noise** | Debug artifacts, redundant comments | `print()`, `# increment x` above `x += 1` |
| 🤥 **Lies** | Hallucinations, placeholders | `def process(): pass`, mutable defaults |
| 💀 **Soul** | Over-engineering, bad style | God functions, deep nesting, hedging comments |
| 🏗️ **Structure** | Anti-patterns | Bare except, star imports, single-method classes |

---

## 📥 What You Put In

```bash
# Scan a directory
sloppy src/

# Scan specific files
sloppy app.py utils.py

# Only high severity issues
sloppy --severity high

# CI mode - exit 1 if issues found
sloppy --ci --max-score 50

# Export JSON report
sloppy --output report.json
```

---

## 📤 What You Get Out

| Output | Description |
|--------|-------------|
| 🎯 **Issues by Severity** | Critical, High, Medium, Low |
| 📊 **Slop Score** | Points breakdown by axis |
| 📋 **Verdict** | CLEAN / ACCEPTABLE / SLOPPY / DISASTER |
| 📁 **JSON Report** | Machine-readable for CI/CD |

---

## 🔍 Pattern Examples

### Critical Severity

```python
# 🚨 mutable_default_arg - AI's favorite mistake
def process_items(items=[]):  # Bug: shared state between calls
    items.append(1)
    return items

# ✅ Fix: Use None and initialize inside
def process_items(items=None):
    if items is None:
        items = []
    items.append(1)
    return items
```

```python
# 🚨 bare_except - Catches SystemExit, KeyboardInterrupt
try:
    risky_operation()
except:  # Bug: swallows Ctrl+C!
    pass

# ✅ Fix: Catch specific exceptions
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
```

### High Severity

```python
# 🚨 pass_placeholder - AI gave up
def validate_email(email):
    pass  # TODO: implement

# 🚨 hedging_comment - AI uncertainty
x = calculate()  # should work hopefully
```

---

## 💰 The Value

<div align="center">
  <h3>🔍 Catch AI mistakes before they hit production</h3>
</div>

### Why This Matters

| Problem | Impact | Sloppy Catches |
|---------|--------|----------------|
| Mutable defaults | Shared state bugs | ✅ Critical alert |
| Bare except | Swallows Ctrl+C | ✅ Critical alert |
| Placeholder functions | Runtime failures | ✅ High alert |
| Hallucinated imports | ImportError in prod | ✅ High alert |
| JavaScript patterns | `.push()`, `.length` errors | ✅ High alert |
| Unused imports | Code bloat | ✅ Medium alert |
| Dead code | Maintenance burden | ✅ Medium alert |
| Copy-paste code | Maintenance nightmare | ✅ Medium alert |

### Research Says

- **40%+ of AI-generated code** contains security vulnerabilities
- **20% of AI package imports** reference non-existent libraries
- **66% of developers** say AI code is "almost right" (the dangerous kind)

---

## 🛠️ CLI Commands

```bash
sloppy .                    # 🔍 Scan current directory
sloppy src/ tests/          # 📁 Scan multiple directories
sloppy --severity high      # ⚡ Only critical/high issues
sloppy --lenient            # 🎯 Same as --severity high
sloppy --strict             # 🔬 Report everything
sloppy --ci                 # 🚦 Exit 1 if any issues
sloppy --max-score 50       # 📊 Exit 1 if score > 50
sloppy --output report.json # 📋 Export JSON report
sloppy --ignore "tests/*"   # 🚫 Exclude patterns
sloppy --disable magic_number # ⏭️ Skip specific checks
sloppy --version            # 📌 Show version
```

---

## ✅ Features

| Feature | Description | Status |
|---------|-------------|--------|
| 🔍 **Hallucinated Imports** | Detect non-existent packages (40+ patterns) | ✅ Done |
| 🎭 **Hallucinated Methods** | Detect JS patterns like `.push()`, `.length` | ✅ Done |
| 📦 **Unused Imports** | AST-based detection | ✅ Done |
| 💀 **Dead Code** | Unused functions/classes | ✅ Done |
| 🔄 **Duplicate Detection** | Cross-file copy-paste | ✅ Done |
| 🎨 **Rich Output** | Colors and tables (optional) | ✅ Done |
| ⚙️ **Config Support** | pyproject.toml configuration | ✅ Done |

---

## 📦 Installation

```bash
# Install from GitHub
pip install git+https://github.com/rsionnach/sloppy.git

# With colored output (recommended)
pip install "sloppy[rich] @ git+https://github.com/rsionnach/sloppy.git"

# With all optional features
pip install "sloppy[all] @ git+https://github.com/rsionnach/sloppy.git"

# Or clone and install for development
git clone https://github.com/rsionnach/sloppy.git
cd sloppy
pip install -e ".[dev]"

# Verify
sloppy --version
```

---

## ⚙️ Configuration

Configure via `pyproject.toml`:

```toml
[tool.sloppy]
ignore = ["tests/*", "migrations/*"]
disable = ["magic_number", "debug_print"]
severity = "medium"
max-score = 100
ci = false
format = "detailed"  # or "compact" or "json"
```

---

## 🤝 Contributing

```bash
git clone https://github.com/rsionnach/sloppy.git
cd sloppy
pip install -e ".[dev]"
pytest tests/ -v  # 57 tests should pass
```

See [AGENTS.md](AGENTS.md) for coding conventions and pattern implementation guide.

---

## 📄 License

MIT

---

## 🙏 Acknowledgments

### Inspiration
- [KarpeSlop](https://github.com/CodeDeficient/KarpeSlop) - The original AI Slop Linter for TypeScript
- Andrej Karpathy's commentary on AI-generated code quality

### Research
- [Counterfeit Code](https://counterfeit-code.github.io/) - MIT research on "looks right but doesn't work" patterns
- [Package Hallucinations](https://arxiv.org/abs/2406.10279) - USENIX study on hallucinated dependencies
