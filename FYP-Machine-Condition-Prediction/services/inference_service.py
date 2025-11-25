# services/inference_service.py

import numpy as np
import pandas as pd
import torch
import pickle
import os
import glob
from datetime import datetime
# MongoDB and email disabled for direct InfluxDB inference
# from bson import ObjectId
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail

class InferenceService:
    def __init__(self):
        # Define paths and device  
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)  # Go up from services/ to FYP-Machine-Condition-Prediction/
        self.base_dir = os.path.join(parent_dir, "FYP-Machine-Condition-Prediction")
        self.base_dir = os.path.abspath(self.base_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Storage for all workspace models and scalers
        self.models = {}  # {workspace_id: model}
        self.scalers = {}  # {workspace_id: scaler}
        self.model_timestamps = {}  # {workspace_id: timestamp}
        self.latest_predictions = {}  # {workspace_id: {"forecast": array, "timestamp": datetime}}
        
        # Load all available workspace models
        self._load_all_workspace_models()
        
        # MongoDB disabled - not needed for direct InfluxDB inference
        self.db = None
        self.users_collection = None
        self.workspaces_collection = None
    
    def _load_all_workspace_models(self):
        """Discover and load models for all available workspaces"""
        from transformers import PatchTSTForPrediction
        
        # Find all model directories
        model_pattern = os.path.join(self.base_dir, "model_*_*")
        all_model_dirs = glob.glob(model_pattern)
        
        if not all_model_dirs:
            print("[InferenceService] WARNING: No trained models found in", self.base_dir)
            return
        
        # Group by workspace
        workspace_models = {}
        for model_dir in all_model_dirs:
            # Extract workspace_id from: model_{workspace}_{timestamp}
            # Example: model_cnc-mill-5-axis_20251124_093154
            dir_name = os.path.basename(model_dir)
            
            # Remove 'model_' prefix
            name_parts = dir_name.replace('model_', '')
            
            # Split by underscore and remove last 2 parts (date_time timestamp)
            parts = name_parts.split('_')
            if len(parts) >= 3:
                # Last 2 parts are timestamp (YYYYMMDD_HHMMSS), rest is workspace name
                workspace_id = '_'.join(parts[:-2])
            else:
                # Fallback: use as-is
                workspace_id = name_parts
            
            if workspace_id not in workspace_models:
                workspace_models[workspace_id] = []
            workspace_models[workspace_id].append(model_dir)
        
        # Load latest model for each workspace
        print(f"[InferenceService] Discovered {len(workspace_models)} workspace(s)")
        
        for workspace_id, model_dirs in workspace_models.items():
            try:
                # Get latest model
                latest_model_dir = max(model_dirs, key=os.path.getctime)
                
                # Find corresponding scaler
                scaler_pattern = os.path.join(self.base_dir, f"scaler_{workspace_id}_*.pkl")
                scaler_files = glob.glob(scaler_pattern)
                
                if not scaler_files:
                    print(f"[InferenceService] WARNING: No scaler found for {workspace_id}")
                    continue
                
                latest_scaler = max(scaler_files, key=os.path.getctime)
                
                # Load scaler
                with open(latest_scaler, "rb") as f:
                    scaler = pickle.load(f)
                
                # Load model
                model = PatchTSTForPrediction.from_pretrained(latest_model_dir)
                model.to(self.device)
                model.eval()
                
                # Store
                self.models[workspace_id] = model
                self.scalers[workspace_id] = scaler
                self.model_timestamps[workspace_id] = os.path.getctime(latest_model_dir)
                
                print(f"[InferenceService] Loaded model for workspace: {workspace_id}")
                print(f"                    Model: {os.path.basename(latest_model_dir)}")
                
            except Exception as e:
                print(f"[InferenceService] Failed to load model for {workspace_id}: {e}")
        
        print(f"[InferenceService] Total models loaded: {len(self.models)}")
    
    def reload_workspace_models(self):
        """Check for new or updated models and reload if necessary"""
        print("[InferenceService] Checking for new/updated workspace models...")
        self._load_all_workspace_models()
    
    def get_available_workspaces(self):
        """Return list of workspaces with loaded models"""
        return list(self.models.keys())

    def run_inference(self, workspace_id, influx_data):
        """
        Run the full inference pipeline: preprocess data, feed to model, detect anomalies, send email.
        Args:
            workspace_id (str): The workspace to run inference for
            influx_data (pandas DataFrame): Raw sensor data from InfluxDB with columns [current, accX, accY, accZ, tempA, tempB]
        Returns: forecast (np.array), alerts (dict with status and message).
        """
        # Check if model exists for this workspace
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
        
        # Step 1: Use raw InfluxDB data directly (already has correct columns)
        raw_data = influx_data[['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']]
        
        # Step 2: Scale data
        scaled_data = scaler.transform(raw_data)
        scaled_data = np.clip(scaled_data, 0, 1)
        
        # Step 3: Reshape for model (use last 50 points for reduced model)
        context_length = 50  # Must match trained model context_length
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
        
        # Step 5: Anomaly detection (IOT 6 features)
        num_features = 6
        horizon = 10  # Reduced prediction horizon
        feature_names = ['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']
        at_risk_features = []
        
        for feature_idx in range(num_features):
            forecast_feature = forecast[:, feature_idx] if forecast.ndim > 1 else forecast
            max_lookback = np.max(scaled_data[-context_length:, feature_idx])
            min_lookback = np.min(scaled_data[-context_length:, feature_idx])
            num_exceeding_max = np.sum(forecast_feature > max_lookback)
            num_below_min = np.sum(forecast_feature < min_lookback)
            total_anomalous = num_exceeding_max + num_below_min
            anomaly_percentage = (total_anomalous / horizon) * 100
            
            print(f"[Inference] Feature {feature_names[feature_idx]}: Anomaly % = {anomaly_percentage:.2f}%")
            
            if anomaly_percentage >= 30:  # Alert if 30% or more anomalous
                at_risk_features.append(feature_names[feature_idx])
        
        # Determine alert message
        current_time = datetime.now().isoformat()
        if at_risk_features:
            overall_at_risk = True
            alert_message = f"Machine at Risk: Stay alert on {', '.join(at_risk_features)} (Checked at: {current_time})"
        else:
            overall_at_risk = False
            alert_message = f"Machine Condition Normal (Checked at: {current_time})"
        
        print(f"[Inference] Alert for {workspace_id}: '{alert_message}'")
        
        # Step 7: Send email if at risk (from notebook Cell 10)
        # if overall_at_risk:
        #     to_email = "aadhiganegoda@gmail.com"
        #     from_email = "thisupun3@gmail.com"
        #     subject = "Machine Condition Alert"
        #     body = alert_message
            
        #     sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        #     if not sendgrid_api_key:
        #         print("[Inference] SendGrid API Key not found.")
        #     else:
        #         message = Mail(from_email=from_email, to_emails=to_email, subject=subject, plain_text_content=body)
        #         try:
        #             sg = SendGridAPIClient(sendgrid_api_key)
        #             response = sg.send(message)
        #             print(f"[Inference] Email sent successfully. Status code: {response.status_code}")
        #         except Exception as e:
        #             print(f"[Inference] Failed to send email: {str(e)}")
        # else:
        #     print("[Inference] No email sent (machine condition normal).")
        
        if overall_at_risk:
            # Get recipient emails from workspace members
            recipient_emails = self.get_emails_for_workspace(workspace_id)
            if not recipient_emails:
                print(f"[Inference] No emails found for workspace {workspace_id}. Skipping email.")
            else:
                from_email = "thisupun3@gmail.com"
                subject = "Machine Condition Alert"
                body = alert_message
                
                sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
                if not sendgrid_api_key:
                    print("[Inference] SendGrid API Key not found.")
                else:
                    for to_email in recipient_emails:
                        message = Mail(from_email=from_email, to_emails=to_email, subject=subject, plain_text_content=body)
                        try:
                            sg = SendGridAPIClient(sendgrid_api_key)
                            response = sg.send(message)
                            print(f"[Inference] Email sent to {to_email}. Status code: {response.status_code}")
                        except Exception as e:
                            print(f"[Inference] Failed to send email to {to_email}: {str(e)}")
        else:
            print("[Inference] No email sent (machine condition normal).")
        
        # Store the latest predictions with timestamp
        self.latest_predictions[workspace_id] = {
            "forecast": forecast.tolist(),  # Convert numpy array to list for JSON serialization
            "timestamp": current_time,
            "alert_message": alert_message,
            "at_risk": overall_at_risk,
            "at_risk_features": at_risk_features
        }
        
        return forecast, {"status": "success", "message": alert_message}

    def get_emails_for_workspace(self, workspace_id):
        """
        Retrieve emails of users associated with the given workspace_id (which is the _id of the workspace document).
        """
        if not self.workspaces_collection or not self.users_collection:
            print("[Inference] Database collections not available.")
            return []
                   
        # Convert workspace_id to ObjectId and query by _id
        try:
            workspace_oid = ObjectId(workspace_id)
        except Exception as e:
            print(f"[Inference] Invalid workspace_id format: {workspace_id}")
            return []
            
        # Query workspaces collection for the workspace_id
        workspace_doc = self.workspaces_collection.find_one({"_id": workspace_oid})
        if not workspace_doc or "members" not in workspace_doc:
            print(f"[Inference] Workspace {workspace_id} not found or has no members.")
            return []
        
        emails = []
        for member in workspace_doc["members"]:
            user_id = member.get("user")  # Assuming 'user' field holds user ID
            if user_id:
                # Query users collection for email
                user_doc = self.users_collection.find_one({"_id": user_id})  # Assuming _id is the user ID
                if user_doc and "email" in user_doc:
                    emails.append(user_doc["email"])
                else:
                    print(f"[Inference] User {user_id} not found or has no email.")
            
        return emails
    
    def get_latest_predictions(self, workspace_id):
        """
        Get the most recent predictions for a workspace.
        Returns dict with forecast array, timestamp, and alert info.
        """
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
            "alert_status": "At Risk" if prediction_data["at_risk"] else "Normal",
            "alert_message": prediction_data["alert_message"],
            "at_risk_features": prediction_data["at_risk_features"],
            "predictions": predictions_by_feature,
            "prediction_horizon": len(forecast),
            "note": "Predictions show next 10 timesteps (~20 seconds at 2s/sample)"
        }
    
    def validate_model(self, workspace_id, influx_data):
        """
        Validate model by comparing predictions against actual future data.
        
        Args:
            workspace_id: The workspace to validate
            influx_data: DataFrame with at least context_length + prediction_length rows
            
        Returns:
            dict with predictions, actual values, and error metrics
        """
        if workspace_id not in self.models:
            return {"status": "error", "message": f"No model for {workspace_id}"}
        
        context_length = 50
        prediction_length = 10
        
        if len(influx_data) < context_length + prediction_length:
            return {"status": "error", "message": f"Need at least {context_length + prediction_length} data points"}
        
        model = self.models[workspace_id]
        scaler = self.scalers[workspace_id]
        feature_names = ['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']
        
        # Take context from the data (excluding last prediction_length points)
        context_data = influx_data[-(context_length + prediction_length):-prediction_length]
        actual_future = influx_data[-prediction_length:]
        
        # Scale context
        raw_context = context_data[feature_names].values
        scaled_context = scaler.transform(raw_context)
        scaled_context = np.clip(scaled_context, 0, 1)
        
        # Get predictions
        input_tensor = torch.tensor(scaled_context.reshape(1, context_length, 6), dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            outputs = model(past_values=input_tensor)
            predictions = outputs.prediction_outputs.squeeze().cpu().numpy()
        
        # Scale actual future data
        actual_scaled = scaler.transform(actual_future[feature_names].values)
        actual_scaled = np.clip(actual_scaled, 0, 1)
        
        # Calculate error metrics for each feature
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