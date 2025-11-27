# services/inference_service.py

import numpy as np
import pandas as pd
import torch
import pickle
import os
import glob
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


class InferenceService:
    def __init__(self):
        
        
        # Get Directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)  
        self.base_dir = os.path.join(parent_dir, "FYP-Machine-Condition-Prediction")
        self.base_dir = os.path.abspath(self.base_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        
        self.models = {}  # {workspace_id: model}
        self.scalers = {}  # {workspace_id: scaler}
        self.model_timestamps = {}  # {workspace_id: timestamp}
        self.latest_predictions = {}  # {workspace_id: {"forecast": array, "timestamp": datetime}}
        
    
        self._load_all_workspace_models()
        
        self.influx_url = os.getenv("INFLUX_URL", "http://142.93.220.152:8086")
        self.influx_token = os.getenv("INFLUX_TOKEN")
        self.influx_org = os.getenv("INFLUX_ORG", "Ruhuna_Eng")
        self.influx_bucket = os.getenv("INFLUX_BUCKET", "New_Sensor")
    
        
    
    def _load_all_workspace_models(self):
        
        from transformers import PatchTSTForPrediction
        
        # Find all model directories
        model_pattern = os. path.join(self.base_dir, "model_*_*")
        all_model_dirs = glob.glob(model_pattern)
        
        if not all_model_dirs:
            print("[InferenceService] WARNING: No trained models found in", self.base_dir)
            return
        
        # Group by workspace
        workspace_models = {}
        for model_dir in all_model_dirs:
            
            dir_name = os.path.basename(model_dir)
            
            
            name_parts = dir_name.replace('model_', '')
            
            
            parts = name_parts.split('_')
            if len(parts) >= 3:
                
                workspace_id = '_'.join(parts[:-2])
            else:
                
                workspace_id = name_parts
            
            if workspace_id not in workspace_models:
                workspace_models[workspace_id] = []
            workspace_models[workspace_id].append(model_dir)
        
        
        print(f"[InferenceService] Discovered {len(workspace_models)} workspace(s)")
        
        for workspace_id, model_dirs in workspace_models.items():
            try:
                
                latest_model_dir = max(model_dirs, key=os.path.getctime)
                
               
                scaler_pattern = os.path.join(self.base_dir, f"scaler_{workspace_id}_*.pkl")
                scaler_files = glob.glob(scaler_pattern)
                
                if not scaler_files:
                    print(f"[InferenceService] WARNING: No scaler found for {workspace_id}")
                    continue
                
                latest_scaler = max(scaler_files, key=os.path.getctime)
                
                
                with open(latest_scaler, "rb") as f:
                    scaler = pickle.load(f)
                
            
                model = None
                
                
                try:
                    model = PatchTSTForPrediction.from_pretrained(latest_model_dir)
                except:
                    
                    pt_file = os.path.join(latest_model_dir, "pytorch_model.bin")
                    if os.path.exists(pt_file):
                        import torch
                        model = torch.load(pt_file, map_location=self.device, weights_only=False)
                    else:
                        raise Exception("No valid model file found")
                
                model.to(self.device)
                model.eval()
                
            
                self.models[workspace_id] = model
                self.scalers[workspace_id] = scaler
                self.model_timestamps[workspace_id] = os.path.getctime(latest_model_dir)
                
                print(f"[InferenceService] Loaded model for workspace: {workspace_id}")
                print(f"                    Model: {os.path.basename(latest_model_dir)}")
                
            except Exception as e:
                print(f"[InferenceService] Failed to load model for {workspace_id}: {e}")
        
        print(f"[InferenceService] Total models loaded: {len(self.models)}")
    
    def reload_workspace_models(self):
       
        print("[InferenceService] Checking for new/updated workspace models...")
        self._load_all_workspace_models()
    
    def get_available_workspaces(self):
       
        return list(self.models.keys())

    def run_inference(self, workspace_id, influx_data):
      
       
        if workspace_id not in self.models:
            print(f"[Inference] No model loaded for workspace: {workspace_id}")
            print(f"[Inference] Available workspaces: {list(self.models.keys())}")
            return None, {"status": "error", "message": f"No model found for workspace {workspace_id}"}
        
        if len(influx_data) < 50:  # Minimum required for reduced model
            print(f"[Inference] Not enough data for {workspace_id} (need 50, got {len(influx_data)}). Skipping inference.")
            return None, {"status": "error", "message": "Not enough data for inference."}
        
        print(f"[Inference] Running inference for workspace: {workspace_id} with {len(influx_data)} data points")
        
        # Get model and scaler for this workspace
        model = self.models[workspace_id]
        scaler = self.scalers[workspace_id]
        

        raw_data = influx_data[['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']]
        
    
        scaled_data = scaler.transform(raw_data)
        scaled_data = np.clip(scaled_data, 0, 1)
        
    
        context_length = 1800 
        if len(scaled_data) < context_length:
            print(f"[Inference] Not enough data after processing (need {context_length}, got {len(scaled_data)})")
            return None, {"status": "error", "message": f"Need at least {context_length} data points"}
        
        # Take the most recent context_length points
        model_input = scaled_data[-context_length:].reshape(1, context_length, 6)
        input_tensor = torch.tensor(model_input, dtype=torch.float32).to(self.device)
        
        # Step 4: Feed to model and get forecast
        with torch.no_grad():
            outputs = model(past_values=input_tensor)
            forecast = outputs.prediction_outputs.squeeze().cpu().numpy()
        
        # Store the latest predictions with timestamp
        current_time = datetime.now().isoformat()
        self.latest_predictions[workspace_id] = {
            "forecast": forecast.tolist(),  # Convert numpy array to list for JSON serialization
            "timestamp": current_time
        }
        
        return forecast, {"status": "success"}

    def get_latest_predictions(self, workspace_id):
        
        if workspace_id not in self.latest_predictions:
            return None
        
        prediction_data = self.latest_predictions[workspace_id]
        
        # Format predictions nicely
        forecast = np.array(prediction_data["forecast"])
        feature_names = ['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']
        
        # Create structured output
        predictions_by_feature = {}
        for idx, feature in enumerate(feature_names):
            predictions_by_feature[feature] = forecast[:, idx].tolist()
        
        return {
            "timestamp": prediction_data["timestamp"],
            "predictions": predictions_by_feature,
            "prediction_horizon": len(forecast),
            "note": "Predictions show next 60 minutes (~1800 timesteps at 2s/sample)"
        }
    
    def validate_model(self, workspace_id, influx_data):
      
        if workspace_id not in self.models:
            return {"status": "error", "message": f"No model for {workspace_id}"}
        
        context_length = 50
        prediction_length = 10
        
        if len(influx_data) < context_length + prediction_length:
            return {"status": "error", "message": f"Need at least {context_length + prediction_length} data points"}
        
        model = self.models[workspace_id]
        scaler = self.scalers[workspace_id]
        feature_names = ['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']
        
       
        context_data = influx_data[-(context_length + prediction_length):-prediction_length]
        actual_future = influx_data[-prediction_length:]
        
        
        raw_context = context_data[feature_names].values
        scaled_context = scaler.transform(raw_context)
        scaled_context = np.clip(scaled_context, 0, 1)
        
       
        input_tensor = torch.tensor(scaled_context.reshape(1, context_length, 6), dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            outputs = model(past_values=input_tensor)
            predictions = outputs.prediction_outputs.squeeze().cpu().numpy()
        
       
        actual_scaled = scaler.transform(actual_future[feature_names].values)
        actual_scaled = np.clip(actual_scaled, 0, 1)
        
        
        metrics = {}
        predictions_by_feature = {}
        actuals_by_feature = {}
        
        for idx, feature in enumerate(feature_names):
            pred = predictions[:, idx]
            actual = actual_scaled[:, idx]
            
            # Calculate metrics
            mae = np.mean(np.abs(pred - actual))
            rmse = np.sqrt(np.mean((pred - actual) ** 2))
            mape = np.mean(np.abs((actual - pred) / (actual + 1e-8))) * 100
            
            metrics[feature] = {
                "MAE": float(mae),
                "RMSE": float(rmse),
                "MAPE": float(mape)
            }
            
            predictions_by_feature[feature] = pred.tolist()
            actuals_by_feature[feature] = actual.tolist()
        
        # Overall accuracy (average MAPE)
        avg_mape = np.mean([m["MAPE"] for m in metrics.values()])
        accuracy = max(0, 100 - avg_mape)
        
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "predictions": predictions_by_feature,
            "actuals": actuals_by_feature,
            "metrics": metrics,
            "overall_accuracy": float(accuracy),
            "note": "Validation compares model predictions against actual future values"
        }
