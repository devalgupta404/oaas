# Production Server Hot Fix Log - December 8, 2025

## Summary
Fixed MLIR string encryption and OLLVM obfuscation passes on production server by deploying LLVM 22 binaries with all target architectures.

## Server Details
- **Production Server**: `root@69.62.77.147`
- **Build VM**: `devalgupta4@34.100.133.67` (IP changed from 34.93.196.34)
- **Container**: `llvm-obfuscator-backend`
- **Docker Image**: `akashsingh04/llvm-obfuscator-backend:patched`

---

## Issue 1: MLIR String Encryption Plugin Not Loading

### Problem
```
Failed to load passes from '/usr/local/llvm-obfuscator/lib/MLIRObfuscation.so'. Request ignored.
<unknown>:0: error: 'string-encrypt' does not refer to a registered pass or pass pipeline
```

### Root Cause
- Production had statically-linked `mlir-opt` (258MB) which cannot load dynamic plugins
- `MLIRObfuscation.so` (1.1MB) was dynamically linked and required `libMLIR.so` and `libLLVM.so`

### Fix Attempt 1: Deploy shared libraries
```bash
# Check binary on server
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend ls -la /usr/local/llvm-obfuscator/lib/MLIRObfuscation.so && docker exec llvm-obfuscator-backend md5sum /usr/local/llvm-obfuscator/lib/MLIRObfuscation.so"

# Output:
# -rwxr-xr-x 1 root root 1086464 Dec  8 12:33 /usr/local/llvm-obfuscator/lib/MLIRObfuscation.so
# 0fa43db9da9eff47bc1e3467e6b74742  /usr/local/llvm-obfuscator/lib/MLIRObfuscation.so

# Copy libMLIR.so to server
scp /tmp/llvm-bins/libMLIR.so.22.0git root@69.62.77.147:/tmp/

# Deploy to container
ssh root@69.62.77.147 "docker cp /tmp/libMLIR.so.22.0git llvm-obfuscator-backend:/usr/local/llvm-obfuscator/lib/libMLIR.so.22.0git && docker exec llvm-obfuscator-backend chmod +x /usr/local/llvm-obfuscator/lib/libMLIR.so.22.0git && docker restart llvm-obfuscator-backend"

# Output: llvm-obfuscator-backend
```

---

## Issue 2: Clang Binary Broken (Dynamic Linking Errors)

### Problem
```
clang: symbol lookup error: clang: undefined symbol: LLVMInitializeAArch64TargetInfo, version LLVM_22.0
```

### Root Cause
- The `clang` binary (107MB) was dynamically linked
- Required `libLLVM.so` with **all targets** including AArch64
- The deployed `libLLVM.so` was built with only X86 target

### Discovery
```bash
# Check clang binary type
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend ldd /usr/local/llvm-obfuscator/bin/clang.real | head -10"

# Output:
# linux-vdso.so.1 (0x0000744cb3d55000)
# libLLVM.so.22.0git => /usr/local/llvm-obfuscator/lib/libLLVM.so.22.0git (0x0000744caaa26000)
# libstdc++.so.6 => /lib/x86_64-linux-gnu/libstdc++.so.6 (0x0000744caa7bc000)
# ...
```

### Fix Attempt 1: Replace with system clang
```bash
# Test system clang
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend /usr/bin/clang --version 2>&1 | head -5"

# Output:
# Debian clang version 19.1.7 (3+b1)
# Target: x86_64-pc-linux-gnu
# Thread model: posix
# InstalledDir: /usr/lib/llvm-19/bin

# Replace broken clang with system clang
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend bash -c 'mv /usr/local/llvm-obfuscator/bin/clang.real /usr/local/llvm-obfuscator/bin/clang.real.broken && ln -sf /usr/bin/clang /usr/local/llvm-obfuscator/bin/clang.real'"

# Output: Replaced broken clang with working one

# Also replace opt
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend bash -c 'mv /usr/local/llvm-obfuscator/bin/opt /usr/local/llvm-obfuscator/bin/opt.broken && ln -sf /usr/bin/opt /usr/local/llvm-obfuscator/bin/opt && /usr/bin/opt --version 2>&1 | head -3'"

# Output:
# Debian LLVM version 19.1.7
# Optimized build.
# Default target: x86_64-pc-linux-gnu

# Restart backend
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend clang --version 2>&1 | head -3 && docker restart llvm-obfuscator-backend"

# Output:
# Debian clang version 19.1.7 (3+b1)
# Target: x86_64-pc-linux-gnu
# Thread model: posix
# llvm-obfuscator-backend
```

