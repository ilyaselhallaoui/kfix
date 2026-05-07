> **Note:** kfix was a vibe-coded experiment and is no longer actively maintained. Feel free to fork it or use it as-is.

# kfix

**AI-powered Kubernetes troubleshooter CLI** — From `kubectl` noise to a clear fix in seconds.

[![PyPI version](https://badge.fury.io/py/kfix.svg)](https://badge.fury.io/py/kfix)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/ilyaselhallaoui/kfix/workflows/Tests/badge.svg)](https://github.com/ilyaselhallaoui/kfix/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## What is kfix?

kfix is a command-line tool that uses AI to diagnose and fix Kubernetes issues instantly. Instead of manually running `kubectl describe`, digging through logs, and searching Stack Overflow, kfix does all of that and returns an actionable fix in under 10 seconds.

<!-- Demo: replace this comment with an asciinema/GIF of `kfix diagnose pod` -->
<!-- ![kfix demo](docs/demo.gif) -->

- **Instant diagnosis** of pods, nodes, deployments, and services
- **AI-powered analysis** using Anthropic Claude
- **Copy-paste ready** kubectl fix commands
- **Cluster scanner** — find every unhealthy resource at once
- **Continuous watch** — alert on new issues as they appear
- **Diagnosis history** — every run is saved locally
- **Works with any** kubectl-configured cluster (EKS, GKE, AKS, k3s, Rancher, ...)

## Installation

```bash
pip install kfix
```

On first run kfix will interactively guide you through API key setup — no manual config step needed.

## Quick Start

```bash
# Diagnose a failing pod
kfix diagnose pod my-app -n production

# Scan all namespaces for unhealthy resources
kfix scan --all-namespaces

# Watch the cluster continuously (Ctrl+C to stop)
kfix watch --all-namespaces --interval 30

# Explain any Kubernetes error in plain English
kfix explain "OOMKilled"

# Review recent diagnoses
kfix history
```

## Commands

### `kfix diagnose`

```bash
kfix diagnose pod <name>        [-n ns] [--context ctx] [--model haiku|sonnet|opus]
kfix diagnose node <name>               [--context ctx]
kfix diagnose deployment <name> [-n ns] [--context ctx]
kfix diagnose service <name>    [-n ns] [--context ctx]
kfix diagnose pvc <name>        [-n ns] [--context ctx]

# Auto-apply safe fixes without prompting
kfix diagnose pod my-app -n prod --auto-fix --auto-fix-policy safe

# Output as JSON (great for CI pipelines)
kfix diagnose pod my-app -o json | jq .diagnosis
```

### `kfix scan`

```bash
kfix scan                        # Scan default namespace
kfix scan -n production          # Scan a specific namespace
kfix scan --all-namespaces       # Scan everything (-A also works)
kfix scan --context my-cluster   # Scan a specific cluster
```

Finds all unhealthy pods, deployments, services, and nodes, then diagnoses each one with AI.

### `kfix watch`

```bash
kfix watch                        # Watch default namespace every 30s
kfix watch -A --interval 60       # Watch all namespaces every 60s
kfix watch -n production          # Watch a specific namespace
```

Continuously polls the cluster. Highlights new issues and suggests the exact `kfix diagnose` command to run.

### `kfix history`

```bash
kfix history           # List last 20 diagnoses
kfix history -n 50     # List last 50
kfix history clear     # Delete all history
```

Every `kfix diagnose` run is automatically saved to `~/.kfix/history.jsonl`.

### `kfix explain`

```bash
kfix explain "CrashLoopBackOff"
kfix explain "ImagePullBackOff"
kfix explain "OOMKilled: container exceeded memory limit"
```

### `kfix config`

```bash
kfix config show                          # Show current configuration
kfix config set api-key sk-ant-api03-...  # Set API key
```

Or set the environment variable: `export ANTHROPIC_API_KEY=sk-ant-...`

## Shell Completions

kfix supports tab completion for all shells out of the box:

```bash
# Install completion (run once)
kfix --install-completion

# Or view the completion script
kfix --show-completion
```

After running `--install-completion`, restart your shell and `kfix <TAB>` will complete commands, flags, and arguments.

## Requirements

- Python 3.8+
- `kubectl` installed and configured with cluster access
- Anthropic API key ([get one free at console.anthropic.com](https://console.anthropic.com/))

## Why kfix?

**Before kfix:**
```bash
kubectl describe pod my-app     # Wall of text
kubectl logs my-app             # Dig through logs
# Google the error, read 5 threads...
# ⏰ 15+ minutes later, maybe fixed
```

**After kfix:**
```bash
kfix diagnose pod my-app
# ✅ Root cause + copy-paste fix in 10 seconds
```

## kfix vs k8sgpt

[k8sgpt](https://k8sgpt.ai) is the closest neighbour in this space and a great project. They solve overlapping problems but make different trade-offs:

| | kfix | k8sgpt |
|---|---|---|
| Shape | Single-binary CLI | CLI + in-cluster operator + CRDs |
| Setup | `pip install kfix` and an API key | CLI install, or operator + CRDs in-cluster |
| Output | Streaming Markdown with copy-paste `kubectl` fixes | Structured analysis, multiple output formats |
| Auto-fix | Built-in with `safe`/`review`/`off` policy | Out of scope |
| LLM backends | Anthropic Claude (today) | Many (OpenAI, Anthropic, Azure, local, ...) |

If you want a continuously-running operator that emits findings into your cluster: use k8sgpt. If you want a fast, local CLI that turns a pager into a fix in one command: use kfix.

## Development

```bash
git clone https://github.com/ilyaselhallaoui/kfix.git
cd kfix
make install-dev      # Install with dev dependencies
make test             # Run all tests
make all              # format + lint + type-check + test
```

## Roadmap

- [x] Auto-fix mode (`--auto-fix`)
- [x] Cluster scan (`kfix scan`)
- [x] Multi-cluster support (`--context`)
- [x] Continuous watch (`kfix watch`)
- [x] Diagnosis history (`kfix history`)
- [x] PVC / storage diagnosis (`kfix diagnose pvc`, PVCs in `kfix scan`)
- [ ] Network connectivity diagnosis
- [ ] `kfix watch` Slack notifications

## Data & Privacy

kfix sends Kubernetes diagnostic context to the Anthropic API to generate analysis. Do not include secrets in pod metadata or logs before running a diagnosis. API keys are stored locally at `~/.kfix/config.yaml` with restrictive file permissions.

## License

MIT — see [LICENSE](LICENSE).

---

**Built for on-call engineers who need speed and clarity, not more noise.**
