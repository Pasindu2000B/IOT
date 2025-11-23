#!/usr/bin/env python3
"""
Direct MQTT to InfluxDB bridge with automatic reconnection and robust error handling
"""
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import json
import time
import logging
from datetime import datetime
import os

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "machine_sensor_data"
MQTT_USERNAME = "test"
MQTT_PASSWORD = "test"

INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "GO7pQ79-Vo-k6uwpQrMmJmITzLRHxyrFbFDrnRbz8PgZbLHKe5hpwNZCWi6Z_zolPRjn7jUQ6irQk-BPe3LK9Q=="
INFLUXDB_ORG = "Ruhuna_Eng"
INFLUXDB_BUCKET = "New_Sensor"

# Reconnection settings
RECONNECT_DELAY = 5  # seconds
MAX_RECONNECT_DELAY = 300  # 5 minutes

# Initialize InfluxDB client
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Message counter
message_count = 0
last_log_time = time.time()

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        logger.info(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        logger.info(f"✅ Subscribed to topic: {MQTT_TOPIC}")
    else:
        logger.error(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Callback when MQTT message received"""
    global message_count, last_log_time
    
    try:
        # Parse JSON payload
        payload = json.loads(msg.payload.decode())
        
        # Create InfluxDB point
        point = Point("sensor_data") \
            .tag("workspace_id", payload.get("workspace_id", "unknown")) \
            .tag("sensor_type", payload.get("sensor_type", "unknown")) \
            .field("current", float(payload.get("current", 0))) \
            .field("accX", float(payload.get("accX", 0))) \
            .field("accY", float(payload.get("accY", 0))) \
            .field("accZ", float(payload.get("accZ", 0))) \
            .field("tempA", float(payload.get("tempA", 0))) \
            .field("tempB", float(payload.get("tempB", 0)))
        
        # Write to InfluxDB
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        
        message_count += 1
        
        # Log every 10 seconds instead of every message to reduce noise
        current_time = time.time()
        if current_time - last_log_time >= 10:
            logger.info(f"📊 Processed {message_count} messages total | Latest: workspace={payload.get('workspace_id')}")
            last_log_time = current_time
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")

def on_disconnect(client, userdata, rc):
    """Callback when disconnected from MQTT broker"""
    if rc != 0:
        logger.warning(f"⚠️  Unexpected disconnection (RC: {rc}). Will attempt to reconnect...")
    else:
        logger.info("Disconnected from MQTT broker")

def main():
    """Main function to run the bridge with automatic reconnection"""
    logger.info("=" * 60)
    logger.info("MQTT to InfluxDB Bridge with Auto-Reconnection")
    logger.info("=" * 60)
    logger.info(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    logger.info(f"MQTT Topic: {MQTT_TOPIC}")
    logger.info(f"InfluxDB: {INFLUXDB_URL}")
    logger.info(f"Bucket: {INFLUXDB_BUCKET}")
    logger.info("=" * 60)
    
    # Setup MQTT client with automatic reconnection
    client = mqtt.Client(client_id="mqtt_influx_bridge")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Configure automatic reconnection
    client.reconnect_delay_set(min_delay=RECONNECT_DELAY, max_delay=MAX_RECONNECT_DELAY)
    
    # Connect with retry logic
    connected = False
    retry_count = 0
    max_retries = 5
    
    while not connected and retry_count < max_retries:
        try:
            logger.info(f"🔄 Connecting to MQTT broker (attempt {retry_count + 1}/{max_retries})...")
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            connected = True
        except Exception as e:
            retry_count += 1
            logger.warning(f"⚠️  Connection failed: {e}")
            if retry_count < max_retries:
                logger.info(f"🔄 Retrying in {RECONNECT_DELAY} seconds...")
                time.sleep(RECONNECT_DELAY)
            else:
                logger.error("❌ Max connection retries reached. Exiting.")
                influx_client.close()
                return
    
    # Start MQTT loop with automatic reconnection
    logger.info("✅ Bridge is running. Press Ctrl+C to exit.")
    logger.info("=" * 60)
    
    try:
        # loop_forever() automatically handles reconnection
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("⏹️  Shutting down bridge...")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        client.disconnect()
        influx_client.close()
        logger.info(f"📊 Total messages processed: {message_count}")
        logger.info("✅ Bridge stopped gracefully")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()
