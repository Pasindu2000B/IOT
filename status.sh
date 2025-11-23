#!/bin/bash
# =============================================================================
# Check IOT System Status
# =============================================================================

echo "==============================================="
echo "  IOT System Status"
echo "==============================================="
echo ""

echo "🐳 Docker Containers:"
docker-compose ps
echo ""

echo "📊 Python Processes:"
if [ -f logs/bridge.pid ]; then
    if ps -p $(cat logs/bridge.pid) > /dev/null 2>&1; then
        echo "   ✅ Bridge:         Running (PID: $(cat logs/bridge.pid))"
    else
        echo "   ❌ Bridge:         Stopped"
    fi
else
    echo "   ❌ Bridge:         Not started"
fi

if [ -f logs/generate_data.pid ]; then
    if ps -p $(cat logs/generate_data.pid) > /dev/null 2>&1; then
        echo "   ✅ Data Generator: Running (PID: $(cat logs/generate_data.pid))"
    else
        echo "   ❌ Data Generator: Stopped"
    fi
else
    echo "   ❌ Data Generator: Not started"
fi
echo ""

echo "📁 Recent Models:"
ls -lht spark-apps/models/*.pt 2>/dev/null | head -3 || echo "   No models found"
echo ""

echo "==============================================="
