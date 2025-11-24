# services/inference_service.py

import numpy as np
import pandas as pd
import torch
import pickle
import os
import glob
from bson import ObjectId
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from configs.mongodb_config import get_database, workspace_id

class InferenceService:
    def __init__(self):
        # Define paths and device
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.join(current_dir, "..", "AI-Model-Artifacts")
        self.base_dir = os.path.abspath(self.base_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Storage for all workspace models and scalers
        self.models = {}  # {workspace_id: model}
        self.scalers = {}  # {workspace_id: scaler}
        self.model_timestamps = {}  # {workspace_id: timestamp}
        
        # Load all available workspace models
        self._load_all_workspace_models()
        
        # MongoDB connection
        self.db = get_database()
        self.users_collection = self.db["users"] if self.db else None
        self.workspaces_collection = self.db["workspaces"] if self.db else None
    
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
            dir_name = os.path.basename(model_dir)
            parts = dir_name.split('_')
            if len(parts) >= 3:
                # Handle workspace names with hyphens (e.g., lathe-1-spindle)
                workspace_id = '_'.join(parts[1:-1])
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
                
                print(f"[InferenceService] ✓ Loaded model for workspace: {workspace_id}")
                print(f"                    Model: {os.path.basename(latest_model_dir)}")
                
            except Exception as e:
                print(f"[InferenceService] ✗ Failed to load model for {workspace_id}: {e}")
        
        print(f"[InferenceService] Total models loaded: {len(self.models)}")
    
    def reload_workspace_models(self):
        """Check for new or updated models and reload if necessary"""
        print("[InferenceService] Checking for new/updated workspace models...")
        self._load_all_workspace_models()
    
    def get_available_workspaces(self):
        """Return list of workspaces with loaded models"""
        return list(self.models.keys())

    def run_inference(self, workspace_id, retrieved_docs):
        """
        Run the full inference pipeline: preprocess data, feed to model, detect anomalies, update DB, send email.
        Args:
            workspace_id (str): The workspace to run inference for
            retrieved_docs (list of dicts from MongoDB, last 1200).
        Returns: forecast (np.array), alerts (dict with status and message).
        """
        # Check if model exists for this workspace
        if workspace_id not in self.models:
            print(f"[Inference] No model loaded for workspace: {workspace_id}")
            print(f"[Inference] Available workspaces: {list(self.models.keys())}")
            return None, {"status": "error", "message": f"No model found for workspace {workspace_id}"}
        
        if len(retrieved_docs) < 1200:
            print(f"[Inference] Not enough data for {workspace_id} (need 1200, got {len(retrieved_docs)}). Skipping inference.")
            return None, {"status": "error", "message": "Not enough data for inference."}
        
        print(f"[Inference] Running inference for workspace: {workspace_id}")
        
        # Get model and scaler for this workspace
        model = self.models[workspace_id]
        scaler = self.scalers[workspace_id]
        
        # Step 1: Extract features (IOT format: 6 features)
        raw_data = pd.DataFrame([
            [doc['current_mean'], doc['accX_mean'], doc['accY_mean'], 
             doc['accZ_mean'], doc['tempA_mean'], doc['tempB_mean']]
            for doc in retrieved_docs
        ], columns=['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB'])
        
        # Step 2: Scale data
        scaled_data = scaler.transform(raw_data)
        scaled_data = np.clip(scaled_data, 0, 1)
        
        # Step 3: Reshape for model (IOT model expects 6 features)
        model_input = scaled_data.reshape(1, 1200, 6)
        input_tensor = torch.tensor(model_input, dtype=torch.float32).to(self.device)
        
        # Step 4: Feed to model and get forecast
        with torch.no_grad():
            outputs = model(past_values=input_tensor)
            forecast = outputs.prediction_outputs.squeeze().cpu().numpy()
        
        # Step 5: Anomaly detection (IOT 6 features)
        num_features = 6
        horizon = 240
        feature_names = ['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']
        at_risk_features = []
        
        for feature_idx in range(num_features):
            forecast_feature = forecast[:, feature_idx]
            max_lookback = np.max(scaled_data[:, feature_idx])
            min_lookback = np.min(scaled_data[:, feature_idx])
            num_exceeding_max = np.sum(forecast_feature > max_lookback)
            num_below_min = np.sum(forecast_feature < min_lookback)
            total_anomalous = num_exceeding_max + num_below_min
            anomaly_percentage = (total_anomalous / horizon) * 100
            
            print(f"[Inference] Feature {feature_idx}: Anomaly % = {anomaly_percentage:.2f}%")
            
            if anomaly_percentage >= -30:
                at_risk_features.append(feature_names[feature_idx])
        
        # Determine alert message
        current_time = datetime.now().isoformat()
        if at_risk_features:
            overall_at_risk = True
            alert_message = f"Machine at Risk: Stay alert on {', '.join(at_risk_features)} (Checked at: {current_time})"
        else:
            overall_at_risk = False
            alert_message = f"Machine Condition Normal (Checked at: {current_time})"
        
        # Step 6: Update MongoDB with alert
        if self.db:
            collection = self.db[f"hourly_means_{workspace_id}"]
            latest_doc = collection.find_one(sort=[("_id", -1)])
            if latest_doc:
                collection.update_one(
                    {"_id": latest_doc["_id"]},
                    {"$set": {"alert_message": alert_message}}
                )
                print(f"[Inference] Alert message for {workspace_id}: '{alert_message}'")
            else:
                print(f"[Inference] No documents found in 'hourly_means_{workspace_id}' collection.")
        else:
            print("[Inference] Database connection failed.")
        
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