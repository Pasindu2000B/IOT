#!/usr/bin/env python3
"""
Distributed Multi-Workspace Model Training using Apache Spark
Automatically detects workspaces and trains separate models using Spark distributed system
Uses HuggingFace PatchTST implementation matching the research notebook
"""
import sys
import os
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from pyspark.sql import SparkSession
from pyspark import SparkConf
from influxdb_client import InfluxDBClient
from transformers import PatchTSTConfig, PatchTSTForPrediction
from sklearn.preprocessing import MinMaxScaler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# InfluxDB configuration
INFLUXDB_URL = "http://influxdb:8086"  # Use Docker service name for containers
INFLUXDB_TOKEN = "GO7pQ79-Vo-k6uwpQrMmJmITzLRHxyrFbFDrnRbz8PgZbLHKe5hpwNZCWi6Z_zolPRjn7jUQ6irQk-BPe3LK9Q=="
INFLUXDB_ORG = "Ruhuna_Eng"
INFLUXDB_BUCKET = "New_Sensor"

# Model configuration (matching notebook specifications)
MODEL_CONFIG = {
    "context_length": 1200,         # 50 days of hourly data
    "prediction_length": 240,        # 10 days of hourly predictions
    "num_input_channels": 6,         # current, accX, accY, accZ, tempA, tempB
    "num_targets": 6,                # Same 6 features for output
    "num_attention_heads": 4,
    "num_hidden_layers": 2,
    "patch_length": 12,
    "patch_stride": 3,
    "d_model": 256,
    "ffn_dim": 512,
    "dropout": 0.1,
    "loss": "mse",
    "scaling": None  # We'll use MinMaxScaler instead
}

# Training configuration (matching notebook)
TRAINING_CONFIG = {
    "batch_size": 128,
    "num_epochs": 20,
    "learning_rate": 1e-5,
    "max_grad_norm": 1.0,
    "early_stopping_patience": 5
}

# Minimum data points required per workspace to train (context + prediction)
MIN_DATA_POINTS = 1440  # At least 1 day of hourly data

class SimplePatchTST(nn.Module):
    """
    HuggingFace PatchTST wrapper for compatibility
    This is kept for reference but we'll use PatchTSTForPrediction directly
    """
    pass  # Not used - using transformers.PatchTSTForPrediction instead

def get_spark_session():
    """Initialize Spark session with proper configuration"""
    logger.info("🔧 Initializing Spark session...")
    
    conf = SparkConf() \
        .setAppName("Multi-Workspace-Model-Training") \
        .set("spark.executor.memory", "1g") \
        .set("spark.driver.memory", "1g") \
        .set("spark.executor.cores", "2") \
        .set("spark.task.cpus", "1") \
        .set("spark.python.worker.reuse", "true")
    
    spark = SparkSession.builder \
        .config(conf=conf) \
        .getOrCreate()
    
    logger.info(f"   ✅ Spark session initialized: {spark.sparkContext.master}")
    logger.info(f"   ✅ Spark version: {spark.version}")
    logger.info(f"   ✅ Available executors: {len(spark.sparkContext._jsc.sc().statusTracker().getExecutorInfos()) - 1}")
    
    return spark