---

## Issue 3: OLLVM Passes Not Recognized

### Problem
```
/usr/local/llvm-obfuscator/bin/opt: unknown pass name 'flattening'
```

### Root Cause
- System `opt` (v19) doesn't have OLLVM custom passes
- OLLVM passes in `LLVMObfuscationPlugin.so` are for LLVM 22, incompatible with opt 19

### Solution: Rebuild LLVM 22 with All Targets

#### Step 1: Check current LLVM build configuration
```bash
ssh devalgupta4@34.100.133.67 "grep LLVM_TARGETS_TO_BUILD /home/devalgupta4/llvm-project/build/CMakeCache.txt 2>/dev/null | head -3"

# Output:
# LLVM_TARGETS_TO_BUILD:STRING=X86
```

#### Step 2: Reconfigure with all targets
```bash
ssh devalgupta4@34.100.133.67 "cd /home/devalgupta4/llvm-project/build && cmake -DLLVM_TARGETS_TO_BUILD='all' ."

# Output (truncated):
# -- Targeting AArch64
# -- Targeting AMDGPU
# -- Targeting ARM
# -- Targeting AVR
# -- Targeting BPF
# -- Targeting Hexagon
# -- Targeting Lanai
# -- Targeting LoongArch
# -- Targeting Mips
# -- Targeting MSP430
# -- Targeting NVPTX
# -- Targeting PowerPC
# -- Targeting RISCV
# -- Targeting Sparc
# -- Targeting SPIRV
# -- Targeting SystemZ
# -- Targeting VE
# -- Targeting WebAssembly
# -- Targeting X86
# -- Targeting XCore
# ...
# -- Configuring done (7.2s)
# -- Generating done (3.8s)
# Reconfigured with all targets
```

#### Step 3: Rebuild LLVM, clang, and opt
```bash
ssh devalgupta4@34.100.133.67 "cd /home/devalgupta4/llvm-project/build && ninja LLVM clang opt 2>&1 | tail -20"

# Build took ~10-15 minutes
# Output:
# [2694/2694] Creating executable symlink bin/clang
```

#### Step 4: Download new binaries
```bash
# Download libLLVM.so
scp devalgupta4@34.100.133.67:/home/devalgupta4/llvm-project/build/lib/libLLVM.so.22.0git /tmp/libLLVM-new.so

# Download opt
scp devalgupta4@34.100.133.67:/home/devalgupta4/llvm-project/build/bin/opt /tmp/opt-new

# Output: Downloaded new binaries
```

#### Step 5: Deploy to production
```bash
# Copy to production server
scp /tmp/libLLVM-new.so root@69.62.77.147:/tmp/libLLVM.so.22.0git
scp /tmp/opt-new root@69.62.77.147:/tmp/opt

# Deploy to container
ssh root@69.62.77.147 "docker cp /tmp/libLLVM.so.22.0git llvm-obfuscator-backend:/usr/local/llvm-obfuscator/lib/libLLVM.so.22.0git && docker cp /tmp/opt llvm-obfuscator-backend:/usr/local/llvm-obfuscator/bin/opt && docker exec llvm-obfuscator-backend chmod +x /usr/local/llvm-obfuscator/bin/opt /usr/local/llvm-obfuscator/lib/libLLVM.so.22.0git && docker restart llvm-obfuscator-backend"

# Output:
# llvm-obfuscator-backend
# ✅ DEPLOYED & RESTARTED
```

