#!/bin/bash

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v session-manager-plugin &> /dev/null; then
    echo "Error: AWS Session Manager Plugin is not installed."
    echo "Please install it from: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html"
    exit 1
fi

# Determine which pip command to use
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo "Error: pip not found. Please install pip."
    exit 1
fi

# Determine which Python command to use
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Please install Python 3."
    exit 1
fi

# Install dependencies silently
$PIP_CMD install -q -r mcp/requirements.txt > /dev/null 2>&1
$PIP_CMD install -q influxdb-client python-dotenv loguru boto3 > /dev/null 2>&1

# Check if .env file exists
if [ ! -f mcp/.env ]; then
    echo "Error: mcp/.env file not found!"
    echo "Please create the .env file with your InfluxDB credentials."
    exit 1
fi

# Create a temporary Python script to read .env variables
cat > /tmp/read_env.py << 'EOF'
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv("mcp/.env")

# Get the environment variables
influxdb_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
influxdb_token = os.getenv('INFLUXDB_TOKEN', '')
influxdb_org = os.getenv('INFLUXDB_ORG', 'cmcd-org')
verify_ssl = os.getenv('VERIFY_SSL', 'False').lower() == 'true'
influxdb_timeout = int(os.getenv('INFLUXDB_TIMEOUT', '30000'))

# Get AWS configuration from environment or .env
aws_region = os.getenv('AWS_REGION', 'us-east-2')
bastion_instance_id = os.getenv('BASTION_INSTANCE_ID', 'i-0e27bf506b4743490')
influxdb_endpoint = os.getenv('INFLUXDB_ENDPOINT', 'b35iqotbpj-couyzfmko7r2io.timestream-influxdb.us-east-2.on.aws')
local_port = os.getenv('LOCAL_PORT', '8086')
remote_port = os.getenv('REMOTE_PORT', '8086')

# Print the variables in a format that can be sourced by bash
print(f"INFLUXDB_URL={influxdb_url}")
print(f"INFLUXDB_TOKEN={influxdb_token}")
print(f"INFLUXDB_ORG={influxdb_org}")
print(f"VERIFY_SSL={'true' if verify_ssl else 'false'}")
print(f"INFLUXDB_TIMEOUT={influxdb_timeout}")
print(f"AWS_REGION={aws_region}")
print(f"BASTION_INSTANCE_ID={bastion_instance_id}")
print(f"INFLUXDB_ENDPOINT={influxdb_endpoint}")
print(f"LOCAL_PORT={local_port}")
print(f"REMOTE_PORT={remote_port}")
EOF

# Source the variables from the Python script
echo "Loading configuration from mcp/.env file..."
eval "$($PYTHON_CMD /tmp/read_env.py)"
rm /tmp/read_env.py

# Extract host from INFLUXDB_URL if not explicitly set
if [ -z "$INFLUXDB_ENDPOINT" ]; then
    # Extract host from URL using Python
    INFLUXDB_ENDPOINT=$($PYTHON_CMD -c "from urllib.parse import urlparse; print(urlparse('$INFLUXDB_URL').netloc.split(':')[0])")
    echo "Extracted INFLUXDB_ENDPOINT from URL: $INFLUXDB_ENDPOINT"
fi

# Display the configuration
echo "Configuration:"
echo "  INFLUXDB_URL: $INFLUXDB_URL"
echo "  INFLUXDB_ORG: $INFLUXDB_ORG"
echo "  AWS_REGION: $AWS_REGION"
echo "  BASTION_INSTANCE_ID: $BASTION_INSTANCE_ID"
echo "  INFLUXDB_ENDPOINT: $INFLUXDB_ENDPOINT"
echo "  LOCAL_PORT: $LOCAL_PORT"
echo "  REMOTE_PORT: $REMOTE_PORT"

# Start the SSM tunnel in the background
echo "Starting SSM tunnel to InfluxDB..."
aws ssm start-session \
    --target $BASTION_INSTANCE_ID \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "host=$INFLUXDB_ENDPOINT,portNumber=$REMOTE_PORT,localPortNumber=$LOCAL_PORT" \
    --region $AWS_REGION &

# Store the tunnel process ID
TUNNEL_PID=$!

# Give the tunnel a moment to establish
sleep 2

# Function to clean up when the script exits
cleanup() {
    echo "Shutting down..."
    if ps -p $TUNNEL_PID > /dev/null; then
        kill $TUNNEL_PID 2>/dev/null
    fi
    exit 0
}

# Set up trap to catch Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM EXIT

# Run the MCP server
echo "Starting MCP server..."
cd mcp
$PYTHON_CMD cmcd_server.py

# Note: The cleanup function will be called automatically when the script exits