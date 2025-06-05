FROM python:3.10-slim

WORKDIR /app
COPY client.py /app/

RUN pip install --no-cache-dir requests

CMD ["python", "client.py"]