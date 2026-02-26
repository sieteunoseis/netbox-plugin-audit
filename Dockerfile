FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir black isort flake8 build twine

COPY . /app
RUN pip install --no-cache-dir /app

ENTRYPOINT ["python", "-m", "netbox_plugin_audit"]