#### Step 6: Verify opt and OLLVM passes
```bash
# Check opt version
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend opt --version 2>&1 | head -3"

# Output:
# LLVM (http://llvm.org/):
#   LLVM version 22.0.0git
#   Optimized build.

# Verify OLLVM passes load
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend opt -load-pass-plugin=/usr/local/llvm-obfuscator/lib/LLVMObfuscationPlugin.so --help 2>&1 | grep -E 'flattening|substitution|boguscf' | head -5"

# Output:
# --boguscf                                                            - inserting bogus control flow
#       --flattening                                                         - Call graph flattening
#       --substitution                                                       - operators substitution
```

---

## Issue 4: LLVM Version Mismatch (Clang 19 vs LLVM 22 Bitcode)

### Problem
```
error: Unknown attribute kind (102) (Producer: 'LLVM22.0.0git' Reader: 'LLVM 19.1.7')
```

### Root Cause
- `opt` (LLVM 22) produces bitcode with LLVM 22 attributes
- `clang` (LLVM 19 system version) cannot read LLVM 22 bitcode

### Solution: Deploy LLVM 22 clang

#### Step 1: Download and deploy clang
```bash
# Download LLVM 22 clang
scp devalgupta4@34.100.133.67:/home/devalgupta4/llvm-project/build/bin/clang /tmp/clang-22

# Copy to production
scp /tmp/clang-22 root@69.62.77.147:/tmp/

# Deploy to container
ssh root@69.62.77.147 "docker cp /tmp/clang-22 llvm-obfuscator-backend:/usr/local/llvm-obfuscator/bin/clang.real && docker exec llvm-obfuscator-backend chmod +x /usr/local/llvm-obfuscator/bin/clang.real && docker restart llvm-obfuscator-backend"

# Output:
# llvm-obfuscator-backend
# ✅ Deployed LLVM 22 clang
```

#### Step 2: Clang missing shared library
```bash
# Test clang
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend clang --version 2>&1 | head -3"

# Output:
# clang: error while loading shared libraries: libclang-cpp.so.22.0git: cannot open shared object file: No such file or directory
```

#### Step 3: Deploy libclang-cpp.so
```bash
# Download and deploy libclang-cpp
scp devalgupta4@34.100.133.67:/home/devalgupta4/llvm-project/build/lib/libclang-cpp.so.22.0git /tmp/
scp /tmp/libclang-cpp.so.22.0git root@69.62.77.147:/tmp/

ssh root@69.62.77.147 "docker cp /tmp/libclang-cpp.so.22.0git llvm-obfuscator-backend:/usr/local/llvm-obfuscator/lib/ && docker exec llvm-obfuscator-backend chmod +x /usr/local/llvm-obfuscator/lib/libclang-cpp.so.22.0git && docker restart llvm-obfuscator-backend"

# Output:
# llvm-obfuscator-backend
# ✅ Deployed libclang-cpp.so
```

#### Step 4: Verify clang works
```bash
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend clang --version 2>&1 | head -3"

# Output:
# clang version 22.0.0git (https://github.com/SkySingh04/llvm-project.git 66345e7cc7edc792c3cb02466e516441aa4a65f7)
# Target: x86_64-unknown-linux-gnu
# Thread model: posix
```

---

## Issue 5: OLLVM Flattening Pass Crash

### Problem
```
Command failed with exit code -11: /usr/local/llvm-obfuscator/bin/opt -load-pass-plugin=/usr/local/llvm-obfuscator/lib/LLVMObfuscationPlugin.so -passes=flattening,substitution,boguscf,split,linear-mba
```

### Root Cause
Bug in OLLVM flattening pass when processing certain switch statements:
```
Stack dump:
1. Running pass "(anonymous namespace)::FlatteningPassWrapper" on function "_ZL14table_describeP5Table"
2. Crash in llvm::LazyValueInfo::getConstantRange() -> ProcessSwitchInst()
```

### Solution
**Workaround**: Disable flattening pass for now. User can still use other OLLVM passes: substitution, boguscf, split, linear-mba.

---

## Issue 6: LTO Linker Incompatibility

