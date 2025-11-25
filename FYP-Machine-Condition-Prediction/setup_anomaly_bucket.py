"""
Setup Anomaly Bucket in InfluxDB
Creates a separate 'Anomalies' bucket for storing anomaly detection logs
"""

import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

# Load environment variables
load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL", "http://142.93.220.152:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "Ruhuna_Eng")
ANOMALY_BUCKET = os.getenv("ANOMALY_BUCKET", "Anomalies")

def setup_anomaly_bucket():
    """Create Anomalies bucket if it doesn't exist"""
    
    if not INFLUX_TOKEN:
        print("❌ Error: INFLUX_TOKEN not found in .env file")
        return False
    
    try:
        # Connect to InfluxDB
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        buckets_api = client.buckets_api()
        
        print(f"\n🔍 Checking for '{ANOMALY_BUCKET}' bucket...")
        
        # Check if bucket already exists
        existing_buckets = buckets_api.find_buckets().buckets
        bucket_exists = any(b.name == ANOMALY_BUCKET for b in existing_buckets)
        
        if bucket_exists:
            print(f"✅ Bucket '{ANOMALY_BUCKET}' already exists")
            
            # Get bucket details
            bucket = next(b for b in existing_buckets if b.name == ANOMALY_BUCKET)
            print(f"\n📋 Bucket Details:")
            print(f"   Name: {bucket.name}")
            print(f"   ID: {bucket.id}")
            print(f"   Organization: {INFLUX_ORG}")
            print(f"   Retention: {bucket.retention_rules[0].every_seconds // 86400} days" if bucket.retention_rules else "   Retention: Infinite")
            
        else:
            print(f"📦 Creating new bucket '{ANOMALY_BUCKET}'...")
            
            # Set retention to 90 days (7776000 seconds)
            retention_seconds = 90 * 24 * 60 * 60
            
            # Create bucket with retention
            bucket = buckets_api.create_bucket(
                bucket_name=ANOMALY_BUCKET,
                org=INFLUX_ORG,
                retention_rules=[{"type": "expire", "everySeconds": retention_seconds}]
            )
            
            print(f"✅ Bucket '{ANOMALY_BUCKET}' created successfully!")
            print(f"\n📋 Bucket Details:")
            print(f"   Name: {bucket.name}")
            print(f"   ID: {bucket.id}")
            print(f"   Organization: {INFLUX_ORG}")
            print(f"   Retention: 90 days")
        
        print(f"\n✅ Anomaly logging system ready!")
        print(f"\n📊 Anomaly data will include:")
        print(f"   • Workspace ID and timestamp")
        print(f"   • Anomaly type (which sensor)")
        print(f"   • Severity score and level")
        print(f"   • Predicted vs actual values")
        print(f"   • Deviation percentages")
        print(f"   • Affected features")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error setting up anomaly bucket: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("  ANOMALY BUCKET SETUP - InfluxDB")
    print("=" * 70)
    print(f"\n📍 InfluxDB: {INFLUX_URL}")
    print(f"🏢 Organization: {INFLUX_ORG}")
    print(f"📦 Bucket: {ANOMALY_BUCKET}")
    
    success = setup_anomaly_bucket()
    
    if success:
        print("\n🎯 Next Steps:")
        print("   1. Start inference service: python main.py")
        print("   2. System will automatically log anomalies when detected")
        print("   3. Query anomalies from InfluxDB UI or API")
        print("\n💡 Query example (Flux):")
        print(f'   from(bucket: "{ANOMALY_BUCKET}")')
        print('   |> range(start: -24h)')
        print('   |> filter(fn: (r) => r._measurement == "anomaly_detections")')
    
    print("\n" + "=" * 70)
