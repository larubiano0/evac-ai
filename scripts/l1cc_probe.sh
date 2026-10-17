#!/usr/bin/env bash
# L1CC capability probe. Run on the LinuxONE VM:  bash l1cc_probe.sh 2>&1 | tee probe.txt
# Read-only: it installs nothing system-wide (pip tests go into a throwaway venv in /tmp).
set +e
h(){ echo; echo "===== $* ====="; }

h SYSTEM;   uname -a; cat /etc/os-release 2>/dev/null | head -4; uptime
h CPU;      lscpu 2>/dev/null | grep -E "Architecture|Byte Order|^CPU\(s\)|Model name|Machine type|Thread|Core|Socket|Hypervisor|L1d|L2|L3"
h CPU_FEATURES; grep -m1 -E "^features" /proc/cpuinfo; grep -m3 -iE "machine|version" /proc/cpuinfo | head -3
echo "--- AI accelerator (NNPA facility, needed for zDNN): ";  grep -qw nnpa /proc/cpuinfo && echo "NNPA PRESENT" || echo "nnpa flag NOT found"
echo "--- Vector extensions (vx/vxe/vxe2 matter for llama.cpp/numpy speed):"; grep -m1 features /proc/cpuinfo | grep -oE "\bvx[a-z0-9]*\b" | sort -u | tr '\n' ' '; echo
h MEMORY;   free -h; grep -E "MemTotal|SwapTotal" /proc/meminfo
h DISK;     df -h / /home /tmp 2>/dev/null
h GPU;      ls /dev/nvidia* 2>/dev/null || echo "no GPU (expected)"
h CONTAINERS; for c in docker podman; do command -v $c && $c --version; done; (docker info 2>/dev/null || podman info 2>/dev/null) | grep -iE "server version|storage driver|rootless" | head -5
h TOOLCHAIN; for t in python3 pip3 gcc g++ cmake make git conda mamba micromamba; do printf "%-11s " $t; command -v $t >/dev/null && ($t --version 2>&1 | head -1) || echo MISSING; done
h SUDO;     sudo -n true 2>/dev/null && echo "passwordless sudo: YES" || echo "passwordless sudo: no"
h PYTHON_ENDIAN; python3 -c "import sys,platform;print(sys.byteorder, platform.machine(), sys.version.split()[0])"

h NETWORK_OUTBOUND
for u in https://pypi.org https://github.com https://overpass-api.de/api/status \
         https://download.geofabrik.de https://copernicus-dem-30m.s3.amazonaws.com \
         https://bipadportal.gov.np/api/v1/ https://hydrology.gov.np https://huggingface.co \
         https://us-south.ml.cloud.ibm.com ; do
  printf "%-50s " "$u"; curl -s -o /dev/null -m 10 -w "%{http_code} %{time_total}s\n" "$u" || echo FAIL
done
h LISTENING_PORTS; (ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | head -15
h FIREWALL; sudo -n firewall-cmd --list-all 2>/dev/null | head -10 || echo "(no firewalld info)"

h PIP_WHEELS  # does a binary wheel exist for s390x, or would pip compile from source?
V=/tmp/probe_venv; python3 -m venv $V >/dev/null 2>&1 && . $V/bin/activate
for p in numpy scipy scikit-learn pandas networkx fastapi uvicorn tifffile pillow shapely pyproj \
         rasterio onnxruntime torch llama-cpp-python; do
  printf "%-18s " $p
  pip download --only-binary=:all: --no-deps -q -d /tmp/probe_whl $p >/dev/null 2>&1 && echo "WHEEL OK" || echo "no s390x wheel (source build or unavailable)"
done
deactivate 2>/dev/null; rm -rf $V /tmp/probe_whl

h QUICK_BENCH  # matrix-multiply speed (proxy for model inference throughput)
python3 - <<'EOF' 2>&1
try:
    import numpy as np, time, os
    a=np.random.rand(2000,2000).astype(np.float32); t=time.time(); [a@a for _ in range(3)]; dt=(time.time()-t)/3
    print(f"numpy {np.__version__}: 2000^3 matmul {dt:.2f}s  -> ~{2*2000**3/dt/1e9:.1f} GFLOP/s, cores={os.cpu_count()}")
except ImportError: print("numpy not installed system-wide (fine; use venv)")
EOF
h DONE; echo "Paste probe.txt back to Claude."
