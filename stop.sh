#!/bin/bash
# =============================================================================
# Stop IOT Predictive Maintenance System
# =============================================================================

echo "==============================================="
echo "  Stopping IOT System"
echo "==============================================="

# Stop Python processes
echo ""
echo "🛑 Stopping Python processes..."

chmod +x stop_bridge.sh
./stop_bridge.sh 2>/dev/null || echo "   Bridge not running"

if [ -f logs/generate_data.pid ]; then
    kill $(cat logs/generate_data.pid) 2>/dev/null || true
    rm logs/generate_data.pid
    echo "   ✅ Data generator stopped"
fi

# Stop Docker containers
echo ""
echo "🐳 Stopping Docker containers..."
docker-compose down

echo ""
echo "==============================================="
echo "  ✅ System Stopped Successfully"
echo "==============================================="
