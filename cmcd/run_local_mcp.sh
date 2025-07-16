#!/bin/bash

# Install required dependencies silently
# Determine which pip command to use
if command -v pip3 &> /dev/null; then
  PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
  PIP_CMD="pip"
else
  echo "Error: pip not found. Please install pip."
  exit 1
fi

# Install dependencies with minimal output
$PIP_CMD install -q -r mcp/requirements.txt > /dev/null 2>&1
$PIP_CMD install -q influxdb-client python-dotenv loguru boto3 > /dev/null 2>&1

# Check if .env file exists
if [ ! -f mcp/.env ]; then
  echo "Error: mcp/.env file not found!"
  echo "Please create the .env file with your InfluxDB credentials."
  exit 1
fi

# Get the token from AWS Secrets Manager if not already set
if grep -q "your_influxdb_token" mcp/.env; then
  echo "You need to update the INFLUXDB_TOKEN in mcp/.env"
  echo "You can get it from AWS Secrets Manager or from the bastion host"
  echo "Run: aws secretsmanager get-secret-value --secret-id <your-secret-id> --query SecretString --output text"
  exit 1
fi

# Run the MCP server
cd mcp

# Try different Python commands
if command -v python3 &> /dev/null; then
  echo "Using python3 command"
  python3 cmcd_server.py
elif command -v python &> /dev/null; then
  echo "Using python command"
  python cmcd_server.py
else
  echo "Error: Python not found. Please install Python 3."
  exit 1
fi