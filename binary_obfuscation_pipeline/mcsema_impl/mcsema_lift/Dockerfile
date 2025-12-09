# McSema Lift Service
# IMPORTANT: Must run on amd64/x86_64 platform
# Use: docker build --platform linux/amd64 -t mcsema-lift .
#
# McSema lifts machine code (from CFG) to LLVM 11 bitcode.

FROM --platform=linux/amd64 ubuntu:20.04

LABEL maintainer="oaas-team"
LABEL description="McSema Lift Service - Binary to LLVM IR lifter"

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-protobuf \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Flask for the service API
RUN pip3 install --no-cache-dir flask requests

# Create directories
RUN mkdir -p /app /mcsema/mcsema /mcsema/remill /app/cfg /app/output

WORKDIR /app

# Copy McSema pre-built binaries (from mcsema-install)
# These are the pre-built binaries from the McSema GitHub release
# Built for Ubuntu 20.04 + LLVM 11
COPY mcsema-install/mcsema /mcsema/mcsema
COPY mcsema-install/remill /mcsema/remill

# Make binaries executable
RUN chmod +x /mcsema/mcsema/bin/* 2>/dev/null || true && \
    chmod +x /mcsema/remill/bin/* 2>/dev/null || true

# Add McSema to PATH
ENV PATH="/mcsema/mcsema/bin:/mcsema/remill/bin:${PATH}"
ENV REMILL_SEMANTICS_DIR="/mcsema/remill/share/remill/11.0/semantics"

# Copy the service script
COPY binary_obfuscation_pipeline/mcsema_impl/mcsema_lift/lift_service.py /app/lift_service.py

# Expose the service port
EXPOSE 5002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

# Run the lift service
CMD ["python3", "/app/lift_service.py"]
