#!/bin/bash
#
# SLURM Offline Package Downloader
#
# This script downloads all required packages for SLURM and MUNGE
# to an NFS share, creating a local repository for offline installation
# on compute nodes without internet access.
#
# Run this on the head node which has internet connectivity.
#

set -e

# Configuration
REPO_DIR="/nfs/shared/slurm-repo"

echo "============================================"
echo "SLURM Offline Package Downloader"
echo "============================================"
echo ""
echo "Target directory: $REPO_DIR"
echo ""

# Create repository directory
echo "Creating repository directory..."
sudo mkdir -p $REPO_DIR
sudo chown $USER:$USER $REPO_DIR

# Clear any existing packages
echo "Clearing old packages..."
rm -rf $REPO_DIR/*.rpm 2>/dev/null || true
rm -rf $REPO_DIR/repodata 2>/dev/null || true

# Install required tools
echo ""
echo "=== Step 1: Installing repository tools ==="
sudo dnf install -y epel-release
sudo dnf install -y createrepo dnf-plugins-core

# Download base system libraries
echo ""
echo "=== Step 2: Downloading base system libraries ==="
dnf download --resolve --destdir=$REPO_DIR \
    readline \
    lua \
    lua-libs \
    ncurses \
    ncurses-libs \
    ncurses-base

# Download MUNGE packages
echo ""
echo "=== Step 3: Downloading MUNGE packages ==="
dnf download --resolve --destdir=$REPO_DIR \
    munge \
    munge-libs \
    munge-devel

# Download SLURM packages with all dependencies
echo ""
echo "=== Step 4: Downloading SLURM packages ==="
dnf download --resolve --alldeps --destdir=$REPO_DIR \
    slurm \
    slurm-libs \
    slurm-slurmd \
    slurm-slurmctld \
    slurm-perlapi

# Download s-nail (provides /bin/mailx required by SLURM)
echo ""
echo "=== Step 5: Downloading mail utility ==="
dnf download --resolve --destdir=$REPO_DIR s-nail

# Download additional dependencies
echo ""
echo "=== Step 6: Downloading additional dependencies ==="
dnf download --resolve --destdir=$REPO_DIR \
    libjwt \
    freeipmi \
    freeipmi-libs \
    hwloc \
    hwloc-libs \
    lz4 \
    lz4-libs \
    http-parser \
    json-c \
    libyaml \
    dbus-libs \
    pmix \
    perl-interpreter \
    perl-libs || true

# Create repository metadata
echo ""
echo "=== Step 7: Creating repository metadata ==="
createrepo $REPO_DIR

# Set permissions for all nodes to access
echo ""
echo "=== Step 8: Setting permissions ==="
chmod -R 755 $REPO_DIR

# Display summary
PKG_COUNT=$(ls -1 $REPO_DIR/*.rpm 2>/dev/null | wc -l)

echo ""
echo "============================================"
echo "Download Complete"
echo "============================================"
echo ""
echo "Packages downloaded: $PKG_COUNT"
echo "Repository location: $REPO_DIR"
echo ""
echo "Packages:"
ls -1 $REPO_DIR/*.rpm | xargs -n1 basename | sort
echo ""
echo "The repository is ready for offline installation."
echo "Run the Ansible playbook to install on all nodes."
