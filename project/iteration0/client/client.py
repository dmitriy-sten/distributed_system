import requests
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SERVER_URL = os.getenv("SERVER_URL", "http://server:8000")

def main():
    test_data = {"message": "Hello, this is a test echo!", "timestamp": time.time()}
    logger.info(f"Sending to {SERVER_URL}/echo: {test_data}")
    resp = requests.post(f"{SERVER_URL}/echo", json=test_data)
    if resp.ok:
        logger.info(f"Received response: {resp.json()}")
    else:
        logger.error(f"Server error: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    main()
