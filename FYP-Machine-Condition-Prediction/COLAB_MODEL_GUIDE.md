# 📚 Complete Guide: Adding Colab-Trained Model to Inference System

## 🎯 Overview

This guide shows you how to train a PatchTST model in Google Colab and deploy it to the local inference system.

---

## Part 1: Training Model in Google Colab

### Step 1: Prepare Data in Colab

```python
import pandas as pd
import numpy as np
import torch
from transformers import PatchTSTConfig, PatchTSTForPrediction
from sklearn.preprocessing import MinMaxScaler
import pickle
from datetime import datetime

# Connect to your InfluxDB or load CSV data
# Example: Load from CSV
df = pd.read_csv('sensor_data.csv')

# Your data should have these columns:
# timestamp, current, accX, accY, accZ, tempA, tempB

# Sort by timestamp
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Total data points: {len(df)}")
print(df.head())
```

### Step 2: Prepare Training Sequences

```python
def create_sequences(data, context_length=50, prediction_length=10):
    """
    Create sliding window sequences for training
    
    Args:
        data: DataFrame with sensor readings
        context_length: Number of past points to use (50)
        prediction_length: Number of future points to predict (10)
    
    Returns:
        X: Context sequences (past data)
        y: Target sequences (future data)
        scaler: Fitted MinMaxScaler
    """
    # Select feature columns
    features = data[['current', 'accX', 'accY', 'accZ', 'tempA', 'tempB']].values
    
    # Normalize data (0-1 range)
    scaler = MinMaxScaler(feature_range=(0, 1))
    features_normalized = scaler.fit_transform(features)
    
    # Create sequences
    X = []  # Context (input)
    y = []  # Target (output)
    
    total_length = context_length + prediction_length
    
    for i in range(len(features_normalized) - total_length + 1):
        context = features_normalized[i:i + context_length]
        target = features_normalized[i + context_length:i + total_length]
        X.append(context)
        y.append(target)
    
    return np.array(X), np.array(y), scaler

# Create sequences
context_length = 50
prediction_length = 10

X_train, y_train, scaler = create_sequences(df, context_length, prediction_length)

print(f"Training sequences: {len(X_train)}")
print(f"X shape: {X_train.shape}")  # Should be (N, 50, 6)
print(f"y shape: {y_train.shape}")  # Should be (N, 10, 6)
```

### Step 3: Configure and Train Model

```python
from torch.utils.data import DataLoader, TensorDataset
import torch.nn as nn

# Convert to PyTorch tensors
X_tensor = torch.FloatTensor(X_train)
y_tensor = torch.FloatTensor(y_train)

# Create DataLoader
dataset = TensorDataset(X_tensor, y_tensor)
dataloader = DataLoader(dataset, batch_size=8, shuffle=True)

# Configure PatchTST model
config = PatchTSTConfig(
    context_length=50,           # Input sequence length
    prediction_length=10,        # Output sequence length
    num_input_channels=6,        # 6 sensor features
    num_targets=6,               # Predict all 6 features
    num_attention_heads=4,       # Multi-head attention
    num_hidden_layers=2,         # Transformer layers
    patch_length=5,              # Patch size
    patch_stride=2,              # Patch stride
    d_model=128,                 # Model dimension
    ffn_dim=256,                 # Feedforward dimension
    dropout=0.1,
    loss="mse",                  # Mean Squared Error
    scaling=None                 # We use MinMaxScaler instead
)

# Create model
model = PatchTSTForPrediction(config)

# Move to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"Training on: {device}")

# Training setup
criterion = nn.MSELoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
num_epochs = 10

# Training loop
model.train()
for epoch in range(num_epochs):
    epoch_loss = 0
    batch_count = 0
    
    for batch_X, batch_y in dataloader:
        batch_X = batch_X.to(device)
        batch_y = batch_y.to(device)
        
        # Forward pass
        optimizer.zero_grad()
        outputs = model(past_values=batch_X)
        predictions = outputs.prediction_outputs
        
        # Calculate loss
        loss = criterion(predictions, batch_y)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        epoch_loss += loss.item()
        batch_count += 1
    
    avg_loss = epoch_loss / batch_count
    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {avg_loss:.6f}")

print("\n✅ Training completed!")
```

