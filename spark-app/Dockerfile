# Use official Spark image with Python
FROM bitnami/spark:3.5.1

# Switch to root to install Python packages
USER root

# Set working directory
WORKDIR /app

# Copy your Spark streaming code
COPY spark_stream.py .

# Install required Python packages
RUN pip install --no-cache-dir influxdb-client pandas pyarrow

# Default command is spark-submit; actual command is overridden in docker-compose
CMD ["spark-submit", "--master", "local[*]", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1", "/app/spark_stream.py"]
