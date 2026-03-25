FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg curl && \
    curl -fsSL https://deno.land/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "downloader.py"]
