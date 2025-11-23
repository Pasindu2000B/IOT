#!/bin/bash
# =============================================================================
# Retrain Models using Spark Distributed System
# =============================================================================

echo "==============================================="
echo "  Retraining Models (Distributed)"
echo "==============================================="
echo ""

docker exec spark-master bash -c "/opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --executor-memory 1g \
  --total-executor-cores 4 \
  --conf spark.executor.cores=2 \
  --conf spark.task.cpus=1 \
  --conf spark.python.worker.reuse=true \
  /opt/spark-apps/train_distributed.py"

echo ""
echo "==============================================="
echo "  ✅ Training Complete"
echo "==============================================="
echo ""
echo "📁 Latest Models:"
docker exec spark-master ls -lh /opt/spark-apps/models/ | grep "^-" | tail -6
echo ""
