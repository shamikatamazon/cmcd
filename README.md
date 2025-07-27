# CMCD MCP Server

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A Model Context Protocol (MCP) server for analyzing Common Media Client Data (CMCD) streaming telemetry. This server provides AI-powered analytics tools for video streaming quality of experience (QoE) analysis using data stored in InfluxDB.

## What is CMCD?

Common Media Client Data (CMCD) is a specification that enables media players to convey streaming performance data to content delivery networks (CDNs) and origin servers. This data helps optimize streaming delivery and provides insights into playback quality.

## Architecture

This MCP server connects to InfluxDB containing CMCD telemetry data and provides structured analytics tools that can be used by AI assistants and other MCP clients to analyze streaming performance.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │───▶│   CMCD MCP       │───▶│    InfluxDB     │
│  (AI Assistant) │    │    Server        │    │ (CMCD Metrics)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Features

### 🎯 **Streaming Analytics**
- **Average Bitrate Analysis** - Calculate mean bitrates across time ranges with session/content filtering
- **Session Timeline Analysis** - Retrieve comprehensive session metrics and playback timelines
- **Buffer Event Detection** - Identify rebuffering incidents and low buffer events
- **Playback Error Analysis** - Detect buffer underruns, startup delays, and bitrate drops
- **Session Discovery** - Enumerate unique session and content identifiers

### 🔧 **Technical Capabilities**
- Real-time streaming telemetry analysis
- Flexible time range queries (`-1h`, `-24h`, `-7d`)
- Session and content ID filtering
- Structured JSON responses for AI consumption
- Comprehensive error detection and reporting

## Prerequisites

- Python 3.8+
- InfluxDB instance with CMCD data
- Valid InfluxDB credentials
- HLS video file (.m3u8) for testing CMCD data generation

## AWS Infrastructure Deployment

### Deploy the CMCD Pipeline

The complete CMCD analytics pipeline is deployed using AWS CloudFormation, which creates:

- **Amazon S3** - Video content storage
- **Amazon CloudFront** - CDN with CMCD log collection
- **AWS Lambda** - Log processing functions
- **Amazon Timestream for InfluxDB** - CMCD metrics storage
- **Amazon EC2** - Bastion host for secure database access
- **Amazon Kinesis Data Firehose** - Real-time log streaming

### Prerequisites for Deployment

- AWS CLI configured with appropriate permissions
- AWS account with sufficient service limits
- VPC with public and private subnets (or use default VPC)

### Deploy CloudFormation Stack

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd cmcd-mcp
   ```

2. **Deploy the Stack**:
   ```bash
   aws cloudformation create-stack \
     --stack-name cmcd-analytics-pipeline \
     --template-body file://cloudformation/cmcd-pipeline.yaml \
     --parameters ParameterKey=Environment,ParameterValue=dev \
     --capabilities CAPABILITY_IAM \
     --region <REGION>
   ```

3. **Monitor Deployment**:
   ```bash
   aws cloudformation describe-stacks --stack-name cmcd-analytics-pipeline --region <REGION>
   ```

4. **Get Stack Outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name cmcd-analytics-pipeline \
     --query 'Stacks[0].Outputs'
   ```

### Key CloudFormation Outputs

| Output | Description | Usage |
|--------|-------------|-------|
| `InfluxDBEndpoint` | InfluxDB connection URL | MCP server configuration |
| `InfluxDBToken` | Database authentication token | MCP server configuration |
| `InfluxDBOrg` | Organization name | MCP server configuration |
| `S3BucketName` | Video content bucket | Upload HLS files |
| `CloudFrontDomain` | CDN domain | Video playback URLs |
| `BastionInstanceId` | EC2 bastion host ID | SSM connection |

## Managing InfluxDB Tokens

