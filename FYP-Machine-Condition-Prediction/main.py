# python main.py

from fastapi import FastAPI, Query
from services.real_influx_streamer import RealInfluxStreamer
from services.statistics_service import StatisticsService
from collections import deque
import threading

app = FastAPI()
streamer = RealInfluxStreamer(interval_seconds=10, max_points=360)
stats_service = StatisticsService()


@app.get("/workspaces")
def get_available_workspaces():
    """
    Return list of all currently monitored workspaces.
    """
    workspaces = streamer.get_available_workspaces()
    models = streamer.inference_service.get_available_workspaces()
    return {
        "status": "success",
        "active_workspaces": workspaces,
        "models_available": models,
        "total_active": len(workspaces),
        "total_models": len(models)
    }


@app.get("/sensor/means-history-db")
def get_means_history_from_db(workspace_id: str = Query(None, description="Specific workspace ID, or omit for all")):
    """
    Return recent mean values from MongoDB for a specific workspace or all workspaces.
    """
    data = streamer.get_recent_means_from_db(workspace_id=workspace_id)
    
    if workspace_id:
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "means_collected": len(data),
            "data": data
        }
    else:
        return {
            "status": "success",
            "workspaces": list(data.keys()) if isinstance(data, dict) else [],
            "data": data
        }

@app.on_event("startup")
def start_background_stream():
    """
    Start the 10-second fake data generator in the background.
    """
    thread = threading.Thread(target=streamer.start_stream, daemon=True)
    thread.start()
    print("Background data streaming process started.")

@app.get("/sensor/latest")
def get_latest_sensor_point(workspace_id: str = Query(None, description="Specific workspace ID")):
    """
    Return the most recent datapoint for a workspace or all workspaces.
    """
    if workspace_id:
        buffer = streamer.workspace_buffers.get(workspace_id, deque())
        latest = buffer[-1] if buffer else None
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "msg": "Latest data retrieved successfully",
            "data": latest
        }
    else:
        latest_all = {}
        for ws_id, buffer in streamer.workspace_buffers.items():
            latest_all[ws_id] = buffer[-1] if buffer else None
        return {
            "status": "success",
            "msg": "Latest data for all workspaces",
            "data": latest_all
        }

@app.get("/sensor/history")
def get_last_hour_points(workspace_id: str = Query(None, description="Specific workspace ID")):
    """
    Return the last hour of data points for a workspace or all workspaces.
    """
    data = streamer.get_last_360_points(workspace_id=workspace_id)
    
    if workspace_id:
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "points_collected": len(data),
            "data": data
        }
    else:
        return {
            "status": "success",
            "workspaces": list(data.keys()),
            "data": data
        }

@app.get("/sensor/hourly-mean")
def get_hourly_mean(workspace_id: str = Query(None, description="Specific workspace ID")):
    """
    Compute hourly mean for a specific workspace or all workspaces.
    """
    if workspace_id:
        data = streamer.get_last_360_points(workspace_id=workspace_id)
        if not data or len(data) < 360:
            return {
                "status": "error",
                "workspace_id": workspace_id,
                "msg": f"Not enough data points yet (need 360, have {len(data) if data else 0})."
            }
        mean_values = stats_service.compute_hourly_mean(data)
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "hourly_mean": mean_values
        }
    else:
        all_data = streamer.get_last_360_points()
        results = {}
        for ws_id, data in all_data.items():
            if data and len(data) >= 360:
                results[ws_id] = stats_service.compute_hourly_mean(data)
        return {
            "status": "success",
            "workspaces": list(results.keys()),
            "hourly_means": results
        }

@app.get("/sensor/means-history")
def get_means_history(workspace_id: str = Query(None, description="Specific workspace ID")):
    """
    Return the list of automatically calculated mean values.
    Note: This endpoint returns in-memory data, use /sensor/means-history-db for MongoDB data.
    """
    return {
        "status": "info",
        "msg": "In-memory tracking removed. Use /sensor/means-history-db instead."
    }

@app.get("/sensor/last-lookback")
def get_last_lookback(workspace_id: str = Query(None, description="Specific workspace ID")):
    """
    Retrieve the last 1200 mean values from MongoDB for a workspace or all workspaces.
    """
    data = streamer.get_last_lookback(workspace_id=workspace_id)
    
    if workspace_id:
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "means_collected": len(data),
            "data": data
        }
    else:
        return {
            "status": "success",
            "workspaces": list(data.keys()) if isinstance(data, dict) else [],
            "data": data
        }





