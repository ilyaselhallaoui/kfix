# kfix Examples

This directory contains example Kubernetes manifests that demonstrate common issues that kfix can diagnose.

## Quick Test with Rancher Desktop

```bash
# Start Rancher Desktop and ensure Kubernetes is running

# Test ImagePullBackOff
kubectl apply -f broken-pod.yaml
sleep 10
kfix diagnose pod broken-app

# Test CrashLoopBackOff
kubectl apply -f crashloop-pod.yaml
sleep 20
kfix diagnose pod crashloop-app

# Test OOMKilled
kubectl apply -f oom-pod.yaml
sleep 30
kfix diagnose pod oom-app

# Test Deployment issues
kubectl apply -f broken-deployment.yaml
sleep 20
kfix diagnose deployment broken-deployment

# Test Service connectivity
kubectl apply -f broken-service.yaml
sleep 10
kfix diagnose service broken-service

# Clean up
kubectl delete -f broken-pod.yaml
kubectl delete -f crashloop-pod.yaml
kubectl delete -f oom-pod.yaml
kubectl delete -f broken-deployment.yaml
kubectl delete -f broken-service.yaml
```

## Example Files

### broken-pod.yaml
Demonstrates **ImagePullBackOff** error - pod tries to pull a non-existent image tag.

**Expected diagnosis:**
- Problem: Image pull failure
- Root cause: Invalid image tag
- Fix: Correct the image tag

### crashloop-pod.yaml
Demonstrates **CrashLoopBackOff** error - container exits immediately with error code.

**Expected diagnosis:**
- Problem: Container crash loop
- Root cause: Command exits with non-zero code
- Fix: Fix the container command/entrypoint

### oom-pod.yaml
Demonstrates **OOMKilled** error - container exceeds memory limit.

**Expected diagnosis:**
- Problem: Out of memory
- Root cause: Memory limit too low
- Fix: Increase memory limits

### broken-deployment.yaml
Demonstrates deployment rollout issues:
- Low memory limits causing startup failures
- Non-existent health check endpoint

**Expected diagnosis:**
- Problem: Rollout stuck
- Root cause: Resource constraints and failed probes
- Fix: Adjust resources and fix health check

### broken-service.yaml
Demonstrates service connectivity issues:
- Wrong service selector
- Mismatched target port

**Expected diagnosis:**
- Problem: No endpoints
- Root cause: Selector mismatch
- Fix: Correct service selector and ports

## Testing Workflow

1. **Apply the manifest**: `kubectl apply -f <file>`
2. **Wait for issue to appear**: Give Kubernetes time to detect the problem
3. **Diagnose with kfix**: `kfix diagnose <resource-type> <name>`
4. **Apply the fix**: Copy-paste the suggested kubectl commands
5. **Verify**: Check that the issue is resolved
6. **Clean up**: `kubectl delete -f <file>`

## Real-World Scenarios

These examples simulate real-world issues you might encounter:

- **ImagePullBackOff**: Typo in image tag, wrong registry, authentication issues
- **CrashLoopBackOff**: Application crashes, missing dependencies, configuration errors
- **OOMKilled**: Undersized memory limits, memory leaks
- **Deployment stuck**: Resource constraints, probe failures, image pull errors
- **Service no endpoints**: Selector mismatches, pod label errors

## Tips

- Use `kubectl get events --sort-by=.lastTimestamp` to see recent events
- Use `kubectl describe <resource>` to see detailed information
- Use `kubectl logs <pod>` to check application logs
- kfix combines all this information and provides AI-powered analysis

## Contributing

Have more example scenarios? Submit a pull request with additional manifests!
