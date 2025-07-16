# CMCD MCP Server

Model Context Protocol (MCP) server for analyzing Common Media Client Data (CMCD) streaming telemetry stored in InfluxDB.

## Overview

This server provides pre-built analytics tools for CMCD streaming performance data, enabling analysis of video streaming quality of experience (QoE) metrics including bitrates, buffer levels, startup delays, and playback errors.

## Features

- **Average Bitrate Analysis** - Calculate mean bitrates across time ranges
- **Session Details** - Retrieve comprehensive session metrics and timelines  
- **Buffer Event Analysis** - Identify rebuffering incidents and low buffer events
- **Playback Error Detection** - Detect buffer underruns, startup delays, and bitrate drops
- **Session/Content ID Listing** - Enumerate unique identifiers in the dataset

## Setup

### Environment Variables

Create a `.env` file:

```
INFLUXDB_URL=https://your-influxdb-instance:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=your-org
VERIFY_SSL=false
```

### Installation

```bash
pip install -r requirements.txt
```

### Running

```bash
python mcp/cmcd_server.py
```

## Data Schema

- **Bucket**: `cmcd-metrics`
- **Measurement**: `cloudfront_logs`
- **Fields**: 
  - `cmcd_bl` - Buffer length (ms)
  - `cmcd_br` - Encoded bitrate (kbps)
  - `cmcd_d` - Segment duration (ms)
  - `cmcd_su` - Startup flag
  - `cmcd_tb` - Top bitrate (kbps)
- **Tags**: `cmcd_sid` (session ID), `cmcd_cid` (content ID)

## Tools

### get_average_bitrate
Calculate average bitrate over time range, optionally filtered by session or content ID.

### get_session_details  
Retrieve detailed metrics timeline for a specific session ID.

### analyze_buffer_events
Identify potential rebuffering events where buffer drops below threshold.

### identify_playback_errors
Detect buffer underruns, startup delays, and sudden bitrate drops.

### list_session_and_content_ids
List unique session and content identifiers in the dataset.

## Usage Examples

The server integrates with MCP clients to provide streaming analytics capabilities. Tools accept time ranges (e.g., `-1h`, `-24h`, `-7d`) and optional filtering parameters.