#!/usr/bin/env python3
"""
Distributed Multi-Workspace Model Training using Apache Spark
Automatically detects workspaces and trains separate models using Spark distributed system
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

# Model configuration
MODEL_CONFIG = {
    "context_length": 60,      # Use last 60 readings (2 minutes at 2sec intervals)
    "prediction_length": 30,    # Predict next 30 readings (1 minute)
    "d_model": 128,
    "num_heads": 4,
    "num_layers": 2,
    "dropout": 0.1,
    "num_features": 6  # current, accX, accY, accZ, tempA, tempB
}

# Minimum data points required per workspace to train
MIN_DATA_POINTS = 90

class SimplePatchTST(nn.Module):
    """Simplified PatchTST model for time series forecasting"""
    
    def __init__(self, config):
        super().__init__()
        self.context_length = config["context_length"]
        self.prediction_length = config["prediction_length"]
        self.d_model = config["d_model"]
        self.num_features = config["num_features"]
        
        # Input projection
        self.input_projection = nn.Linear(self.num_features, self.d_model)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=self.d_model,
            nhead=config["num_heads"],
            dim_feedforward=self.d_model * 4,
            dropout=config["dropout"],
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config["num_layers"]
        )
        
        # Output projection
        self.output_projection = nn.Linear(
            self.d_model * self.context_length,
            self.prediction_length * self.num_features
        )
        
    def forward(self, x):
        # x shape: [batch_size, context_length, num_features]
        batch_size = x.shape[0]
        
        # Project input
        x = self.input_projection(x)  # [batch_size, context_length, d_model]
        
        # Transformer encoding
        x = self.transformer_encoder(x)  # [batch_size, context_length, d_model]
        
        # Flatten and project to output
        x = x.reshape(batch_size, -1)  # [batch_size, context_length * d_model]
        x = self.output_projection(x)  # [batch_size, prediction_length * num_features]
        
        # Reshape to prediction format
        x = x.reshape(batch_size, self.prediction_length, self.num_features)
        
        return x

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

def get_available_workspaces(hours_back=1):
    """Query InfluxDB to get list of all workspaces with data"""
    logger.info(f"🔍 Discovering workspaces from last {hours_back} hours...")
    
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

def load_workspace_data(workspace_id, hours_back=1):
    """Load sensor data for a specific workspace from InfluxDB"""
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
    """Prepare sliding window sequences for training"""
    # Sort by time
    df = df.sort_values('time').reset_index(drop=True)
    
    # Extract features
    features = df[['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']].values
    
    # Normalize features
    mean = features.mean(axis=0)
    std = features.std(axis=0) + 1e-8
    features_normalized = (features - mean) / std
    
    # Create sequences
    X, y = [], []
    total_length = context_length + prediction_length
    
    for i in range(len(features_normalized) - total_length + 1):
        context = features_normalized[i:i + context_length]
        target = features_normalized[i + context_length:i + total_length]
        X.append(context)
        y.append(target)
    
    return np.array(X), np.array(y), mean, std

def train_workspace_model(workspace_info):
    """Train model for a single workspace - executed on Spark worker"""
    workspace_id = workspace_info['workspace_id']
    hours_back = workspace_info['hours_back']
    
    try:
        logger.info(f"🎯 Training model for workspace: {workspace_id}")
        
        # Load data
        df = load_workspace_data(workspace_id, hours_back)
        
        if len(df) < MIN_DATA_POINTS:
            logger.warning(f"⚠️  Skipping {workspace_id}: Only {len(df)} records (need {MIN_DATA_POINTS})")
            return {'workspace_id': workspace_id, 'status': 'skipped', 'reason': 'insufficient_data', 'records': len(df)}
        
        logger.info(f"   📊 Loaded {len(df)} records for {workspace_id}")
        
        # Prepare sequences
        X, y, mean, std = prepare_sequences(df, MODEL_CONFIG["context_length"], MODEL_CONFIG["prediction_length"])
        
        if len(X) == 0:
            logger.warning(f"⚠️  Skipping {workspace_id}: No sequences generated")
            return {'workspace_id': workspace_id, 'status': 'skipped', 'reason': 'no_sequences', 'records': len(df)}
        
        logger.info(f"   📊 Created {len(X)} training sequences")
        
        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)
        
        # Create DataLoader
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        # Initialize model
        model = SimplePatchTST(MODEL_CONFIG)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        # Training loop
        model.train()
        num_epochs = 20
        
        for epoch in range(num_epochs):
            epoch_loss = 0
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                predictions = model(batch_X)
                loss = criterion(predictions, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            
            if (epoch + 1) % 5 == 0:
                avg_loss = epoch_loss / len(dataloader)
                logger.info(f"   Epoch {epoch+1}/{num_epochs}, Loss: {avg_loss:.6f}")
        
        # Save model
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"/opt/spark-apps/models/model_{workspace_id}_{timestamp}.pt"
        stats_path = f"/opt/spark-apps/models/stats_{workspace_id}_{timestamp}.npz"
        
        torch.save(model.state_dict(), model_path)
        np.savez(stats_path, mean=mean, std=std)
        
        logger.info(f"✅ Model saved: {model_path}")
        
        return {
            'workspace_id': workspace_id,
            'status': 'success',
            'records': len(df),
            'sequences': len(X),
            'model_path': model_path,
            'stats_path': stats_path
        }
        
    except Exception as e:
        logger.error(f"❌ Error training {workspace_id}: {e}")
        return {'workspace_id': workspace_id, 'status': 'failed', 'error': str(e)}

def train_all_workspaces_distributed(spark, workspaces, hours_back=1):
    """Train models for all workspaces using Spark distributed processing"""
    logger.info("=" * 80)
    logger.info(f"🚀 Starting distributed training for {len(workspaces)} workspaces")
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
        # Get available workspaces
        workspaces = get_available_workspaces(hours_back=1)
        
        if not workspaces:
            logger.warning("⚠️  No workspaces found with data in the last hour")
            return
        
        # Train models using distributed processing
        results = train_all_workspaces_distributed(spark, workspaces, hours_back=1)
        
        logger.info("🎉 Distributed training complete!")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
