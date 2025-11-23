# PatchTST Notebook Integration - Complete System Update

**Date:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")  
**Source Notebook:** `WF_7_PatchTST_Vanilla (5).ipynb`  
**Integration Type:** Research Notebook → Production System

---

## 🎯 Overview

The entire IOT Predictive Maintenance system has been updated to match the proven PatchTST model architecture from the research notebook. This update replaces the simplified custom implementation with the production-grade HuggingFace Transformers PatchTST model.

---

## 📊 Key Changes

### 1. **Model Architecture** 
**Before (SimplePatchTST):**
- Custom PyTorch implementation
- Basic Transformer encoder
- 128 d_model, 4 heads, 2 layers
- Context: 60 timesteps, Prediction: 30 timesteps

**After (HuggingFace PatchTST):**
- Official HuggingFace Transformers implementation
- Advanced PatchTST architecture with patching mechanism
- 256 d_model, 512 FFN dim, 4 heads, 2 layers
- **Patch length: 12, Patch stride: 3** (key innovation)
- Context: **1200 timesteps (50 days)**, Prediction: **240 timesteps (10 days)**

### 2. **Feature Set**
**Before (6 features):**
- `current`, `accX`, `accY`, `accZ`, `tempA`, `tempB`

**After (4 features):**
- `temp_body` (previously tempA)
- `temp_shaft` (previously tempB)
- `current` (unchanged)
- `vibration_magnitude` (combined from X/Y/Z accelerations)

### 3. **Data Preprocessing**
**Before:**
- StandardScaler (Z-score normalization)
- Mean/std saved as normalization stats

**After:**
- **MinMaxScaler(feature_range=(0, 1))** - matching notebook
- Scaler object saved as pickle file
- NaN handling: Replace with feature mean (matching notebook approach)

### 4. **Training Configuration**
| Parameter | Before | After (Notebook Match) |
|-----------|--------|------------------------|
| Batch Size | 32 | **128** |
| Learning Rate | 0.001 | **1e-5** |
| Optimizer | Adam | **AdamW** |
| Epochs | 20 | 20 (unchanged) |
| Gradient Clipping | None | **max_norm=1.0** |
| Early Stopping | None | **patience=5** |

### 5. **Time Scale**
**Before:**
- 2-second intervals (real-time sensor data)
- 60 readings = 2 minutes of data
- 30 predictions = 1 minute ahead

**After:**
- **Hourly intervals** (industrial monitoring standard)
- 1200 readings = **50 days of hourly data**
- 240 predictions = **10 days ahead**
- Minimum data: 1440 points (1 day hourly data)

---

## 🔧 Files Modified

### **Core System Files:**

1. **`GenerateData.py`**
   - Updated sensor fields: `temp_body`, `temp_shaft`, `current`, `vibration_magnitude`
   - Adjusted vibration range: 0.5-2.5 (magnitude instead of X/Y/Z components)

2. **`mqtt_to_influx_bridge.py`**
   - Updated InfluxDB point creation with new field names
   - Maintains same auto-reconnection and reliability features

3. **`spark-apps/train_distributed.py`** ⚠️ **MAJOR REWRITE**
   - Imports: Added `transformers`, `sklearn.preprocessing.MinMaxScaler`
   - Model Config: Updated to match notebook specifications
   - Training Config: New dictionary with batch_size=128, lr=1e-5, etc.
   - Removed: Custom `SimplePatchTST` class
   - Added: `PatchTSTConfig` and `PatchTSTForPrediction` from HuggingFace
   - Updated: `load_workspace_data()` with new field names
   - Updated: `prepare_sequences()` with MinMaxScaler and NaN handling
   - Rewritten: `train_workspace_model()` with:
     - HuggingFace model initialization
     - AdamW optimizer
     - Gradient clipping
     - Early stopping logic
     - Train/validation split (80/20)
     - Per-feature loss tracking
     - Model saved via `save_pretrained()`
     - Scaler saved as pickle

4. **`docker-compose.yml`**
   - Changed Spark services to use custom Dockerfile (build context)
   - All 4 Spark containers now build from `spark-apps/Dockerfile`

5. **`spark-apps/Dockerfile`** ⚠️ **NEW FILE**
   - Base: `apache/spark:3.4.1`
   - Python dependencies:
     - `torch==2.0.1`
     - `transformers==4.35.0`
     - `accelerate==0.24.1`
     - `datasets==2.14.6`
     - `influxdb-client==1.38.0`
     - `pandas==2.1.1`
     - `numpy==1.24.3`
     - `scikit-learn==1.3.1`
     - `tqdm==4.66.1`

---

## 🧠 Model Architecture Details

### PatchTST Configuration
```python
PatchTSTConfig(
    context_length=1200,          # 50 days hourly
    prediction_length=240,         # 10 days hourly
    num_attention_heads=4,
    num_input_channels=4,          # 4 sensor features
    num_targets=4,                 # Same 4 features for output
    num_hidden_layers=2,
    patch_length=12,               # ⭐ Patching innovation
    patch_stride=3,                # ⭐ Stride for patches
    d_model=256,                   # 2x increase
    ffn_dim=512,                   # 4x increase
    dropout=0.1,
    loss="mse",
    scaling=None                   # Manual MinMaxScaler instead
)
```

