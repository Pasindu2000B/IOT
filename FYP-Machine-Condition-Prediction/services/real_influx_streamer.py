# services/real_influx_streamer.py

import time
from collections import deque
from influxdb_client import InfluxDBClient
from services.statistics_service import StatisticsService
from services.inference_service import InferenceService
from configs.mongodb_config import get_database
from configs.mongodb_config import influx_url, influx_token, influx_org, influx_bucket

class RealInfluxStreamer:
    def __init__(self, interval_seconds=10, max_points=360):
        self.influx_client = InfluxDBClient(
            url=influx_url, 
            token=influx_token, 
            org=influx_org
        )
        self.influx_bucket = influx_bucket

        # Track multiple workspaces
        self.workspace_buffers = {}  # {workspace_id: deque}
        self.workspace_counters = {}  # {workspace_id: int}
        self.workspace_last_times = {}  # {workspace_id: timestamp}
        
        self.interval = interval_seconds
        self.max_points = max_points
        
        self.stats_service = StatisticsService()
        self.db = get_database()
        
        # Initialize inference service (loads all workspace models)
        self.inference_service = InferenceService()
        
        print(f"[RealInfluxStreamer] Initialized for multi-workspace monitoring")
        print(f"[RealInfluxStreamer] Available workspaces: {self.inference_service.get_available_workspaces()}")

    def _get_available_workspaces_from_influx(self):
        """Query InfluxDB to discover all active workspaces"""
        query = f'''
        from(bucket: "{self.influx_bucket}")
          |> range(start: -1h)
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

    def start_stream(self):
        """
        Continuously poll InfluxDB for new data every 10 seconds.
        Monitors all workspaces dynamically.
        Every 360 points per workspace, compute mean, insert to MongoDB, retrieve lookback, run inference.
        """
        print("[RealInfluxStreamer] Starting multi-workspace streaming...")
        
        while True:
            # Discover active workspaces
            active_workspaces = self._get_available_workspaces_from_influx()
            
            if not active_workspaces:
                print("[RealInfluxStreamer] No active workspaces found in InfluxDB")
                time.sleep(self.interval)
                continue
            
            # Process each workspace
            for workspace_id in active_workspaces:
                self._process_workspace(workspace_id)
            
            time.sleep(self.interval)
    
    def _process_workspace(self, workspace_id):
        """Process data for a single workspace"""
        # Initialize buffer and counter if new workspace
        if workspace_id not in self.workspace_buffers:
            self.workspace_buffers[workspace_id] = deque(maxlen=self.max_points)
            self.workspace_counters[workspace_id] = 0
            print(f"[RealInfluxStreamer] New workspace detected: {workspace_id}")
        
        # Query InfluxDB for the latest data point
        timestamp_query = f'''
        from(bucket: "{self.influx_bucket}")
          |> range(start: -2m)
          |> filter(fn: (r) => r._measurement == "sensor_data")
          |> filter(fn: (r) => r.workspace_id == "{workspace_id}")
          |> keep(columns: ["_time"])
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 1)
        '''

        try:
            timestamp_result = self.influx_client.query_api().query(timestamp_query)
            latest_time = None
            for table in timestamp_result:
                for record in table.records:
                    latest_time = record.get_time()

            if latest_time and latest_time != self.workspace_last_times.get(workspace_id):
                # Fetch full data for the latest timestamp
                full_query = f'''
                from(bucket: "{self.influx_bucket}")
                  |> range(start: -5m)
                  |> filter(fn: (r) => r["_measurement"] == "sensor_data")
                  |> filter(fn: (r) => r["workspace_id"] == "{workspace_id}")
                  |> pivot(
                      rowKey: ["_time"],
                      columnKey: ["_field"],
                      valueColumn: "_value"
                  )
                  |> sort(columns: ["_time"], desc: false)
                '''

                full_data = self.influx_client.query_api().query(full_query)

                for table in full_data:
                    for record in table.records:
                        if record["_time"] == latest_time:
                            new_point = {
                                "timestamp": record.get_time().isoformat(),
                                "current": float(record.values.get("current", 0)),
                                "accX": float(record.values.get("accX", 0)),
                                "accY": float(record.values.get("accY", 0)),
                                "accZ": float(record.values.get("accZ", 0)),
                                "tempA": float(record.values.get("tempA", 0)),
                                "tempB": float(record.values.get("tempB", 0)),
                                "workspace_id": workspace_id,
                            }
                            self.workspace_buffers[workspace_id].append(new_point)
                            self.workspace_counters[workspace_id] += 1
                            print(f"[RealInfluxStreamer] {workspace_id}: New data point (buffer: {len(self.workspace_buffers[workspace_id])})")
                            break
                        
                self.workspace_last_times[workspace_id] = latest_time
            
        except Exception as e:
            print(f"[RealInfluxStreamer] Error querying {workspace_id}: {e}")
            return

        # Check if we have 360 points for this workspace
        if self.workspace_counters[workspace_id] >= 360:
            self._run_inference_for_workspace(workspace_id)
            self.workspace_counters[workspace_id] = 0
    
    def _run_inference_for_workspace(self, workspace_id):
        """Run inference for a specific workspace"""
        print(f"[RealInfluxStreamer] Running inference for {workspace_id}...")
        
        data = list(self.workspace_buffers[workspace_id])
        mean_values = self.stats_service.compute_hourly_mean(data)
        
        if mean_values and self.db:
            collection = self.db[f"hourly_means_{workspace_id}"]
            
            try:
                mean_values["workspace_id"] = workspace_id
                collection.insert_one(mean_values)
                print(f"[RealInfluxStreamer] {workspace_id}: Mean inserted into MongoDB")

                # Retrieve lookback
                last_lookback = list(collection.find({"workspace_id": workspace_id}).sort("_id", -1).limit(1200))
                print(f"[RealInfluxStreamer] {workspace_id}: Retrieved lookback: {len(last_lookback)} items")

                # Run inference
                forecast, alerts = self.inference_service.run_inference(workspace_id, last_lookback)
                
                if forecast is not None:
                    print(f"[RealInfluxStreamer] {workspace_id}: Forecast shape: {forecast.shape}")
                    print(f"[RealInfluxStreamer] {workspace_id}: Alerts: {alerts}")
                
                # Clear buffer
                self.workspace_buffers[workspace_id].clear()
                print(f"[RealInfluxStreamer] {workspace_id}: Buffer cleared")

            except Exception as e:
                print(f"[RealInfluxStreamer] Error in MongoDB/inference for {workspace_id}: {e}")
    
    def get_last_360_points(self, workspace_id=None):
        """Return the rolling window for a specific workspace or all workspaces"""
        if workspace_id:
            return list(self.workspace_buffers.get(workspace_id, []))
        return {ws: list(buffer) for ws, buffer in self.workspace_buffers.items()}
    
    def get_recent_means_from_db(self, workspace_id=None, limit=360):
        """Retrieve recent means from MongoDB for a specific workspace or all workspaces"""
        if not self.db:
            return []
        
        if workspace_id:
            collection = self.db[f"hourly_means_{workspace_id}"]
            return list(collection.find().sort("_id", -1).limit(limit))
        else:
            # Return means for all workspaces
            all_means = {}
            for ws_id in self.workspace_buffers.keys():
                collection = self.db[f"hourly_means_{ws_id}"]
                all_means[ws_id] = list(collection.find().sort("_id", -1).limit(limit))
            return all_means
    
    def get_last_lookback(self, workspace_id=None):
        """Return the last 1200 retrieved means for a workspace or all workspaces"""
        if not self.db:
            return []
        
        if workspace_id:
            collection = self.db[f"hourly_means_{workspace_id}"]
            return list(collection.find({"workspace_id": workspace_id}).sort("_id", -1).limit(1200))
        else:
            # Return lookback for all workspaces
            all_lookback = {}
            for ws_id in self.workspace_buffers.keys():
                collection = self.db[f"hourly_means_{ws_id}"]
                all_lookback[ws_id] = list(collection.find({"workspace_id": ws_id}).sort("_id", -1).limit(1200))
            return all_lookback
    
    def get_available_workspaces(self):
        """Return list of currently monitored workspaces"""
        return list(self.workspace_buffers.keys())


