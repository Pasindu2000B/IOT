#!/bin/bash
# =============================================================================
# Start MQTT to InfluxDB Bridge as a System Service (Linux)
# =============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/mqtt_to_influx_bridge.py"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$LOG_DIR/bridge.pid"

# Create logs directory
mkdir -p "$LOG_DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Bridge is already running (PID: $PID)"
        exit 1
    else
        echo "Removing stale PID file..."
        rm "$PID_FILE"
    fi
fi

# Start bridge in background
echo "🚀 Starting MQTT to InfluxDB Bridge..."
nohup python3 "$PYTHON_SCRIPT" > "$LOG_DIR/bridge_output.log" 2>&1 &
echo $! > "$PID_FILE"

# Wait a moment and check if it's running
sleep 2
if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
    echo "✅ Bridge started successfully (PID: $(cat $PID_FILE))"
    echo "📝 Logs: tail -f $LOG_DIR/bridge.log"
else
    echo "❌ Failed to start bridge. Check logs: $LOG_DIR/bridge_output.log"
    rm "$PID_FILE"
    exit 1
fi
