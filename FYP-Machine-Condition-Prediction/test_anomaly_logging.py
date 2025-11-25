"""
Test Anomaly Logging - Write a test anomaly to verify the system works
"""

import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL", "http://142.93.220.152:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "Ruhuna_Eng")
ANOMALY_BUCKET = os.getenv("ANOMALY_BUCKET", "Anomalies")

def write_test_anomaly():
    """Write a test anomaly to InfluxDB to verify the system works"""
    
    if not INFLUX_TOKEN:
        print("❌ Error: INFLUX_TOKEN not found")
        return False
    
    try:
        # Connect to InfluxDB
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        print(f"\n📝 Writing TEST anomaly to InfluxDB...")
        print(f"   Bucket: {ANOMALY_BUCKET}")
        print(f"   VM: {INFLUX_URL}")
        
        # Create test anomaly point
        point = Point("anomaly_detections") \
            .tag("workspace_id", "test-workspace") \
            .tag("anomaly_type", "current") \
            .tag("severity_level", "high") \
            .field("severity_score", 0.95) \
            .field("alert_message", "TEST ANOMALY - System verification") \
            .field("affected_features", "current") \
            .field("actual_current", 25.5) \
            .field("predicted_current", 12.5) \
            .field("deviation_current", 13.0) \
            .field("deviation_pct_current", 104.0) \
            .field("actual_accX", 0.15) \
            .field("predicted_accX", 0.14) \
            .field("actual_accY", 0.12) \
            .field("predicted_accY", 0.11) \
            .field("actual_accZ", 0.18) \
            .field("predicted_accZ", 0.17) \
            .field("actual_tempA", 45.0) \
            .field("predicted_tempA", 44.5) \
            .field("actual_tempB", 42.0) \
            .field("predicted_tempB", 41.8)
        
        # Write to InfluxDB
        write_api.write(bucket=ANOMALY_BUCKET, record=point)
        
        print("\n✅ TEST anomaly written successfully!")
        print("\n📊 Anomaly Details:")
        print("   Workspace: test-workspace")
        print("   Type: current (high severity)")
        print("   Score: 0.95")
        print("   Deviation: +13.0A (104%)")
        print("   Message: TEST ANOMALY - System verification")
        
        print("\n🔍 Verify in InfluxDB:")
        print(f"   1. Open: {INFLUX_URL}")
        print(f"   2. Go to Data Explorer")
        print(f"   3. Select bucket: {ANOMALY_BUCKET}")
        print(f"   4. Look for measurement: anomaly_detections")
        print(f"   5. Filter by workspace_id: test-workspace")
        
        print("\n💡 Or query via Python:")
        print(f"   python check_anomalies.py")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error writing test anomaly: {e}")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("  TEST ANOMALY LOGGER - Verify InfluxDB Connection")
    print("=" * 80)
    
    success = write_test_anomaly()
    
    if success:
        print("\n✅ SUCCESS! Anomaly logging system is working correctly.")
        print("\n🎯 Next: Generate real data and wait for ML model to detect anomalies")
        print("   python GenerateData.py")
    else:
        print("\n❌ FAILED! Check:")
        print("   • INFLUX_TOKEN in .env file")
        print("   • VM InfluxDB is accessible (142.93.220.152:8086)")
        print("   • Anomalies bucket exists")
    
    print("\n" + "=" * 80)
