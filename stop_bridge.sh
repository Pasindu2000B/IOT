#!/bin/bash
# =============================================================================
# Stop MQTT to InfluxDB Bridge (Linux)
# =============================================================================

LOG_DIR="./logs"
PID_FILE="$LOG_DIR/bridge.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  Bridge is not running (no PID file)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  Bridge process not found (stale PID file)"
    rm "$PID_FILE"
    exit 0
fi

echo "🛑 Stopping bridge (PID: $PID)..."
kill $PID

# Wait for graceful shutdown
for i in {1..10}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "✅ Bridge stopped gracefully"
        rm "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# Force kill if still running
echo "⚠️  Forcing bridge to stop..."
kill -9 $PID 2>/dev/null
rm "$PID_FILE"
echo "✅ Bridge stopped (forced)"
