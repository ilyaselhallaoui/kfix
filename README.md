# kfix

**AI-powered Kubernetes troubleshooter CLI** - Debug pods in 10 seconds instead of 10 minutes.

[![PyPI version](https://badge.fury.io/py/kfix.svg)](https://badge.fury.io/py/kfix)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is kfix?

kfix is a command-line tool that uses AI to diagnose and fix Kubernetes issues instantly. Instead of manually running `kubectl describe`, checking logs, and searching Stack Overflow, kfix does all that for you and provides:

- 🔍 **Instant diagnosis** of pod and node issues
- 🤖 **AI-powered analysis** using Claude (Anthropic)
- 📋 **Copy-paste ready** kubectl fix commands
- 📚 **Links to relevant** Kubernetes documentation
- ⚡ **Works with any** kubectl-configured cluster

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

### 2. Diagnose a pod

```bash
kfix diagnose pod my-app

# With namespace
kfix diagnose pod my-app -n production
```

### 3. Diagnose a node

```bash
kfix diagnose node worker-node-1
```

### 4. Explain an error

```bash
kfix explain "CrashLoopBackOff"
kfix explain "ImagePullBackOff"
```

## Usage Examples

### Pod in CrashLoopBackOff

```bash
$ kfix diagnose pod broken-app -n production

🔍 Diagnosing pod: broken-app (namespace: production)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Problem: ImagePullBackOff

The pod cannot pull the container image 'myapp:v1.2.3-typo'
because it doesn't exist in the registry.

🔧 Fix:
kubectl set image pod/broken-app app=myapp:v1.2.3 -n production

✅ Verification:
kubectl get pod broken-app -n production

📚 Documentation:
https://kubernetes.io/docs/concepts/containers/images/
```

### Node Issues

```bash
$ kfix diagnose node worker-1

🔍 Diagnosing node: worker-1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Status: DiskPressure

Node has insufficient disk space. Current usage: 95%

🔧 Fix:
# SSH into the node and clean up
kubectl drain worker-1 --ignore-daemonsets
ssh worker-1 'docker system prune -af'
kubectl uncordon worker-1

📚 Documentation:
https://kubernetes.io/docs/concepts/architecture/nodes/
```

## Features

- **Smart Diagnosis**: Analyzes pod status, events, logs, and more
- **Plain English**: No need to be a Kubernetes expert
- **Actionable Fixes**: Get exact commands to solve the issue
- **Fast**: 10 seconds instead of 15 minutes of debugging
- **Cluster Agnostic**: Works with any kubectl-configured cluster (EKS, GKE, AKS, k3s, etc.)

## Requirements

- Python 3.8+
- kubectl configured with cluster access
- Anthropic API key ([get one here](https://console.anthropic.com/))

## Commands

```bash
kfix diagnose pod <name> [-n namespace]    # Diagnose a pod
kfix diagnose node <name>                   # Diagnose a node
kfix explain "<error>"                      # Explain any K8s error
kfix config set api-key <key>               # Set API key
kfix version                                # Show version
```

## How It Works

1. kfix runs `kubectl` commands to gather pod/node information
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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/ilyaselhallaoui/kfix/issues)
- 📖 **Documentation**: See [TESTING.md](TESTING.md) for detailed usage

## Roadmap

- [ ] Support for deployments, services, and other resources
- [ ] Auto-fix mode (apply fixes automatically)
- [ ] History/logging of diagnoses
- [ ] Web dashboard
- [ ] Slack/Discord integration

---

**Made with ❤️ for DevOps engineers who are tired of debugging Kubernetes manually**
