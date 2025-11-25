"""
Check Anomalies Bucket - Query logged anomalies from InfluxDB
"""

import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from datetime import datetime, timedelta

load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL", "http://142.93.220.152:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "Ruhuna_Eng")
ANOMALY_BUCKET = os.getenv("ANOMALY_BUCKET", "Anomalies")

def query_anomalies(hours=1, workspace_id=None):
    """Query recent anomalies from InfluxDB"""
    
    if not INFLUX_TOKEN:
        print("❌ Error: INFLUX_TOKEN not found")
        return
    
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        query_api = client.query_api()
        
        # Build Flux query
        workspace_filter = f'|> filter(fn: (r) => r.workspace_id == "{workspace_id}")' if workspace_id else ''
        
        query = f'''
        from(bucket: "{ANOMALY_BUCKET}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r._measurement == "anomaly_detections")
          {workspace_filter}
          |> sort(columns: ["_time"], desc: true)
        '''
        
        print(f"\n📊 Querying anomalies from last {hours} hour(s)...")
        print(f"   Bucket: {ANOMALY_BUCKET}")
        print(f"   Organization: {INFLUX_ORG}")
        if workspace_id:
            print(f"   Workspace: {workspace_id}")
        
        tables = query_api.query(query)
        
        if not tables:
            print("\n❌ No anomalies found in the specified time range")
            print("\n💡 Possible reasons:")
            print("   • No anomalies detected yet (need 50+ data points)")
            print("   • Inference service just started")
            print("   • All predictions within normal range")
            return
        
        # Group results by time
        anomalies = {}
        for table in tables:
            for record in table.records:
                time_key = record.get_time().isoformat()
                if time_key not in anomalies:
                    anomalies[time_key] = {
                        "time": record.get_time(),
                        "workspace": record.values.get("workspace_id", "unknown"),
                        "anomaly_type": record.values.get("anomaly_type", "unknown"),
                        "severity_level": record.values.get("severity_level", "unknown"),
                        "fields": {}
                    }
                
                field_name = record.get_field()
                field_value = record.get_value()
                anomalies[time_key]["fields"][field_name] = field_value
        
        # Display results
        print(f"\n✅ Found {len(anomalies)} anomaly event(s)\n")
        print("=" * 100)
        
        for idx, (time_key, anomaly) in enumerate(sorted(anomalies.items(), reverse=True), 1):
            print(f"\n🔴 Anomaly #{idx}")
            print(f"   Time: {anomaly['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Workspace: {anomaly['workspace']}")
            print(f"   Type: {anomaly['anomaly_type']}")
            print(f"   Severity: {anomaly['severity_level'].upper()}")
            
            fields = anomaly['fields']
            if 'severity_score' in fields:
                print(f"   Score: {fields['severity_score']:.3f}")
            if 'alert_message' in fields:
                print(f"   Message: {fields['alert_message']}")
            if 'affected_features' in fields:
                print(f"   Affected: {fields['affected_features']}")
            
            # Show predictions vs actuals
            print("\n   📊 Sensor Values:")
            sensors = ['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']
            for sensor in sensors:
                actual_key = f'actual_{sensor}'
                predicted_key = f'predicted_{sensor}'
                deviation_key = f'deviation_{sensor}'
                
                if actual_key in fields and predicted_key in fields:
                    actual = fields[actual_key]
                    predicted = fields[predicted_key]
                    deviation = fields.get(deviation_key, actual - predicted)
                    
                    marker = "⚠️ " if deviation_key.replace('deviation_', '') in anomaly.get('anomaly_type', '') else "   "
                    print(f"   {marker}{sensor:8s}: Actual={actual:.3f}, Predicted={predicted:.3f}, Deviation={deviation:+.3f}")
            
            print("\n" + "-" * 100)
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error querying anomalies: {e}")


if __name__ == "__main__":
    import sys
    
    print("=" * 100)
    print("  ANOMALY BUCKET VIEWER - Check Logged Anomalies")
    print("=" * 100)
    
    # Parse arguments
    hours = 1
    workspace = None
    
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except:
            workspace = sys.argv[1]
    
    if len(sys.argv) > 2:
        workspace = sys.argv[2]
    
    query_anomalies(hours=hours, workspace_id=workspace)
    
    print("\n" + "=" * 100)
    print("\n💡 Usage:")
    print("   python check_anomalies.py           # Last 1 hour, all workspaces")
    print("   python check_anomalies.py 24        # Last 24 hours, all workspaces")
    print("   python check_anomalies.py cnc-mill-5-axis  # Last 1 hour, specific workspace")
    print("   python check_anomalies.py 24 cnc-mill-5-axis  # Last 24 hours, specific workspace")
    print("\n" + "=" * 100)
