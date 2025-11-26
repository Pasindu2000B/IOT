# python main.py

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from services.real_influx_streamer import RealInfluxStreamer
import threading
import os

app = FastAPI()


static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


streamer = RealInfluxStreamer(interval_seconds=10, lookback_minutes=60)


@app.get("/workspaces")
def get_available_workspaces():
    
    models = streamer.get_available_workspaces()
    return {
        "status": "success",
        "workspaces_with_models": models,
        "total_models": len(models)
    }

@app.get("/inference/status")
def get_inference_status():
   
    return {
        "status": "success",
        "interval_seconds": streamer.interval,
        "lookback_minutes": streamer.lookback_minutes,
        "available_models": streamer.get_available_workspaces(),
        "message": "Inference running directly from InfluxDB data"
    }

@app.get("/predict/{workspace_id}")
def get_latest_predictions(workspace_id: str):
    
    predictions = streamer.inference_service.get_latest_predictions(workspace_id)
    
    if predictions is None:
        return {
            "status": "error",
            "message": f"No predictions available for {workspace_id}. Wait for inference cycle."
        }
    
    return {
        "status": "success",
        "workspace_id": workspace_id,
        "predictions": predictions,
        "message": "Predictions show next 10 timesteps for all 6 sensor features"
    }

@app.get("/validate/{workspace_id}")
def validate_model(workspace_id: str):
   
    validation = streamer.validate_workspace_model(workspace_id)
    return validation

@app.on_event("startup")
def start_background_stream():
   
    thread = threading.Thread(target=streamer.start_stream, daemon=True)
    thread.start()
    print("[Main] Inference engine started - monitoring InfluxDB every 60 seconds")

@app.get("/", response_class=HTMLResponse)
def root():
    
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")
    if os.path.exists(dashboard_path):
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """
        <html>
            <body style="font-family: Arial; padding: 50px; text-align: center;">
                <h1>IOT Predictive Maintenance API</h1>
                <p>Dashboard not found. Please check if static/dashboard.html exists.</p>
                <p><a href="/docs">View API Documentation</a></p>
            </body>
        </html>
        """

@app.get("/validation", response_class=HTMLResponse)
def validation_page():
    
    validation_path = os.path.join(os.path.dirname(__file__), "static", "validation.html")
    if os.path.exists(validation_path):
        with open(validation_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """
        <html>
            <body style="font-family: Arial; padding: 50px; text-align: center;">
                <h1>Validation Page Not Found</h1>
                <p><a href="/">Back to Dashboard</a></p>
            </body>
        </html>
        """

@app.get("/api")
def api_info():
    
    return {
        "service": "IOT Predictive Maintenance Inference API",
        "version": "2.0",
        "mode": "Direct InfluxDB Inference",
        "endpoints": {
            "/": "Interactive dashboard",
            "/workspaces": "List workspaces with trained models",
            "/inference/status": "Get inference engine status",
            "/predict/{workspace_id}": "Get predictions for specific workspace",
            "/docs": "Interactive API documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