### Creating a New InfluxDB Token
1. **Open a SSM tunnel connection to the InfluxDB**:
   - Get bastion instance ID from CloudFormation outputs
   - Get InfluxDB endpoint from CloudFormation outputs
   - Run the below command by replacing the Instance ID and InfluxDB endpoint from the output
   
   ```bash
   aws ssm start-session --target <BASTION-HOST-INSTANCE-ID> --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["<INFLUX_DB_ENDPOINT>"],"portNumber":["8086"],"localPortNumber":["8086"]}' --region <REGION>
   ```
   
   Sample Command:
   ```bash
   aws ssm start-session --target i-06c116da03a889de9 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["73h2dsg42t-couyzfmko7r2io.timestream-influxdb.us-east-2.on.aws"],"portNumber":["8086"],"localPortNumber":["8086"]}' --region us-east-2
   ```

   Keep this terminal window open as it maintains the tunnel connection.

2. **Access the InfluxDB UI**:
   - Make sure that the SSM tunnel is up and accepting connections by running the previous command
   - Access the InfluxDB UI at https://localhost:8086 from any browser like Chrome

3. **Generate a New Token**:
   - Log in with your admin credentials which can be retrieved from secrets manager. The secrets starts with InfluxDBSecret-<dbinstance>
   - Enter the Username as 'admin' and password retrieved from the secrets manager
   - Navigate to "Load Data" > "API Tokens" in the left sidebar
   - Click "Generate API Token" > "All Access API Token"
     - Select the appropriate permissions:
     - For full access: Select "All Access"
     - For limited access: Select specific buckets and permissions
   - Enter a description for your token e.g. "Used for writing and querying"
   - Click "Save"
   - Copy the generated token immediately (it will only be shown once)
   - Save the InfluxDB Token as this will be used later.

4. **Update Lambda Function Environment Variables**:
   - Navigate to the AWS Lambda Console
   - Find and select your CMCD processor Lambda function (named `cmcd-analytics-dev-processor`)
   - Go to the "Configuration" tab
   - Select "Environment variables"
   - Find the `INFLUXDB_TOKEN` variable and click "Edit"
   - Update the value with your new token
   - Click "Save"

### Upload HLS Content

The CloudFormation template creates an S3 bucket for video content accessible via CloudFront:

1. **Upload HLS Video Files**:
   ```bash
   # Upload your HLS playlist and segments to the S3 bucket
   # Use the S3BucketName from CloudFormation outputs
   aws s3 cp your-video.m3u8 s3://<S3BucketName from CloudFormation outputs>/videos/
   aws s3 cp video-segments/ s3://<S3BucketName from CloudFormation outputs>/videos/ --recursive
   ```

2. **Configure the Player**:
   - Open `index.html` in the S3 bucket
   - Update the video source URL with your video path:
   ```javascript
   // Replace the source URL in web/index.html
   src: "https://<CloudFrontDomain from CloudFormation outputs>/videos/your-video.m3u8"
   ```
   If your-video.m3u8 is named as master.m3u8, then no change is needed.

3. **Generate CMCD Data**:
   - Play the video in the browser
   - The player automatically sends CMCD parameters to CloudFront
   - Streaming telemetry data will be collected and processed into InfluxDB

## Integration with Amazon Q CLI

To use this MCP server with Amazon Q CLI, you need to configure the MCP settings:

### 1. Install Required Dependencies

```bash
# Navigate to the CMCD directory
cd /<DirectoryPath>/cmcd/
pip install -r mcp/requirements.txt
```

### 2. Configure Environment

Update the `mcp/.env` file in the project mcp using values from your CloudFormation stack outputs:

```bash
INFLUXDB_URL=https://localhost:8086
INFLUXDB_TOKEN=<InfluxDBToken generated previously from the InfluxDB UI>
INFLUXDB_ORG=<InfluxDBOrg from secrets manager e.g. cmcd-org>
VERIFY_SSL=false
```

### 3. Verify the MCP Configuration File

The file at `mcp/mcp.json` should have the following content:
```json
{
  "mcpServers": {
    "cmcd-mcp": {
      "command": "python3",
      "args": ["cmcd_server.py"],
      "cwd": "<DIRECTORY_PATH>",
      "env": {
        "FASTMCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```
Example mcp.json

```json

{
  "mcpServers": {
    "cmcd-mcp": {
      "command": "python3",
      "args": ["cmcd_server.py"],
      "cwd": "/Users/johndoe/Downloads/cmcd/mcp",
      "env": {
        "FASTMCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```