### Problem
```
ld.lld: error: /tmp/pasted_source_obfuscated-cdcdb3.o: Unknown attribute kind (102) (Producer: 'LLVM22.0.0git' Reader: 'LLVM 19.1.7')
```

### Root Cause
- System linker `ld.lld` is version 19
- LLVM 22 bitcode with `-flto` flag requires LLVM 22 linker

### Solution
**Workaround**: Remove `-flto` flag from compilation. Link-Time Optimization requires matching linker version.

**Note**: Building LLVM 22 lld was attempted but lld project wasn't enabled in cmake configuration:
```bash
ssh devalgupta4@34.100.133.67 "cd /home/devalgupta4/llvm-project/build && ninja lld 2>&1"

# Output:
# ninja: error: unknown target 'lld', did you mean 'lli'?
```

---

## Issue 7: Frontend LTO Option Removal

### Problem
Users could still select `-flto` flag in the UI, which causes linker errors since LLVM 22 lld is not available.

### Solution
Remove LTO option from frontend UI and disable flag in code.

#### Step 1: Edit App.tsx to disable LTO
```bash
# Edit frontend source locally
# File: cmd/llvm-obfuscator/frontend/src/App.tsx
# Line 4735-4743: Comment out LTO checkbox
# Line 2741: Comment out -flto flag logic
```

Changes made:
```typescript
// Line 4735-4743: Commented out LTO checkbox
{/* LTO temporarily disabled - requires LLVM 22 linker */}
{/* <label className="sub-option">
  <input
    type="checkbox"
    checked={flagLTO}
    onChange={(e) => setFlagLTO(e.target.checked)}
  />
  Link-Time Optimization (-flto)
</label> */}

// Line 2740-2741: Disabled -flto flag
// LTO (Link-Time Optimization) - DISABLED: requires LLVM 22 linker (lld)
// if (flagLTO) flags.push('-flto');
```

#### Step 2: Package and copy frontend source
```bash
tar -czf /tmp/frontend-src.tar.gz -C cmd/llvm-obfuscator/frontend --exclude='node_modules' --exclude='dist' .
scp /tmp/frontend-src.tar.gz root@69.62.77.147:/tmp/

# Output: Copied frontend source to server
```

#### Step 3: Copy Dockerfile
```bash
scp /home/zrahay/oaas/cmd/llvm-obfuscator/frontend/Dockerfile.frontend root@69.62.77.147:/tmp/frontend-build/
```

#### Step 4: Rebuild frontend Docker image
```bash
ssh root@69.62.77.147 "cd /tmp/frontend-build && tar -xzf /tmp/frontend-src.tar.gz && docker build -f Dockerfile.frontend -t akashsingh04/llvm-obfuscator-frontend:latest . 2>&1 | tail -30"

# Output (build took ~30 seconds):
# #17 exporting to image
# #17 exporting layers 5.6s done
# #17 writing image sha256:863a5c786b1f465258cedbaf223f0ed8a2c6223ba35a17f20a02c83c2e85514d done
# #17 naming to docker.io/akashsingh04/llvm-obfuscator-frontend:latest done
# #17 DONE 5.6s
```

#### Step 5: Redeploy frontend container
```bash
ssh root@69.62.77.147 "docker stop llvm-obfuscator-frontend && docker rm llvm-obfuscator-frontend && docker run -d --name llvm-obfuscator-frontend --network oaas_obfuscator-network -p 4666:4666 --restart unless-stopped akashsingh04/llvm-obfuscator-frontend:latest"

# Output:
# llvm-obfuscator-frontend
# llvm-obfuscator-frontend
# 67fd05cde326e9bce09d6e03e71457bdba9625ac4884c237decef89b0c56f334
# ✅ Frontend redeployed
```

#### Step 6: Verify frontend is running
```bash
ssh root@69.62.77.147 "docker logs llvm-obfuscator-frontend --tail 5"

# Output:
# > llvm-obfuscator-frontend@1.0.0 preview
# > vite preview
#
#   ➜  Local:   http://localhost:4666/
#   ➜  Network: http://172.25.0.3:4666/
```

