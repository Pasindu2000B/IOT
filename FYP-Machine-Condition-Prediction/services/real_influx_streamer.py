# services/real_influx_streamer.py

import time
import pandas as pd
from influxdb_client import InfluxDBClient
from services.inference_service import InferenceService
from configs.mongodb_config import influx_url, influx_token, influx_org, influx_bucket

class RealInfluxStreamer:
    def __init__(self, interval_seconds=60, lookback_minutes=10):
        """
        Initialize streamer to directly fetch data from InfluxDB and run inference.
        
        Args:
            interval_seconds: How often to run inference (default: 60 seconds)
            lookback_minutes: How much historical data to fetch for inference (default: 10 minutes)
        """
        self.influx_client = InfluxDBClient(
            url=influx_url, 
            token=influx_token, 
            org=influx_org
        )
        self.influx_bucket = influx_bucket
        self.interval = interval_seconds
        self.lookback_minutes = lookback_minutes
        
        # Initialize inference service (loads all workspace models)
        self.inference_service = InferenceService()
        
        print(f"[RealInfluxStreamer] Initialized for direct InfluxDB inference")
        print(f"[RealInfluxStreamer] Inference interval: {interval_seconds}s, Lookback: {lookback_minutes}min")
        print(f"[RealInfluxStreamer] Available workspaces: {self.inference_service.get_available_workspaces()}")

    def _get_available_workspaces_from_influx(self):
        """Query InfluxDB to discover all active workspaces"""
        query = f'''
        from(bucket: "{self.influx_bucket}")
          |> range(start: -{self.lookback_minutes}m)
          |> filter(fn: (r) => r._measurement == "sensor_data")
          |> keep(columns: ["workspace_id"])
          |> distinct(column: "workspace_id")
        '''
        
        try:
            result = self.influx_client.query_api().query(query)
            workspaces = set()
            for table in result:
                for record in table.records:
                    workspace_id = record.values.get('workspace_id')
                    if workspace_id:
                        workspaces.add(workspace_id)
            return list(workspaces)
        except Exception as e:
            print(f"[RealInfluxStreamer] Error discovering workspaces: {e}")
            return []
    
    def _fetch_workspace_data(self, workspace_id):
        """
        Fetch raw sensor data directly from InfluxDB for a workspace.
        Returns pandas DataFrame with columns: [timestamp, current, accX, accY, accZ, tempA, tempB]
        """
        query = f'''
        from(bucket: "{self.influx_bucket}")
          |> range(start: -{self.lookback_minutes}m)
          |> filter(fn: (r) => r._measurement == "sensor_data")
          |> filter(fn: (r) => r.workspace_id == "{workspace_id}")
          |> pivot(
              rowKey: ["_time"],
              columnKey: ["_field"],
              valueColumn: "_value"
          )
          |> sort(columns: ["_time"], desc: false)
        '''
        
        try:
            result = self.influx_client.query_api().query(query)
            
            data_points = []
            for table in result:
                for record in table.records:
                    data_points.append({
                        "timestamp": record.get_time(),
                        "current": float(record.values.get("current", 0)),
                        "accX": float(record.values.get("accX", 0)),
                        "accY": float(record.values.get("accY", 0)),
                        "accZ": float(record.values.get("accZ", 0)),
                        "tempA": float(record.values.get("tempA", 0)),
                        "tempB": float(record.values.get("tempB", 0)),
                    })
            
            if not data_points:
                print(f"[RealInfluxStreamer] No data found for {workspace_id}")
                return None
            
            df = pd.DataFrame(data_points)
            print(f"[RealInfluxStreamer] Fetched {len(df)} data points for {workspace_id}")
            return df
            
        except Exception as e:
            print(f"[RealInfluxStreamer] Error fetching data for {workspace_id}: {e}")
            return None

    def start_stream(self):
        """
        Continuously poll InfluxDB and run inference every interval.
        Fetches data directly from InfluxDB without MongoDB buffer.
        """
        print(f"[RealInfluxStreamer] Starting direct InfluxDB inference (interval: {self.interval}s)...")
        
        while True:
            try:
                # Discover active workspaces
                active_workspaces = self._get_available_workspaces_from_influx()
                
                if not active_workspaces:
                    print("[RealInfluxStreamer] No active workspaces found in InfluxDB")
                    time.sleep(self.interval)
                    continue
                
                print(f"[RealInfluxStreamer] Active workspaces: {active_workspaces}")
                
                # Process each workspace
                for workspace_id in active_workspaces:
                    # Check if model exists for this workspace
                    if workspace_id not in self.inference_service.models:
                        print(f"[RealInfluxStreamer] No model loaded for {workspace_id}, skipping...")
                        continue
                    
                    # Fetch data directly from InfluxDB
                    sensor_data = self._fetch_workspace_data(workspace_id)
                    
                    if sensor_data is None or len(sensor_data) < 50:
                        print(f"[RealInfluxStreamer] Insufficient data for {workspace_id} (need 50 points)")
                        continue
                    
                    # Run inference directly with InfluxDB data
                    forecast, alerts = self.inference_service.run_inference(workspace_id, sensor_data)
                    
                    if forecast is not None:
                        print(f"[RealInfluxStreamer] {workspace_id}: Forecast shape: {forecast.shape}")
                        print(f"[RealInfluxStreamer] {workspace_id}: {alerts['message']}")
                    
            except Exception as e:
                print(f"[RealInfluxStreamer] Error in stream loop: {e}")
            
            
            # Wait before next inference cycle
            time.sleep(self.interval)
    
    def get_available_workspaces(self):
        """Return list of available workspaces with loaded models"""
        return self.inference_service.get_available_workspaces()