### 4. Copy the mcp.json File to Q CLI Directory

```bash
cp mcp/mcp.json ~/.aws/amazonq/mcp.json
```

### OR based on your directory structure:

```bash
cp mcp.json ~/.q/mcp.json
```

### Make sure that the files in the mcp directory have execute permissions:

```bash
chmod +x mcp/*
```
### 5. Connect via AWS SSM (Bastion Host)

The InfluxDB instance is typically deployed in a private subnet and requires connection through a bastion host.
If the SSM connection which was started previously has closed, then start the session again:

- Run the below command by replacing the Instance ID and InfluxDB endpoint from the output
  ```bash
  aws ssm start-session --target <BASTION-HOST-INSTANCE-ID> --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["<INFLUX_DB_ENDPOINT>"],"portNumber":["8086"],"localPortNumber":["8086"]}' --region <REGION>
  ```
  
  Sample Command:
  ```bash
  aws ssm start-session --target i-06c116da03a889de9 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["73h2dsg42t-couyzfmko7r2io.timestream-influxdb.us-east-2.on.aws"],"portNumber":["8086"],"localPortNumber":["8086"]}' --region us-east-2
  ```

  Keep this terminal window open as it maintains the tunnel connection.


### Running Amazon Q CLI

Enter into chat mode with the CLI:

```bash
# Run Q CLI
q chat
```

Once configured, Amazon Q can analyze your CMCD streaming data and provide insights about:

- Streaming performance trends
- Quality issues and their root causes
- User experience metrics
- Session and content correlations

## Usage Examples

### Example 1: Query Bitrate Information
```
Q: What is the bitrate in last 1 hour?
```

### Example 2: Request Performance Insights
```
Q: Provide insights on the streaming performance
```

### Example Output:

```
Based on the data I've gathered, here are the key insights on streaming performance:

## Streaming Performance Summary

### Bitrate Analysis
- Average Bitrate: 3,566 kbps (3.57 Mbps)
- This indicates a relatively high-quality stream, suitable for HD content

### Buffer Events
- Total Buffer Events: 947 events recorded in the last 24 hours
- Low Buffer Events: 0 (below the 500ms threshold)
- This suggests that while there are many buffer-related events, none have reached critically low levels

### Playback Errors
- Total Errors: 53 detected in the last 24 hours
- Error Type: All errors are "sudden_buffer_drop" events
- Severity: All errors are classified as "medium" severity

### Buffer Drop Analysis
- Most significant drops:
  - 101,400ms → 10,400ms (91% drop)
  - 101,200ms → 31,100ms (69% drop)
  - 100,800ms → 36,700ms (64% drop)
- These sudden buffer drops could cause momentary quality degradation or brief pauses

### Content and Session Information
- Active Sessions: 1 unique session ID (session_md91ykdl5yrcwq371f5)
- Content: 1 unique content ID (video-content-demo)

## Performance Insights

1. Overall Quality: The average bitrate of 3.57 Mbps indicates good streaming quality, likely delivering HD content to viewers.

2. Buffer Health: While there are numerous buffer events, the system is maintaining adequate buffer levels above the critical threshold of 500ms, preventing playback interruptions.

3. Playback Stability Issues: The 53 sudden buffer drop events suggest network fluctuations or adaptive bitrate switching. These drops could cause momentary quality degradation but aren't causing complete playback failures.

4. Pattern Analysis: Buffer drops are clustered around specific time periods (notably around 16:47-16:58 and 18:09-18:33), suggesting potential network congestion during these times.

5. Buffer Management: The system appears to maintain large buffers (often 60,000-100,000ms) before drops occur, which helps prevent actual rebuffering events despite the drops.

## Recommendations

1. Optimize ABR Logic: Review the adaptive bitrate switching logic to make smoother transitions that don't cause such dramatic buffer drops.

2. Network Analysis: Investigate network conditions during the time periods with clustered buffer drops to identify potential bottlenecks.

3. Buffer Strategy: Consider adjusting the buffer strategy to maintain more consistent buffer levels rather than allowing very large buffers that then experience dramatic drops.

4. Session Monitoring: Set up alerts for when buffer drops exceed 70% to proactively address potential streaming issues.

5. Content Delivery Optimization: Analyze edge location performance to ensure optimal content delivery across all regions.

The streaming service is performing adequately with good bitrates, but the buffer stability could be improved to provide a more consistent viewing experience.
```

