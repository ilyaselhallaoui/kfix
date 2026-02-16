# kfix Cheat Sheet

## 🚀 Quick Start

```bash
# Activate environment
source venv/bin/activate

# Or use wrapper (no activation needed)
./kfix.sh <command>
```

---

## 📋 Commands

### Diagnose Pod Issues
```bash
# Diagnose a specific pod
kfix diagnose pod <POD-NAME>

# Diagnose pod in specific namespace
kfix diagnose pod <POD-NAME> -n <NAMESPACE>

# Examples
kfix diagnose pod my-app -n production
kfix diagnose pod nginx-xyz -n default
```

**Use when:**
- Pod is CrashLoopBackOff
- Pod is ImagePullBackOff
- Pod is Pending
- Pod is Error
- Pod keeps restarting
- Pod logs show errors

---

### Diagnose Node Issues
```bash
# Diagnose a node
kfix diagnose node <NODE-NAME>

# Example
kfix diagnose node worker-node-1
```

**Use when:**
- Node is NotReady
- Node has disk pressure
- Node has memory pressure
- Pods not scheduling

---

### Explain Errors
```bash
# Explain any K8s error
kfix explain "<ERROR-MESSAGE>"

# Examples
kfix explain "CrashLoopBackOff"
kfix explain "OOMKilled"
kfix explain "ImagePullBackOff"
kfix explain "Pending"
kfix explain "ErrImagePull"
kfix explain "Evicted"
```

**Use when:**
- You see an unfamiliar error
- You want quick explanation
- You need fix suggestions

---

## 🔧 Configuration

```bash
# Set API key (one-time setup)
kfix config set api-key YOUR_API_KEY

# Check version
kfix version

# Get help
kfix --help
kfix diagnose --help
```

---

## 💡 Common Workflows

### 1. Pod Won't Start
```bash
kubectl get pods              # See the issue
kfix diagnose pod my-app      # Get AI diagnosis + fix
# Copy-paste the fix command
```

### 2. Understanding Errors
```bash
# See error in kubectl output
kfix explain "the error message"
# Get plain English explanation
```

### 3. Node Problems
```bash
kubectl get nodes             # See node status
kfix diagnose node node-1     # Get detailed analysis
```

### 4. Quick Triage
```bash
# Check all problem pods
kubectl get pods -A | grep -v Running

# Diagnose each one
kfix diagnose pod <name> -n <namespace>
```

---

## 🎯 Pro Tips

1. **Always specify namespace** with `-n` flag if not using default
2. **Copy-paste fixes directly** - kfix gives you exact commands
3. **Use explain for quick answers** - faster than searching docs
4. **Check documentation links** - kfix provides relevant K8s docs
5. **Works on healthy pods too** - validates configuration

---

## 📊 What You Get

Every diagnosis includes:
- ✅ Clear problem description
- ✅ Root cause analysis
- ✅ Copy-paste kubectl fix commands
- ✅ Verification steps
- ✅ Links to K8s documentation
- ✅ Under 300 words (quick to read)

---

## 🆘 Troubleshooting kfix

```bash
# Check if cluster is accessible
kubectl cluster-info

# Check if API key is set
cat ~/.kfix/config.yaml

# Test basic functionality
kfix version

# Run with full path (if command not found)
./kfix.sh version
```

---

## 📝 Real Examples from Your Cluster

```bash
# Your CoreDNS has 34 restarts - diagnose it
kfix diagnose pod coredns-64fd4b4794-kvr5n -n kube-system

# Check your node health
kfix diagnose node ilyaslaptop

# Understand common errors
kfix explain "CrashLoopBackOff"
```

---

## 🔗 Quick Reference

| Task | Command |
|------|---------|
| Pod not running | `kfix diagnose pod <name> -n <ns>` |
| Node issues | `kfix diagnose node <name>` |
| Explain error | `kfix explain "<error>"` |
| Set API key | `kfix config set api-key <key>` |
| Check version | `kfix version` |
| Get help | `kfix --help` |

---

**Save time:** Instead of 15 minutes debugging, get AI-powered diagnosis in 10 seconds! 🚀
