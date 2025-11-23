# =============================================================================
# Retrain Models using Spark Distributed System (Windows)
# =============================================================================

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Retraining Models (Distributed)" -ForegroundColor Yellow
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

docker exec spark-master bash -c "/opt/spark/bin/spark-submit --master spark://spark-master:7077 --executor-memory 1g --total-executor-cores 4 --conf spark.executor.cores=2 --conf spark.task.cpus=1 --conf spark.python.worker.reuse=true /opt/spark-apps/train_distributed.py"

Write-Host "`n===============================================" -ForegroundColor Cyan
Write-Host "  ✅ Training Complete" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📁 Latest Models:" -ForegroundColor Yellow
Get-ChildItem -Path "spark-apps\models\*.pt" | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object { Write-Host "   $($_.Name)" }
Write-Host ""