## Data Schema

The server expects CMCD data in InfluxDB with the following structure:

| Component | Value | Description |
|-----------|-------|-------------|
| **Bucket** | `cmcd-metrics` | InfluxDB bucket containing CMCD data |
| **Measurement** | `cloudfront_logs` | Primary measurement name |

### CMCD Fields

| Field | Description | Unit |
|-------|-------------|------|
| `cmcd_bl` | Buffer length | milliseconds |
| `cmcd_br` | Encoded bitrate | kbps |
| `cmcd_d` | Segment duration | milliseconds |
| `cmcd_su` | Startup flag | boolean |
| `cmcd_tb` | Top bitrate | kbps |
| `cmcd_bs` | Buffer starved flag | boolean |
| `cmcd_mtp` | Measured throughput | kbps |

### Tags

| Tag | Description |
|-----|-------------|
| `cmcd_sid` | Session identifier |
| `cmcd_cid` | Content identifier |
| `edge_location` | CDN edge location |

## Available Tools

### `get_average_bitrate`
Calculates average bitrate over specified time ranges with optional filtering.

**Parameters:**
- `time_range` (default: "-24h"): Time range for analysis
- `cmcd_sid` (optional): Filter by session ID
- `cmcd_cid` (optional): Filter by content ID

### `get_session_details`
Retrieves comprehensive metrics timeline for a specific session.

**Parameters:**
- `cmcd_sid` (required): Session ID to analyze
- `time_range` (default: "-24h"): Time range for analysis

### `analyze_buffer_events`
Identifies potential rebuffering events based on buffer level thresholds.

**Parameters:**
- `time_range` (default: "-24h"): Time range for analysis
- `cmcd_sid` (optional): Filter by session ID
- `threshold_ms` (default: 500): Buffer level threshold in milliseconds

### `identify_playback_errors`
Detects various playback issues including buffer underruns and startup delays.

**Parameters:**
- `time_range` (default: "-24h"): Time range for analysis
- `cmcd_sid` (optional): Filter by session ID

### `list_session_and_content_ids`
Enumerates unique session and content identifiers in the dataset.

**Parameters:**
- `time_range` (default: "-24h"): Time range for analysis
- `limit` (default: 100): Maximum number of IDs to return


## Troubleshooting

### Common Issues

1. **Connection Errors**: 
   - Verify InfluxDB URL and credentials
   - Ensure SSM port forwarding is active
   - Check bastion host security groups allow port 8086
   - Ensure the URL in mcp/.env file has https and not http

2. **No Data Returned**: 
   - Check bucket name and measurement structure
   - Verify CMCD data is being generated by video player
   - Confirm CloudFront logs are being processed into InfluxDB

3. **Schema Errors**: 
   - Ensure CMCD fields match expected format
   - Verify tag names use `cmcd_sid` and `cmcd_cid`

4. **SSM Connection Issues**:
   ```bash
   # Check SSM agent status using bastion instance ID from CloudFormation
   aws ssm describe-instance-information --filters "Key=InstanceIds,Values=<BastionInstanceId>"
   
   # Verify IAM permissions for SSM
   aws sts get-caller-identity
   ```

### Logging

Logs are written to `cmcd_server.log` with rotation at 10MB. Check logs for detailed error information.

## Contributing

Contributions are welcome! Please ensure:

1. Code follows existing patterns
2. New tools include proper documentation
3. Error handling is comprehensive
4. Tests cover new functionality

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [CloudFront CMCD Real-time Dashboard](https://github.com/aws-samples/cloudfront-cmcd-realtime-dashboard)
- [CMCD Specification (CTA-5004)](https://www.cta.tech/Resources/Standards)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

**Note**: This server focuses on analytics and does not include direct InfluxDB query capabilities. For custom Flux queries, consider the companion InfluxDB MCP server.
