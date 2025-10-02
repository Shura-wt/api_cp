FROM python:3.12-slim

WORKDIR /app

# Dépendances système (msodbcsql, etc)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl gnupg supervisor && \
    mkdir -p /etc/apt/keyrings && \
    curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY api/ ./api/
COPY scripts/ ./scripts/
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start.sh .
# Normalize line endings and make the script executable
#RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 5000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]