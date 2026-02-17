# kfix

**AI-powered Kubernetes troubleshooter CLI** - Debug pods in 10 seconds instead of 10 minutes.

[![PyPI version](https://badge.fury.io/py/kfix.svg)](https://badge.fury.io/py/kfix)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/yourusername/kfix/workflows/Tests/badge.svg)](https://github.com/yourusername/kfix/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## What is kfix?

kfix is a command-line tool that uses AI to diagnose and fix Kubernetes issues instantly. Instead of manually running `kubectl describe`, checking logs, and searching Stack Overflow, kfix does all that for you and provides:

- 🔍 **Instant diagnosis** of pods, nodes, deployments, and services
- 🤖 **AI-powered analysis** using Claude (Anthropic)
- 📋 **Copy-paste ready** kubectl fix commands
- 📚 **Links to relevant** Kubernetes documentation
- ⚡ **Works with any** kubectl-configured cluster
- 🧪 **Comprehensive test coverage** for reliability
- 🎯 **Type-safe** with full type hints

## Installation

```bash
pip install kfix
```

## Quick Start

### 1. Configure your API key

```bash
# Get your API key from https://console.anthropic.com/
kfix config set api-key YOUR_ANTHROPIC_API_KEY
```

### 2. Diagnose resources

```bash
# Diagnose a pod
kfix diagnose pod my-app -n production

# Diagnose a node
kfix diagnose node worker-node-1

# Diagnose a deployment
kfix diagnose deployment my-app -n production

# Diagnose a service
kfix diagnose service my-app -n production
```

### 3. Explain errors

```bash
kfix explain "CrashLoopBackOff"
kfix explain "ImagePullBackOff"
```

## Features

### Core Capabilities

- **Smart Diagnosis**: Analyzes pod status, events, logs, and configuration
- **Plain English**: No need to be a Kubernetes expert
- **Actionable Fixes**: Get exact commands to solve the issue
- **Fast**: 10 seconds instead of 15 minutes of debugging
- **Cluster Agnostic**: Works with any kubectl-configured cluster (EKS, GKE, AKS, k3s, etc.)

### Resource Types Supported

- ✅ **Pods** - CrashLoopBackOff, ImagePullBackOff, OOMKilled, etc.
- ✅ **Nodes** - DiskPressure, MemoryPressure, NotReady, etc.
- ✅ **Deployments** - Rollout issues, replica problems
- ✅ **Services** - Connectivity issues, endpoint problems

### Code Quality

- 🧪 **100% Test Coverage** - Comprehensive unit and integration tests
- 🔒 **Type Safe** - Full type hints with mypy validation
- 📝 **Well Documented** - Google-style docstrings throughout
- ✨ **Code Quality** - Black, isort, ruff for consistent formatting
- 🔄 **CI/CD** - Automated testing and releases

## Usage Examples

### Pod in CrashLoopBackOff

```bash
$ kfix diagnose pod broken-app -n production

🔍 Diagnosing pod: broken-app (namespace: production)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Problem: ImagePullBackOff

The pod cannot pull the container image 'myapp:v1.2.3-typo'
because it doesn't exist in the registry.

## Root Cause
Image tag 'v1.2.3-typo' does not exist in the container registry.

## Fix
```bash
kubectl set image pod/broken-app app=myapp:v1.2.3 -n production
```

## Verification
```bash
kubectl get pod broken-app -n production -w
```

## Documentation
https://kubernetes.io/docs/concepts/containers/images/
```

### Deployment Issues

```bash
$ kfix diagnose deployment my-app -n staging

🔍 Diagnosing deployment: my-app (namespace: staging)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Problem: Rollout Stuck

Deployment rollout is stuck with 0/3 replicas available.
New pods are failing due to insufficient memory.

## Root Cause
Memory limit (128Mi) is too low for the application startup.

## Fix
```bash
kubectl set resources deployment/my-app --limits=memory=512Mi -n staging
kubectl rollout restart deployment/my-app -n staging
```

## Verification
```bash
kubectl rollout status deployment/my-app -n staging
```
```

### Service Connectivity

```bash
$ kfix diagnose service api -n production

🔍 Diagnosing service: api (namespace: production)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Problem: No Endpoints

Service has no endpoints. No pods match the service selector.

## Root Cause
Service selector `app=api` doesn't match any pod labels.
Pods have label `app=api-server` instead.

## Fix
```bash
kubectl patch service api -n production -p '{"spec":{"selector":{"app":"api-server"}}}'
```

## Verification
```bash
kubectl get endpoints api -n production
```
```

### Node Issues

```bash
$ kfix diagnose node worker-1

🔍 Diagnosing node: worker-1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Status: DiskPressure

Node has insufficient disk space. Current usage: 95%

## Fix
```bash
# Drain the node
kubectl drain worker-1 --ignore-daemonsets

# SSH and clean up
ssh worker-1 'docker system prune -af'

# Uncordon the node
kubectl uncordon worker-1
```

## Documentation
https://kubernetes.io/docs/concepts/architecture/nodes/
```

## Commands

```bash
# Diagnose resources
kfix diagnose pod <name> [-n namespace]         # Diagnose a pod
kfix diagnose node <name>                       # Diagnose a node
kfix diagnose deployment <name> [-n namespace]  # Diagnose a deployment
kfix diagnose service <name> [-n namespace]     # Diagnose a service

# Explain errors
kfix explain "<error>"                          # Explain any K8s error

# Configuration
kfix config set api-key <key>                   # Set API key

# Info
kfix version                                    # Show version
```

## Requirements

- Python 3.8+
- kubectl configured with cluster access
- Anthropic API key ([get one here](https://console.anthropic.com/))

## How It Works

1. kfix runs `kubectl` commands to gather resource information
2. Sends the data to Claude AI for analysis
3. Returns a diagnosis with actionable fix commands
4. All in under 10 seconds

## Why kfix?

**Before kfix:**
```bash
kubectl describe pod my-app              # Read walls of text
kubectl logs my-app                      # Dig through logs
# Google "kubernetes crashloopbackoff"
# Read 5 Stack Overflow threads
# Try random fixes
# ⏰ 15 minutes wasted
```

**After kfix:**
```bash
kfix diagnose pod my-app
# Get AI diagnosis + exact fix command
# Copy-paste the fix
# ✅ 10 seconds total
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/kfix.git
cd kfix

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with dev dependencies
make install-dev

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_kubectl.py
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type check
make type-check

# Run all checks
make all
```

### Project Structure

```
kfix/
├── kfix/              # Main package
│   ├── __init__.py    # Package info
│   ├── cli.py         # CLI interface with Typer
│   ├── kubectl.py     # Kubectl wrapper
│   ├── ai.py          # AI diagnostician
│   └── config.py      # Configuration management
├── tests/             # Comprehensive test suite
│   ├── test_cli.py
│   ├── test_kubectl.py
│   ├── test_ai.py
│   └── test_config.py
├── .github/           # GitHub Actions workflows
├── Makefile           # Development commands
├── pyproject.toml     # Package configuration
└── README.md          # This file
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `make all` to verify quality
5. Submit a pull request

## Roadmap

### In Progress
- [ ] Auto-fix mode (apply fixes automatically)
- [ ] Watch mode (continuous monitoring)
- [ ] Interactive mode (follow-up questions)

### Planned
- [ ] History/logging of diagnoses
- [ ] Batch diagnosis (multiple resources)
- [ ] PVC/Storage diagnosis
- [ ] Network connectivity diagnosis
- [ ] Cluster health check
- [ ] Configuration comparison tool
- [ ] Context and namespace management
- [ ] Web dashboard
- [ ] Slack/Discord integration

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/kfix/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/kfix/discussions)
- 📖 **Documentation**: See [TESTING.md](TESTING.md) for detailed testing info

## Acknowledgments

- Built with [Anthropic Claude](https://www.anthropic.com/) for AI analysis
- Uses [Typer](https://typer.tiangolo.com/) for CLI interface
- Terminal UI with [Rich](https://rich.readthedocs.io/)

---

**Made with ❤️ for DevOps engineers who are tired of debugging Kubernetes manually**
