from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, FloatType, StringType, BooleanType
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os

# Environment variables
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = "iot-sensor-data"
INFLUXDB_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUX_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUX_BUCKET")
CHECKPOINT_DIR = "/app/checkpoints"

# Schema for ESP32 JSON
schema = StructType([
    StructField("mqtt_topic", StringType()),
    StructField("payload", StructType([
        StructField("dhtA", StructType([StructField("ok", BooleanType()), StructField("t", FloatType()), StructField("h", FloatType())])),
        StructField("dhtB", StructType([StructField("ok", BooleanType()), StructField("t", FloatType()), StructField("h", FloatType())])),
        StructField("acc", StructType([StructField("x", FloatType()), StructField("y", FloatType()), StructField("z", FloatType())])),
        StructField("current", FloatType())
    ]))
])

# Initialize Spark
spark = SparkSession.builder.appName("ESP32SensorStream").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

# Read from Kafka
df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "earliest") \
    .load()

# Convert Kafka value to string and parse JSON
json_df = df.select(from_json(col("value").cast("string"), schema).alias("data"))

# Flatten
flattened_df = json_df.select(
    col("data.mqtt_topic").alias("topic"),
    col("data.payload.dhtA.t").alias("tempA"),
    col("data.payload.dhtA.h").alias("humA"),
    col("data.payload.dhtB.t").alias("tempB"),
    col("data.payload.dhtB.h").alias("humB"),
    col("data.payload.acc.x").alias("accX"),
    col("data.payload.acc.y").alias("accY"),
    col("data.payload.acc.z").alias("accZ"),
    col("data.payload.current").alias("current")
)

# Write batch to InfluxDB
def write_to_influxdb(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        for row in batch_df.collect():
            point = (
                Point("sensor_data")
                .tag("topic", row["topic"])
                .field("tempA", row["tempA"])
                .field("humA", row["humA"])
                .field("tempB", row["tempB"])
                .field("humB", row["humB"])
                .field("accX", row["accX"])
                .field("accY", row["accY"])
                .field("accZ", row["accZ"])
                .field("current", row["current"])
            )
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)

query = flattened_df.writeStream \
    .outputMode("append") \
    .foreachBatch(write_to_influxdb) \
    .option("checkpointLocation", CHECKPOINT_DIR) \
    .start()

query.awaitTermination()
