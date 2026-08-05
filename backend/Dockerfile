FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    sumo sumo-tools \
    && rm -rf /var/lib/apt/lists/*

ENV SUMO_HOME=/usr/share/sumo

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "backend/main.py"]