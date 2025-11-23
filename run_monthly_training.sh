#!/bin/bash
# =============================================================================
# Monthly Model Retraining Script
# This script is run by the training-scheduler container on a monthly basis
# It triggers model retraining using the Spark distributed system
# =============================================================================

echo "=================================================="
echo "Monthly Model Retraining - $(date)"
echo "=================================================="

# Run distributed training using Spark
docker exec spark-master bash -c "/opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --executor-memory 1g \
  --total-executor-cores 4 \
  --conf spark.executor.cores=2 \
  --conf spark.task.cpus=1 \
  --conf spark.python.worker.reuse=true \
  /opt/spark-apps/train_distributed.py"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Monthly retraining completed successfully - $(date)"
else
    echo "❌ Monthly retraining failed with exit code $EXIT_CODE - $(date)"
fi

echo "=================================================="

exit $EXIT_CODE
