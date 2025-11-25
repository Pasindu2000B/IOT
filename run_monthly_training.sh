#!/bin/bash

# Monthly Model Training Script
# This script trains models for all workspaces using Spark

echo "========================================="
echo " Monthly Model Training"
echo "========================================="
echo ""
echo "Starting training at: $(date)"
echo ""

# Navigate to spark-apps directory
cd "$(dirname "$0")/spark-apps" || exit 1

# Check if model_trainer.py exists
if [ ! -f "model_trainer.py" ]; then
    echo "ERROR: model_trainer.py not found in spark-apps/"
    exit 1
fi

# Run model training
echo "Running model training..."
python model_trainer.py

EXIT_CODE=$?

echo ""
echo "Training completed at: $(date)"
echo "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Training successful!"
else
    echo "❌ Training failed with exit code $EXIT_CODE"
fi

echo "========================================="
exit $EXIT_CODE
