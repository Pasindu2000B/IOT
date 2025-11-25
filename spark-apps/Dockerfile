# Custom Spark image with Python ML dependencies
FROM apache/spark:3.4.1

USER root

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages for training (one by one for progress visibility)
RUN pip3 install --no-cache-dir torch==2.0.1
RUN pip3 install --no-cache-dir transformers==4.38.0
RUN pip3 install --no-cache-dir accelerate==0.24.1
RUN pip3 install --no-cache-dir datasets==2.14.6
RUN pip3 install --no-cache-dir influxdb-client==1.38.0
RUN pip3 install --no-cache-dir scikit-learn==1.3.1

USER 185

WORKDIR /opt/spark-apps
