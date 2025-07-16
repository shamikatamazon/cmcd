#!/bin/bash

# Variables - replace these with your actual values
BASTION_INSTANCE_ID="i-0e27bf506b4743490" # Your bastion instance ID
LOCAL_PORT=8086
REMOTE_PORT=8086
AWS_REGION="us-east-2" # Your AWS region

# Hardcode the InfluxDB endpoint - get this from CloudFormation outputs or AWS console
# This should be the private DNS name or IP of your InfluxDB instance
# Format should be: <instance-id>.timestream-influxdb.<region>.amazonaws.com
INFLUXDB_ENDPOINT="b35iqotbpj-couyzfmko7r2io.timestream-influxdb.us-east-2.on.aws"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if session-manager-plugin is installed
if ! command -v session-manager-plugin &> /dev/null; then
    echo "AWS Session Manager Plugin is not installed."
    echo "Please install it from: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html"
    exit 1
fi

# Minimal output for tunnel setup

# Start SSM port forwarding session
aws ssm start-session \
    --target $BASTION_INSTANCE_ID \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "host=$INFLUXDB_ENDPOINT,portNumber=$REMOTE_PORT,localPortNumber=$LOCAL_PORT" \
    --region $AWS_REGION

# This command will keep running until you press Ctrl+C