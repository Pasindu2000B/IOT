"""
IoT Sensor Data Generator
Generates realistic machine sensor data and publishes to MQTT broker
"""

import json
import time
import random
import math
from datetime import datetime
import paho.mqtt.client as mqtt

# MQTT Configuration
MQTT_BROKER = "142.93.220.152"  # Your VM IP
MQTT_PORT = 1883
MQTT_TOPIC = "machine_sensor_data"

# Workspace configurations
WORKSPACES = [
    "cnc-mill-5-axis",
    "lathe-1-spindle", 
    "robot-arm-02"
]

class SensorDataGenerator:
    def __init__(self):
        self.client = mqtt.Client()
        self.connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.connected = True
        else:
            print(f"❌ Connection failed with code {rc}")
            
    def connect(self):
        """Connect to MQTT broker"""
        self.client.on_connect = self.on_connect
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 5
            start = time.time()
            while not self.connected and (time.time() - start) < timeout:
                time.sleep(0.1)
                
            if not self.connected:
                print("❌ Connection timeout")
                return False
                
            return True
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def generate_normal_data(self, workspace, base_values):
        """Generate normal operating sensor data"""
        return {
            "workspace_id": workspace,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "current": round(base_values["current"] + random.uniform(-0.5, 0.5), 2),
            "accX": round(base_values["accX"] + random.uniform(-0.2, 0.2), 3),
            "accY": round(base_values["accY"] + random.uniform(-0.2, 0.2), 3),
            "accZ": round(base_values["accZ"] + random.uniform(-0.2, 0.2), 3),
            "tempA": round(base_values["tempA"] + random.uniform(-1.0, 1.0), 1),
            "tempB": round(base_values["tempB"] + random.uniform(-1.0, 1.0), 1)
        }
    
    def generate_anomaly_data(self, workspace, base_values, anomaly_type):
        """Generate anomalous sensor data"""
        data = self.generate_normal_data(workspace, base_values)
        
        if anomaly_type == "high_current":
            data["current"] = round(base_values["current"] * random.uniform(1.5, 2.0), 2)
        elif anomaly_type == "vibration":
            data["accX"] = round(base_values["accX"] * random.uniform(2.0, 3.0), 3)
            data["accY"] = round(base_values["accY"] * random.uniform(2.0, 3.0), 3)
            data["accZ"] = round(base_values["accZ"] * random.uniform(2.0, 3.0), 3)
        elif anomaly_type == "overheating":
            data["tempA"] = round(base_values["tempA"] + random.uniform(10, 20), 1)
            data["tempB"] = round(base_values["tempB"] + random.uniform(10, 20), 1)
        
        return data
    
    def publish_data(self, data):
        """Publish sensor data to MQTT"""
        try:
            payload = json.dumps(data)
            result = self.client.publish(MQTT_TOPIC, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                print(f"❌ Publish failed: {result.rc}")
                return False
        except Exception as e:
            print(f"❌ Publish error: {e}")
            return False
    
    def run(self, duration_minutes=None, interval_seconds=2):
        """
        Run data generation
        
        Args:
            duration_minutes: How long to run (None = infinite)
            interval_seconds: Time between readings (default: 2 seconds)
        """
        if not self.connect():
            return
        
        # Base values for each workspace
        workspace_configs = {
            "cnc-mill-5-axis": {
                "current": 12.5,
                "accX": 0.15,
                "accY": 0.12,
                "accZ": 0.18,
                "tempA": 45.0,
                "tempB": 42.0
            },
            "lathe-1-spindle": {
                "current": 15.0,
                "accX": 0.20,
                "accY": 0.15,
                "accZ": 0.25,
                "tempA": 50.0,
                "tempB": 48.0
            },
            "robot-arm-02": {
                "current": 8.5,
                "accX": 0.10,
                "accY": 0.08,
                "accZ": 0.12,
                "tempA": 38.0,
                "tempB": 36.0
            }
        }
        
        print(f"\n🚀 Starting data generation...")
        print(f"   Workspaces: {', '.join(WORKSPACES)}")
        print(f"   Interval: {interval_seconds} seconds")
        if duration_minutes:
            print(f"   Duration: {duration_minutes} minutes")
        else:
            print(f"   Duration: Infinite (Ctrl+C to stop)")
        print(f"   Topic: {MQTT_TOPIC}\n")
        
        start_time = time.time()
        count = 0
        anomaly_counter = 0
        
        try:
            while True:
                # Check duration
                if duration_minutes:
                    elapsed = (time.time() - start_time) / 60
                    if elapsed >= duration_minutes:
                        print(f"\n✅ Completed {duration_minutes} minutes of data generation")
                        break
                
                # Generate data for each workspace
                for workspace in WORKSPACES:
                    base_values = workspace_configs[workspace]
                    
                    # Inject anomalies occasionally (5% chance)
                    if random.random() < 0.05:
                        anomaly_type = random.choice(["high_current", "vibration", "overheating"])
                        data = self.generate_anomaly_data(workspace, base_values, anomaly_type)
                        anomaly_counter += 1
                    else:
                        data = self.generate_normal_data(workspace, base_values)
                    
                    # Publish
                    if self.publish_data(data):
                        count += 1
                        print(f"[{workspace}] Current: {data['current']}A, "
                              f"Temp: {data['tempA']}°C, Acc: {data['accX']}/{data['accY']}/{data['accZ']}")
                
                # Wait for next interval
                time.sleep(interval_seconds)
                
                # Show stats every 50 readings
                if count % 50 == 0:
                    print(f"\n📊 Stats: {count} readings sent, {anomaly_counter} anomalies ({anomaly_counter/count*100:.1f}%)\n")
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Stopped by user")
            print(f"📊 Final stats: {count} readings sent, {anomaly_counter} anomalies")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print("✅ Disconnected from MQTT broker")


def main():
    """Main entry point"""
    print("=" * 70)
    print("  IoT SENSOR DATA GENERATOR")
    print("=" * 70)
    print(f"\n📍 Target: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"📡 Topic: {MQTT_TOPIC}")
    print(f"🏭 Workspaces: {len(WORKSPACES)}")
    
    generator = SensorDataGenerator()
    
    # Run forever (or specify duration in minutes)
    generator.run(duration_minutes=None, interval_seconds=2)


if __name__ == "__main__":
    main()