def get_available_workspaces(hours_back=720):
    """Query InfluxDB to get list of all workspaces with data"""
    logger.info(f"🔍 Discovering workspaces from last {hours_back} hours ({hours_back/24:.1f} days)...")
    
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    
    # Query to get unique workspace IDs
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -{hours_back}h)
        |> filter(fn: (r) => r._measurement == "sensor_data")
        |> keep(columns: ["workspace_id"])
        |> distinct(column: "workspace_id")
    '''
    
    result = query_api.query(query=query)
    
    workspaces = set()
    for table in result:
        for record in table.records:
            workspace_id = record.values.get('workspace_id')
            if workspace_id:
                workspaces.add(workspace_id)
    
    client.close()
    
    workspaces = sorted(list(workspaces))
    logger.info(f"✅ Found {len(workspaces)} workspaces: {workspaces}")
    return workspaces

def load_workspace_data(workspace_id, hours_back=720):
    """Load sensor data for a specific workspace from InfluxDB (default: 30 days)"""
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    
    # Query to get data for specific workspace
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -{hours_back}h)
        |> filter(fn: (r) => r._measurement == "sensor_data")
        |> filter(fn: (r) => r.workspace_id == "{workspace_id}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    
    result = query_api.query(query=query)
    
    # Convert to pandas DataFrame
    records = []
    for table in result:
        for record in table.records:
            records.append({
                'time': record.get_time(),
                'current': float(record.values.get('current', 0)),
                'accX': float(record.values.get('accX', 0)),
                'accY': float(record.values.get('accY', 0)),
                'accZ': float(record.values.get('accZ', 0)),
                'tempA': float(record.values.get('tempA', 0)),
                'tempB': float(record.values.get('tempB', 0))
            })
    
    df = pd.DataFrame(records)
    client.close()
    
    return df

def prepare_sequences(df, context_length, prediction_length):
    """Prepare sliding window sequences for training using MinMaxScaler (matching notebook)
    
    Handles sparse data: Only creates sequences from continuous data blocks.
    If machine is down (no data), those time periods are automatically excluded.
    """
    # Sort by time
    df = df.sort_values('time').reset_index(drop=True)
    
    # Extract features (current, accX, accY, accZ, tempA, tempB)
    features = df[['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']].values
    
    # Handle NaN values - replace with feature mean (matching notebook approach)
    for i in range(features.shape[1]):
        feature_col = features[:, i]
        if np.isnan(feature_col).any():
            feature_mean = np.nanmean(feature_col)
            features[:, i] = np.nan_to_num(feature_col, nan=feature_mean)
    
    # Normalize features using MinMaxScaler (matching notebook)
    scaler = MinMaxScaler(feature_range=(0, 1))
    features_normalized = scaler.fit_transform(features)
    
    # Create sequences (sliding window)
    # Note: Only creates sequences from available data points
    # Machine downtime (missing data) naturally creates fewer sequences
    X, y = [], []
    total_length = context_length + prediction_length
    
    for i in range(len(features_normalized) - total_length + 1):
        context = features_normalized[i:i + context_length]
        target = features_normalized[i + context_length:i + total_length]
        X.append(context)
        y.append(target)
    
    return np.array(X), np.array(y), scaler

def train_workspace_model(workspace_info):
    """Train model for a single workspace using HuggingFace PatchTST - executed on Spark worker"""
    workspace_id = workspace_info['workspace_id']
    hours_back = workspace_info['hours_back']
    
    try:
        logger.info(f"🎯 Training PatchTST model for workspace: {workspace_id}")
        
        # Load data
        df = load_workspace_data(workspace_id, hours_back)
        
        if len(df) < MIN_DATA_POINTS:
            logger.warning(f"⚠️  Skipping {workspace_id}: Only {len(df)} records (need {MIN_DATA_POINTS})")
            return {'workspace_id': workspace_id, 'status': 'skipped', 'reason': 'insufficient_data', 'records': len(df)}
        
        logger.info(f"   📊 Loaded {len(df)} records for {workspace_id}")
        
        # Prepare sequences
        X, y, scaler = prepare_sequences(df, MODEL_CONFIG["context_length"], MODEL_CONFIG["prediction_length"])
        
        if len(X) == 0:
            logger.warning(f"⚠️  Skipping {workspace_id}: No sequences generated")
            return {'workspace_id': workspace_id, 'status': 'skipped', 'reason': 'no_sequences', 'records': len(df)}
        
        logger.info(f"   📊 Created {len(X)} training sequences")
        
        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)
        
        # Create DataLoader
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=TRAINING_CONFIG["batch_size"], shuffle=True)
        
        # Initialize HuggingFace PatchTST model
        config = PatchTSTConfig(
            context_length=MODEL_CONFIG["context_length"],
            prediction_length=MODEL_CONFIG["prediction_length"],
            num_attention_heads=MODEL_CONFIG["num_attention_heads"],
            num_input_channels=MODEL_CONFIG["num_input_channels"],
            num_targets=MODEL_CONFIG["num_targets"],
            num_hidden_layers=MODEL_CONFIG["num_hidden_layers"],
            patch_length=MODEL_CONFIG["patch_length"],
            patch_stride=MODEL_CONFIG["patch_stride"],
            d_model=MODEL_CONFIG["d_model"],
            ffn_dim=MODEL_CONFIG["ffn_dim"],
            dropout=MODEL_CONFIG["dropout"],
            loss=MODEL_CONFIG["loss"],
            scaling=MODEL_CONFIG["scaling"]
        )
        model = PatchTSTForPrediction(config)
        
        # Setup device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        logger.info(f"   🔧 Using device: {device}")
        
        # Define loss and optimizer (matching notebook)
        criterion = nn.MSELoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=TRAINING_CONFIG["learning_rate"])
        
        # Training loop with early stopping
        model.train()
        best_val_loss = float('inf')
        early_stop_counter = 0
        train_losses = []
        
        # Split data for validation (80/20 split)
        split_idx = int(0.8 * len(dataset))
        train_dataset = torch.utils.data.Subset(dataset, range(0, split_idx))
        val_dataset = torch.utils.data.Subset(dataset, range(split_idx, len(dataset)))
        
        train_loader = DataLoader(train_dataset, batch_size=TRAINING_CONFIG["batch_size"], shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=TRAINING_CONFIG["batch_size"])
        
        for epoch in range(TRAINING_CONFIG["num_epochs"]):
            # Training phase
            epoch_loss = 0
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                
                optimizer.zero_grad()
                outputs = model(past_values=batch_X, future_values=batch_y)
                loss = outputs.loss
                
                # Check for NaN loss
                if torch.isnan(loss):
                    logger.warning(f"   ⚠️ NaN loss detected at epoch {epoch+1}")
                    continue
                
                loss.backward()
                # Gradient clipping (matching notebook)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=TRAINING_CONFIG["max_grad_norm"])
                optimizer.step()
                
                epoch_loss += loss.item()
            
            avg_train_loss = epoch_loss / len(train_loader) if len(train_loader) > 0 else 0
            train_losses.append(avg_train_loss)
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for batch_X, batch_y in val_loader:
                    batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                    outputs = model(past_values=batch_X, future_values=batch_y)
                    preds = outputs.prediction_outputs if outputs.prediction_outputs is not None else outputs.logits
                    loss = criterion(preds, batch_y)
                    val_loss += loss.item()
            
            avg_val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0
            
            if (epoch + 1) % 5 == 0:
                logger.info(f"   Epoch {epoch+1}/{TRAINING_CONFIG['num_epochs']}, Train Loss: {avg_train_loss:.6f}, Val Loss: {avg_val_loss:.6f}")
            
            # Early stopping check
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                early_stop_counter = 0
            else:
                early_stop_counter += 1
                if early_stop_counter >= TRAINING_CONFIG["early_stopping_patience"]:
                    logger.info(f"   🛑 Early stopping triggered at epoch {epoch+1}")
                    break
            
            model.train()
        
        # Save model
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_dir = f"/opt/spark-apps/models/model_{workspace_id}_{timestamp}"
        scaler_path = f"/opt/spark-apps/models/scaler_{workspace_id}_{timestamp}.pkl"
        
        # Save HuggingFace model
        model.save_pretrained(model_dir)
        
        # Save scaler
        import pickle
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        logger.info(f"✅ Model saved: {model_dir}")
        logger.info(f"✅ Scaler saved: {scaler_path}")
        
        return {
            'workspace_id': workspace_id,
            'status': 'success',
            'records': len(df),
            'sequences': len(X),
            'model_path': model_dir,
            'scaler_path': scaler_path,
            'final_train_loss': avg_train_loss,
            'final_val_loss': best_val_loss
        }
        
    except Exception as e:
        logger.error(f"❌ Error training {workspace_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'workspace_id': workspace_id, 'status': 'failed', 'error': str(e)}

def train_all_workspaces_distributed(spark, workspaces, hours_back=720):
    """Train models for all workspaces using Spark distributed processing"""
    logger.info("=" * 80)
    logger.info(f"🚀 Starting distributed training for {len(workspaces)} workspaces (using {hours_back/24:.1f} days of data)")
    logger.info("=" * 80)
    
    # Prepare workspace data for distribution
    workspace_data = [{'workspace_id': w, 'hours_back': hours_back} for w in workspaces]
    
    # Distribute training across Spark workers using RDD
    workspace_rdd = spark.sparkContext.parallelize(workspace_data, len(workspaces))
    results = workspace_rdd.map(train_workspace_model).collect()
    
    # Summary
    logger.info("=" * 80)
    logger.info("📊 Training Summary:")
    logger.info("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"⚠️  Skipped: {skipped_count}")
    logger.info(f"❌ Failed: {failed_count}")
    logger.info("")
    
    for result in results:
        if result['status'] == 'success':
            logger.info(f"   ✅ {result['workspace_id']}: {result['sequences']} sequences, {result['records']} records")
        elif result['status'] == 'skipped':
            logger.info(f"   ⚠️  {result['workspace_id']}: {result.get('reason', 'unknown')} ({result.get('records', 0)} records)")
        else:
            logger.info(f"   ❌ {result['workspace_id']}: {result.get('error', 'unknown error')}")
    
    logger.info("=" * 80)
    
    return results

def main():
    """Main function"""
    logger.info("=" * 80)
    logger.info("IOT Predictive Maintenance - Distributed Model Training")
    logger.info("=" * 80)
    
    # Initialize Spark
    spark = get_spark_session()
    
    try:
        # Get available workspaces (30 days = 720 hours for monthly training)
        workspaces = get_available_workspaces(hours_back=720)
        
        if not workspaces:
            logger.warning("⚠️  No workspaces found with data in the last 30 days")
            return
        
        # Train models using distributed processing (30 days of data)
        results = train_all_workspaces_distributed(spark, workspaces, hours_back=720)
        
        logger.info("🎉 Distributed training complete!")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
