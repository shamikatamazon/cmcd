#!/usr/bin/env python3
"""
Comprehensive script to check the InfluxDB connection with different configurations.
"""

import os
import sys
import socket
import urllib3
from urllib.parse import urlparse
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

# Load environment variables from the .env file
load_dotenv("mcp/.env")

# Get the environment variables
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
VERIFY_SSL = os.getenv('VERIFY_SSL', 'False').lower() == 'true'
INFLUXDB_TIMEOUT = int(os.getenv('INFLUXDB_TIMEOUT', '30000'))

def check_port_open(host, port):
    """Check if a port is open on a host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception as e:
        print(f"Error connecting to {host}:{port} - {e}")
        return False

def test_connection(url, token, org, timeout, verify_ssl):
    """Test connection to InfluxDB with given parameters."""
    print(f"\nTesting connection with:")
    print(f"  URL: {url}")
    print(f"  Organization: {org}")
    print(f"  Verify SSL: {verify_ssl}")
    print(f"  Timeout: {timeout}ms")
    
    # Disable SSL warnings if verify_ssl is False
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("  SSL certificate verification is disabled")
    
    try:
        # Create the client
        print("  Creating InfluxDB client...")
        client = InfluxDBClient(
            url=url,
            token=token,
            org=org,
            timeout=timeout,
            verify_ssl=verify_ssl
        )
        
        # Check health
        print("  Checking InfluxDB health...")
        health = client.health()
        print(f"  Health status: {health.status}")
        print(f"  Health message: {health.message}")
        
        # List buckets
        print("  Listing buckets...")
        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets().buckets
        print(f"  Found {len(buckets)} buckets:")
        for bucket in buckets:
            print(f"    - {bucket.name}")
        
        # Try a simple query
        print("  Executing a simple query...")
        query_api = client.query_api()
        query = 'buckets()'
        result = query_api.query(query=query)
        print(f"  Query result: {len(result)} tables")
        
        # Close the client
        client.close()
        print("  Connection test successful!")
        return True
        
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def main():
    print("InfluxDB Connection Tester")
    print("=========================")
    print(f"Current configuration from .env file:")
    print(f"URL: {INFLUXDB_URL}")
    print(f"Organization: {INFLUXDB_ORG}")
    print(f"Verify SSL: {VERIFY_SSL}")
    print(f"Timeout: {INFLUXDB_TIMEOUT}ms")
    
    # Check if the tunnel is running
    print("\nChecking if port 8086 is open on localhost...")
    if check_port_open('localhost', 8086):
        print("Port 8086 is open and accepting connections")
    else:
        print("Port 8086 is not accessible")
        print("Make sure the SSM tunnel is running in another terminal")
        return 1
    
    # Test with current configuration
    print("\nTesting with current configuration...")
    if test_connection(INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_TIMEOUT, VERIFY_SSL):
        print("\nSuccess! The current configuration works.")
        return 0
    
    # Try with HTTPS and verify_ssl=False
    print("\nTrying with HTTPS and verify_ssl=False...")
    https_url = INFLUXDB_URL.replace('http://', 'https://')
    if test_connection(https_url, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_TIMEOUT, False):
        print("\nSuccess with HTTPS and verify_ssl=False!")
        print(f"Recommended configuration:")
        print(f"INFLUXDB_URL={https_url}")
        print(f"VERIFY_SSL=False")
        return 0
    
    # Try with HTTP
    print("\nTrying with HTTP...")
    http_url = INFLUXDB_URL.replace('https://', 'http://')
    if test_connection(http_url, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_TIMEOUT, False):
        print("\nSuccess with HTTP!")
        print(f"Recommended configuration:")
        print(f"INFLUXDB_URL={http_url}")
        print(f"VERIFY_SSL=False")
        return 0
    
    print("\nAll connection attempts failed.")
    print("Please check:")
    print("1. The SSM tunnel is running correctly")
    print("2. The InfluxDB endpoint in setup_tunnel.sh is correct")
    print("3. The token in the .env file is valid")
    print("4. The security groups allow connections from the bastion to InfluxDB")
    return 1

if __name__ == "__main__":
    sys.exit(main())