### Step 4: Save Model and Scaler

```python
# YOUR WORKSPACE ID - MUST MATCH INFLUXDB TAG EXACTLY!
workspace_id = "production-line-1"  # ⚠️ CHANGE THIS to your real workspace name

# Generate timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create directory names
model_dir = f"model_{workspace_id}_{timestamp}"
scaler_file = f"scaler_{workspace_id}_{timestamp}.pkl"

print(f"\n📦 Saving model...")
print(f"   Model folder: {model_dir}")
print(f"   Scaler file: {scaler_file}")

# Save PatchTST model (HuggingFace format)
model.save_pretrained(model_dir)
print(f"   ✅ Model saved")

# Save scaler
with open(scaler_file, "wb") as f:
    pickle.dump(scaler, f)
print(f"   ✅ Scaler saved")

# Verify files exist
import os
print(f"\n📁 Files created:")
print(f"   Model folder exists: {os.path.exists(model_dir)}")
print(f"   Scaler file exists: {os.path.exists(scaler_file)}")

# List model files
if os.path.exists(model_dir):
    print(f"\n   Model files:")
    for file in os.listdir(model_dir):
        print(f"      - {file}")
```

### Step 5: Download from Colab

```python
# Zip the model folder
import shutil
zip_file = f"{model_dir}"
shutil.make_archive(zip_file, 'zip', model_dir)

# Download files
from google.colab import files

print("\n⬇️ Downloading files...")
files.download(f"{model_dir}.zip")
files.download(scaler_file)
print("✅ Download started! Check your browser downloads.")
```

---

## Part 2: Deploy to Local System

### Step 6: Extract and Organize Files (on your PC)

**A. Extract the downloaded files:**

```powershell
# Navigate to downloads folder
cd C:\Users\Asus\Downloads

# Extract the zip file
Expand-Archive -Path "model_production-line-1_20251125_120000.zip" -DestinationPath "."

# You should now have:
# model_production-line-1_20251125_120000/
#   ├── config.json
#   ├── generation_config.json
#   ├── pytorch_model.bin
#   └── (other files)
# scaler_production-line-1_20251125_120000.pkl
```

**B. Verify workspace ID matches InfluxDB:**

⚠️ **CRITICAL:** The workspace ID in the folder name MUST exactly match the `workspace_id` tag in your InfluxDB data!

```powershell
# Check your InfluxDB workspace names
curl http://142.93.220.152:8086/api/v2/query `
  -H "Authorization: Token YOUR_TOKEN" `
  -d 'from(bucket:"New_Sensor") |> range(start: -1h) |> keep(columns: ["workspace_id"]) |> distinct(column: "workspace_id")'
```

If your InfluxDB has `workspace_id = "production-line-1"`, your files must be:
- `model_production-line-1_{timestamp}/`
- `scaler_production-line-1_{timestamp}.pkl`

### Step 7: Copy to Inference System

**Option A: Manual Copy**

```powershell
# Copy model folder
Copy-Item -Recurse `
  "C:\Users\Asus\Downloads\model_production-line-1_20251125_120000" `
  "C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction\FYP-Machine-Condition-Prediction\"

# Copy scaler file
Copy-Item `
  "C:\Users\Asus\Downloads\scaler_production-line-1_20251125_120000.pkl" `
  "C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction\FYP-Machine-Condition-Prediction\"

# Verify
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction\FYP-Machine-Condition-Prediction
Get-ChildItem | Where-Object {$_.Name -like "*production-line-1*"}
```

**Option B: Using Helper Script**

```powershell
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction

python add_colab_model.py `
  "C:\Users\Asus\Downloads\model_production-line-1_20251125_120000" `
  "C:\Users\Asus\Downloads\scaler_production-line-1_20251125_120000.pkl"
```

### Step 8: Verify Model Files

