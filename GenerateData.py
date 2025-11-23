import paho.mqtt.client as mqtt
import time
import json
import random


MQTT_BROKER_HOST = "localhost" 
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "machine_sensor_data"  
CLIENT_ID = "data_generator_script"


SENSOR_WORKSPACES = ["lathe-1-spindle", "cnc-mill-5-axis", "robot-arm-02"]

def generate_sensor_data():
    
    data = {
        # --- These are your TAGS ---
        "workspace_id": random.choice(SENSOR_WORKSPACES),
        "sensor_type": "industrial",

        # --- These are your FIELDS (matching notebook: temp_body, temp_shaft, current, vibration_magnitude) ---
        "temp_body": round(random.uniform(55.0, 80.0), 2),      # Previously tempA
        "temp_shaft": round(random.uniform(55.0, 80.0), 2),     # Previously tempB
        "current": round(random.uniform(10.0, 25.0), 2),
        "vibration_magnitude": round(random.uniform(0.5, 2.5), 4)  # Combined vibration from X/Y/Z
    }
    return data

def connect_mqtt():
    """Connects to the MQTT broker."""
    client = mqtt.Client(client_id=CLIENT_ID)
    client.username_pw_set("test", "test")  # Set credentials
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    return client

def run_simulator():
    """Runs the main data generation loop."""
    client = connect_mqtt()
    client.loop_start()  # Starts a background thread to handle network
    time.sleep(2)  # Give the client time to connect
    print(f"Started data generator.")
    print(f"Publishing to topic: {MQTT_TOPIC}")
    print(f"Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    
    try:
        while True:
            # 1. Generate new data
            data = generate_sensor_data()
            
            # 2. Convert to JSON string
            payload = json.dumps(data)
            
            # 3. Publish to MQTT
            result = client.publish(MQTT_TOPIC, payload)
            result.wait_for_publish() # Wait for publish to complete
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Published: {payload}")
            else:
                print(f"Failed to publish message: {result.rc}")

            # 4. Wait for 2 seconds
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nShutting down generator.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    run_simulator()
