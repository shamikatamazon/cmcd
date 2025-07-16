# CMCD Analytics Platform

## Overview

The CMCD (Common Media Client Data) Analytics Platform is a comprehensive solution for capturing, processing, and analyzing streaming media performance data. This platform leverages AWS services including CloudFront, Kinesis, Lambda, and Timestream for InfluxDB to provide real-time insights into streaming media quality of experience (QoE).

CMCD is a standard defined by the Consumer Technology Association (CTA) that enables media players to communicate standardized playback telemetry to content delivery networks (CDNs) and origin servers. This platform collects and analyzes this telemetry data to help optimize streaming performance.

## Architecture

The platform consists of the following components:

1. **CloudFront Distribution**: Delivers streaming media content and collects CMCD metrics
2. **Kinesis Data Stream**: Processes real-time streaming data
3. **Lambda Function**: Transforms and loads data into InfluxDB
4. **Timestream for InfluxDB**: Time-series database for storing and querying metrics
5. **Bastion Host**: Provides secure access to the InfluxDB instance
6. **MCP Server**: Model Context Protocol server that provides tools to query and analyze CMCD metrics

## Key Features

- Real-time collection of CMCD metrics from streaming media clients
- Storage and analysis of streaming performance data including:
  - Buffer levels (bl)
  - Bitrates (br)
  - Duration (d)
  - Media type (mtp)
  - Startup time (su)
  - Target buffer (tb)
- Interactive querying and analysis through the MCP client
- Secure access to the database through AWS SSM tunneling
- Comprehensive CloudFormation template for infrastructure deployment

## Getting Started

### Prerequisites

- AWS CLI installed and configured
- AWS Session Manager Plugin installed
- Python 3.x
- pip package manager

### Setup

1. **Deploy the CloudFormation Stack**:
   ```
   aws cloudformation deploy --template-file cmcd-analytics-stack.yaml --stack-name cmcd-analytics --capabilities CAPABILITY_IAM
   ```

2. **Set up the SSM Tunnel**:
   ```
   ./setup_tunnel.sh
   ```

3. **Configure Environment Variables**:
   Update the `mcp/.env` file with your InfluxDB credentials and AWS configuration.

4. **Test the InfluxDB Connection**:
   ```
   ./check_influxdb.py
   ```

### Running the MCP Server

The MCP (Model Context Protocol) server provides tools to query and analyze CMCD metrics stored in InfluxDB.

```
./run_mcp_server.sh
```

### Running the MCP Client

The MCP client allows you to interact with the MCP server and execute queries against the CMCD metrics.

```
./run_client.sh
```

## Available Tools

The MCP server provides the following tools:

1. **get_average_bitrate**: Get average bitrate statistics
2. **get_session_details**: Retrieve detailed session information
3. **analyze_buffer_events**: Analyze buffer-related events
4. **identify_playback_errors**: Identify potential playback errors
5. **get_edge_location_stats**: Analyze metrics by edge location

## Configuration

### Environment Variables

The following environment variables can be configured in the `mcp/.env` file:

```
# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=cmcd-org
VERIFY_SSL=False
INFLUXDB_TIMEOUT=5000

# AWS SSM Tunnel Configuration
AWS_REGION=REGION (e.g. us-east-2)
BASTION_INSTANCE_ID=INSTANCE_ID (e.g. i-0e27bf506b4743490)
INFLUXDB_ENDPOINT=your-influxdb-endpoint.timestream-influxdb.region.on.aws
LOCAL_PORT=8086
REMOTE_PORT=8086
```

## Troubleshooting

### Connection Issues

If you're experiencing connection issues with InfluxDB:

1. Ensure the SSM tunnel is running
2. Check if port 8086 is open and accessible
3. Verify your InfluxDB token is correct
4. Try using HTTP instead of HTTPS for the InfluxDB URL
5. Reduce the timeout value if connections are slow

### Alternative Test Scripts

The repository includes several test scripts to help diagnose connection issues:

- `check_influxdb.py`: Tests the InfluxDB connection with current configuration
- `test_influxdb_connection.py`: Simple connection test with timing information
## Project Structure

```
.
├── check_influxdb.py              # InfluxDB connection tester
├── cmcd-analytics-stack-fixed.yaml # CloudFormation template
├── mcp/
│   ├── .env                       # Environment variables
│   ├── cmcd_client.py             # MCP client implementation
│   ├── cmcd_server.py             # MCP server implementation
│   ├── mcp.json                   # MCP configuration
│   └── requirements.txt           # Python dependencies
├── run_client.sh                  # Script to run the MCP client
├── run_local_mcp.sh               # Script to run the MCP server locally
├── run_mcp_server.sh              # Script to run the MCP server with tunnel
├── setup_tunnel.sh                # Script to set up SSM tunnel
└── README.md                      # This file
```

## References

- [CMCD Specification (CTA-5004)](https://cdn.cta.tech/cta/media/media/resources/standards/pdfs/cta-5004-final.pdf)
- [AWS Timestream for InfluxDB](https://aws.amazon.com/timestream/influxdb/)
- [Model Context Protocol (MCP)](https://github.com/model-context-protocol/mcp)

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.