---

## Final Working Configuration

### Deployed Binaries (All LLVM 22)
```
/usr/local/llvm-obfuscator/bin/
├── clang -> clang.real
├── clang.real (LLVM 22.0.0git from custom build)
├── opt (LLVM 22.0.0git from custom build)

/usr/local/llvm-obfuscator/lib/
├── libLLVM.so.22.0git (145MB, with all targets)
├── libMLIR.so.22.0git (145MB)
├── libclang-cpp.so.22.0git (210MB)
├── MLIRObfuscation.so (1.1MB, fixed version)
├── LLVMObfuscationPlugin.so (26KB)
```

### Working Features
✅ MLIR string encryption (string-encrypt pass)
✅ OLLVM substitution
✅ OLLVM bogus control flow
✅ OLLVM split basic blocks
✅ OLLVM linear MBA
✅ Symbol obfuscation

### Disabled Features (Workarounds)
❌ OLLVM flattening (crashes on certain switch statements)
❌ Link-Time Optimization `-flto` (requires LLVM 22 lld which wasn't built)

---

## Verification Commands

### Check all binary versions
```bash
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend bash -c 'echo \"=== Clang ===\"  && clang --version && echo && echo \"=== Opt ===\" && opt --version && echo && echo \"=== Shared Libraries ===\" && ls -lh /usr/local/llvm-obfuscator/lib/*.so* | grep -E \"LLVM|MLIR|clang\"'"
```

### Check OLLVM passes
```bash
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend opt -load-pass-plugin=/usr/local/llvm-obfuscator/lib/LLVMObfuscationPlugin.so --help 2>&1 | grep -A2 'OLLVM Obfuscation Passes'"
```

### Check MLIR passes
```bash
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend bash -c 'export LD_LIBRARY_PATH=/usr/local/llvm-obfuscator/lib && /home/devalgupta4/llvm-project/build/bin/mlir-opt --help 2>&1 | grep string-encrypt'"
```

---

## GCP Tarball Updates

Updated `llvm-obfuscator-binaries.tar.gz` on `gs://llvmbins/` with:
- ✅ `mlir-opt` (18K, dynamic)
- ✅ `mlir-translate` (17K, dynamic)
- ✅ `libMLIR.so.22.0git` (145MB)
- ✅ `libLLVM.so.22.0git` (75MB, with all targets)
- ✅ `MLIRObfuscation.so` (1.1MB, fixed version)

---

## Related Documentation
- [STRING_ENCRYPTION_FIX.md](./STRING_ENCRYPTION_FIX.md) - Details on the MLIR plugin fixes
- [CLAUDE.md](../CLAUDE.md) - Deployment procedures

---

## Issue 8: Library Path Not Configured (December 9, 2025)

### Problem
```
clang: error while loading shared libraries: libclang-cpp.so.22.0git: cannot open shared object file: No such file or directory
```

### Root Cause
- Shared libraries exist in `/usr/local/llvm-obfuscator/lib/`
- Linux dynamic linker doesn't know to look there
- `LD_LIBRARY_PATH` environment variable wasn't being passed to spawned clang processes

### Solution: Configure ldconfig

```bash
# Add library path to system config and run ldconfig
ssh root@69.62.77.147 "docker exec llvm-obfuscator-backend bash -c 'echo /usr/local/llvm-obfuscator/lib > /etc/ld.so.conf.d/llvm.conf && ldconfig'"
```

### Dockerfile Fix
Updated `Dockerfile.backend` to:
1. Copy all required shared libraries (`libclang-cpp.so.22.0git`, `libMLIR.so.22.0git`)
2. Run `ldconfig` during build to register library paths system-wide

```dockerfile
# Added to COPY command:
plugins/linux-x86_64/libclang-cpp.so.22.0git \
plugins/linux-x86_64/libMLIR.so.22.0git \

# Added to RUN command:
echo "/usr/local/llvm-obfuscator/lib" > /etc/ld.so.conf.d/llvm.conf && ldconfig
```

---

## Date
December 8-9, 2025