```powershell
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction\FYP-Machine-Condition-Prediction

# Check model folder structure
Get-ChildItem "model_production-line-1_*" -Recurse | Select-Object Name

# Should show:
#   config.json
#   generation_config.json  
#   pytorch_model.bin
#   (other files)

# Check scaler file
Get-ChildItem "scaler_production-line-1_*.pkl"
```

### Step 9: Test Model Loading

```powershell
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction

# Test if model loads correctly
python -c "
from services.inference_service import InferenceService
service = InferenceService()
print('Available workspaces:', service.get_available_workspaces())
"
```

Expected output:
```
[InferenceService] Discovered 1 workspace(s)
[InferenceService] Loaded model for workspace: production-line-1
                    Model: model_production-line-1_20251125_120000
[InferenceService] Total models loaded: 1
Available workspaces: ['production-line-1']
```

### Step 10: Start Inference Server

```powershell
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction

# Start server
python main.py
```

Wait for:
```
[InferenceService] Loaded model for workspace: production-line-1
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 11: Verify Model is Working

**A. Check API:**
```powershell
# List workspaces
curl http://localhost:8000/workspaces

# Should return:
# {
#   "status": "success",
#   "workspaces_with_models": ["production-line-1"],
#   "total_models": 1
# }
```

**B. Check Dashboard:**
- Open: http://localhost:8000
- Your workspace should appear in the dashboard
- Wait 60 seconds for first inference to complete

**C. Test Predictions:**
```powershell
curl http://localhost:8000/predict/production-line-1
```

---

## 📋 Troubleshooting

### Problem: Model not loading

**Check 1: File structure**
```powershell
# Should see:
# FYP-Machine-Condition-Prediction/
#   FYP-Machine-Condition-Prediction/
#     model_production-line-1_20251125_120000/
#       config.json
#       pytorch_model.bin
#     scaler_production-line-1_20251125_120000.pkl
```

**Check 2: Naming convention**
- Model folder: `model_{workspace}_{timestamp}`
- Scaler file: `scaler_{workspace}_{timestamp}.pkl`
- Both must have SAME workspace ID and timestamp

**Check 3: Required files in model folder**
- `config.json` ✓
- `pytorch_model.bin` ✓
- `generation_config.json` ✓

### Problem: No predictions appearing

**Check 1: InfluxDB has data**
```powershell
# Query InfluxDB for your workspace
curl http://142.93.220.152:8086/health
```

**Check 2: Workspace ID matches exactly**
```python
# In inference logs, check:
[RealInfluxStreamer] Active workspaces: ['production-line-1']
```

**Check 3: Enough data points**
- Need at least 50 data points for inference
- Data should be recent (last 10 minutes)

### Problem: Validation fails

**Error: "Insufficient data for validation"**
- Need at least 60 data points (50 context + 10 prediction)
- Let data accumulate for 2-3 minutes
- Check InfluxDB has continuous data stream

---

## 🎯 Quick Reference

### File Naming Convention
```
model_{workspace-id}_{timestamp}/
scaler_{workspace-id}_{timestamp}.pkl

Example:
model_production-line-1_20251125_143022/
scaler_production-line-1_20251125_143022.pkl
```

### Required Model Files
- `config.json` - Model configuration
- `pytorch_model.bin` - Trained weights
- `generation_config.json` - Generation parameters

### Target Directory
```
C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction\FYP-Machine-Condition-Prediction\
```

### Key Points
✅ Workspace ID must match InfluxDB exactly  
✅ Use MinMaxScaler with feature_range=(0, 1)  
✅ Model must be PatchTST saved with .save_pretrained()  
✅ 6 features: current, accX, accY, accZ, tempA, tempB  
✅ Context length: 50, Prediction length: 10  

---

## 🚀 Next Steps After Deployment

1. **Monitor in Dashboard**: http://localhost:8000
2. **Validate Accuracy**: http://localhost:8000/validation
3. **Check API**: http://localhost:8000/docs
4. **View Logs**: Check terminal for inference results

Your model is now live and making real-time predictions! 🎉
