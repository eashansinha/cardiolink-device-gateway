FROM python:3.12-slim
ARG PIP_INDEX_URL
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# cardiolink-shared-auth is supplied as an additional build context (see cardiolink-infra/local/docker-compose.yml)
COPY --from=shared-auth . /tmp/shared-auth
RUN pip install --no-cache-dir /tmp/shared-auth
COPY app app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
