#!/bin/bash

# Docker Auto-Restart Setup for VM
# Run this script on the VM to enable auto-restart for all containers

echo "========================================================================"
echo "  Docker Container Auto-Restart Setup"
echo "========================================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo bash setup_docker_restart.sh)"
    exit 1
fi

echo "This script will set restart policy for all Docker containers to 'unless-stopped'"
echo "Containers will automatically restart after crashes or VM reboots."
echo ""

# Get all container IDs
echo "Finding all Docker containers..."
CONTAINERS=$(docker ps -aq)

if [ -z "$CONTAINERS" ]; then
    echo "No Docker containers found!"
    exit 1
fi

echo "Found $(echo "$CONTAINERS" | wc -l) container(s)"
echo ""

# Update restart policy for each container
echo "Setting restart policies..."
for CONTAINER in $CONTAINERS; do
    CONTAINER_NAME=$(docker inspect --format='{{.Name}}' "$CONTAINER" | sed 's/\///')
    echo "  • $CONTAINER_NAME ($CONTAINER)"
    docker update --restart=unless-stopped "$CONTAINER"
done

echo ""
echo "========================================================================"
echo "  Verification"
echo "========================================================================"
echo ""

# Show container status with restart policy
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.State}}\t{{.RestartPolicy}}"

echo ""
echo "========================================================================"
echo "  Setup Complete!"
echo "========================================================================"
echo ""
echo "All containers will now:"
echo "  ✅ Auto-restart on crash"
echo "  ✅ Auto-start on VM reboot"
echo "  ✅ Stay stopped if manually stopped"
echo ""
echo "To verify after VM reboot:"
echo "  docker ps -a"
echo ""
echo "To check logs:"
echo "  docker logs <container-name>"
echo ""