### Patching Mechanism
The PatchTST model divides the input time series into **patches** of length 12 with stride 3:
- Input: 1200 timesteps
- After patching: ~399 patches (each patch = 12 timesteps)
- Each patch processed as a "token" by transformer
- **Benefit:** Captures local patterns while maintaining long-range dependencies

### Training Process
1. **Data Loading:** InfluxDB → Pandas DataFrame (4 features)
2. **Preprocessing:** MinMaxScaler(0, 1) + NaN handling
3. **Windowing:** Sliding windows (1200 context + 240 target)
4. **Split:** 80% train, 20% validation
5. **Training Loop:**
   - Forward pass: `model(past_values=X, future_values=y)`
   - Loss: MSE on prediction_outputs vs ground truth
   - Backward pass with gradient clipping (max_norm=1.0)
   - AdamW optimizer step (lr=1e-5)
6. **Early Stopping:** Monitor validation loss, patience=5 epochs
7. **Model Save:** `model.save_pretrained()` + scaler pickle

---

## 🚀 Deployment Impact

### Build Changes
- **First-time setup:** Requires Docker image build (~5-10 minutes)
  ```bash
  docker-compose build
  docker-compose up -d
  ```
- **Subsequent updates:** Only rebuild if dependencies change

### Resource Requirements
| Resource | Before | After | Notes |
|----------|--------|-------|-------|
| RAM per worker | 2GB | 2GB | Unchanged |
| CPU per worker | 2 cores | 2 cores | Unchanged |
| Model size | ~1MB | ~5-10MB | HuggingFace model larger |
| Training time | 2-3 min | 5-10 min | More complex model + larger data |

### Data Requirements
- **Minimum:** 1440 hourly data points (1 day) per workspace
- **Recommended:** 2400+ points (100 days) for quality training
- **Previous:** Only 90 data points (3 minutes)
- **Impact:** System needs to run longer before first training

---

## ✅ Benefits

1. **Research-Proven Architecture**
   - Using same model as validated in notebook
   - Proven performance on industrial sensor data

2. **Long-Term Predictions**
   - 10-day ahead forecasting (vs 1 minute before)
   - Better for predictive maintenance planning

3. **Advanced Patching Mechanism**
   - Efficient processing of long sequences
   - Better capture of temporal patterns

4. **Production-Grade Implementation**
   - HuggingFace Transformers library (industry standard)
   - Better maintained, documented, and optimized

5. **Improved Training**
   - Early stopping prevents overfitting
   - Gradient clipping improves stability
   - AdamW better for transformer models

---

## ⚠️ Important Notes

### Breaking Changes
1. **Field Names:** Old data with `accX/accY/accZ/tempA/tempB` won't work
   - **Action:** Flush InfluxDB or migrate data manually
   - **Alternative:** Keep old data for historical reference only

2. **Model Format:** Old `.pt` models incompatible with new system
   - **Action:** Retrain all workspace models after deployment

3. **Time Scale:** System expects hourly data, not 2-second intervals
   - **Current Generator:** Still sends every 2 seconds (for testing)
   - **Production:** Should be updated to hourly intervals

### Data Migration
If you have existing historical data:
```flux
// Query to check old format data
from(bucket: "New_Sensor")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "accX" or r._field == "tempA")
  |> count()

// If count > 0, you have old format data
// Options:
// 1. Delete old data: flux delete with predicate
// 2. Keep separate: Create new bucket for new format
// 3. Migrate: Transform old fields to new (manual script)
```

---

## 🧪 Testing Checklist

- [ ] Build Docker images successfully
- [ ] Start all containers (mosquitto, influxdb, spark cluster)
- [ ] Run data generator (4 features published)
- [ ] Verify bridge writes to InfluxDB (new field names)
- [ ] Wait for 1440 data points (or adjust MIN_DATA_POINTS for testing)
- [ ] Trigger manual training: `./retrain.sh`
- [ ] Check Spark logs for training progress
- [ ] Verify model saved in `spark-apps/models/`
- [ ] Verify scaler pickle saved
- [ ] Check model can be loaded: `PatchTSTForPrediction.from_pretrained(path)`

---

## 📚 References

- **Source Notebook:** `WF_7_PatchTST_Vanilla (5).ipynb`
- **HuggingFace Docs:** https://huggingface.co/docs/transformers/model_doc/patchtst
- **PatchTST Paper:** "A Time Series is Worth 64 Words" (ICLR 2023)
- **Original Implementation:** https://github.com/yuqinie98/PatchTST

---

## 🔄 Rollback Plan

If issues occur, revert to previous version:

```bash
# Stop current system
./stop.sh

# Checkout previous commit
git checkout <previous_commit_hash>

# Rebuild containers
docker-compose down --volumes
docker-compose build
docker-compose up -d

# Restart bridge
./start_bridge.sh
```

---

## 📝 Next Steps

1. ✅ **Code Integration** - COMPLETE
2. ✅ **Docker Configuration** - COMPLETE
3. ⏳ **Documentation Update** - IN PROGRESS
4. ⏳ **System Testing** - PENDING
5. ⏳ **Production Deployment** - PENDING
6. ⏳ **Performance Monitoring** - PENDING

---

**Status:** Ready for deployment and testing  
**Risk Level:** Medium (breaking changes in data format)  
**Recommendation:** Test in staging environment before production
