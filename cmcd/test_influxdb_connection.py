#!/usr/bin/env python3
import os
import sys
import socket
import time
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

# Load environment variables from the .env file
load_dotenv("mcp/.env")

# Get the environment variables
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
VERIFY_SSL = os.getenv('VERIFY_SSL', 'False').lower() == 'true'
INFLUXDB_TIMEOUT = int(os.getenv('INFLUXDB_TIMEOUT', '5000'))

print(f"Testing connection to {INFLUXDB_URL}")
print(f"Token: {INFLUXDB_TOKEN[:5]}...{INFLUXDB_TOKEN[-5:]}")
print(f"Organization: {INFLUXDB_ORG}")
print(f"Timeout: {INFLUXDB_TIMEOUT}ms")
print(f"Verify SSL: {VERIFY_SSL}")

# First check if the port is open
host = 'localhost'
port = 8086
print(f"\nChecking if port {port} is open on {host}...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect((host, port))
    print(f"Port {port} is open!")
    s.close()
except Exception as e:
    print(f"Error connecting to {host}:{port} - {e}")
    sys.exit(1)

# Try both HTTP and HTTPS
for protocol in ['http', 'https']:
    url = f"{protocol}://{host}:{port}"
    print(f"\nTrying with {url}...")
    
    try:
        print("Creating client...")
        client = InfluxDBClient(
            url=url,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG,
            timeout=INFLUXDB_TIMEOUT,
            verify_ssl=VERIFY_SSL
        )
        
        print("Checking health...")
        start_time = time.time()
        health = client.health()
        end_time = time.time()
        
        print(f"Health check took {end_time - start_time:.2f} seconds")
        print(f"Health status: {health.status}")
        print(f"Health message: {health.message}")
        
        print("Success with this configuration!")
        client.close()
        break
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Failed with {url}")

print("\nTesting complete.")