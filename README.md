# kfix

AI-powered Kubernetes troubleshooter CLI.

## Installation

```bash
pip install kfix
```

## Quick Start

```bash
# Set your Anthropic API key
kfix config set api-key YOUR_API_KEY

# Diagnose a pod
kfix diagnose pod my-app

# Diagnose a node
kfix diagnose node node-1

# Explain an error
kfix explain "CrashLoopBackOff"
```

## Features

- 🔍 Smart diagnosis of pod and node issues
- 🤖 AI-powered analysis using Claude
- 📋 Copy-paste ready kubectl commands
- 📚 Links to relevant Kubernetes documentation
- ⚡ Works with any kubectl-configured cluster
