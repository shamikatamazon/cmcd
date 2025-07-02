# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import boto3
import os
from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.write.point import Point
from influxdb_client.client.write_api import ASYNCHRONOUS, SYNCHRONOUS
from influxdb_client.domain.write_precision import WritePrecision
import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")
logger.add("cmcd_server.log", rotation="10 MB", level="DEBUG")
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get the environment variables
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
VERIFY_SSL = os.getenv('VERIFY_SSL', 'False').lower() == 'true'


# Define Field parameters as global variables to avoid duplication
# Common fields

mcp = FastMCP(
    'cmcd-mcp',
    instructions="""
    This MCP server provides tools to query and analyze Common Media Client Data (CMCD) metrics stored in InfluxDB.
    
    CMCD is a standard defined by the Consumer Technology Association (CTA) that enables media players to communicate
    standardized playback telemetry to content delivery networks (CDNs) and origin servers. This server allows you to:
    
    1. Get average bitrate statistics with the get_average_bitrate tool
    2. Retrieve detailed session information with the get_session_details tool
    3. Analyze buffer-related events with the analyze_buffer_events tool
    4. Identify potential playback errors with the identify_playback_errors tool
    5. Analyze metrics by edge location with the get_edge_location_stats tool
    
    The server analyzes streaming performance data including buffer levels (bl), bitrates (br), duration (d),
    media type (mtp), startup (su), and target buffer (tb) to generate insights about streaming quality of experience (QoE).
    
    Data is stored in the 'cmcd-metrics' database with measurements in 'cloudfront_logs'. Edge location information
    is available as the 'edge_location' field for geographic analysis.
    """,
    dependencies=['loguru', 'boto3', 'influxdb-client'],
)


def get_influxdb_client(url, token, org=None, timeout=10000, verify_ssl: bool = False):
    """Get an InfluxDB client.

    Args:
        url: The URL of the InfluxDB server e.g. https://<host-name>:8086.
        token: The authentication token.
        org: The organization name.
        timeout: The timeout in milliseconds.
        verify_ssl: whether to verify SSL with https connections

    Returns:
        An InfluxDB client.

    Raises:
        ValueError: If the URL does not use HTTPS protocol or is not properly formatted.
    """
    try:
        parsed_url = urlparse(url)
        url_scheme = parsed_url.scheme
        if url_scheme != 'https' and url_scheme != 'http':
            raise ValueError('URL must use HTTP(S) protocol')
    except Exception as e:
        logger.error(f'Error parsing URL: {str(e)}')
        raise

    if not token:
        raise ValueError('Token must be provided')

    # Ensure org is not None when passed to InfluxDBClient
    org_param = org if org is not None else ''

    # Connect to the InfluxDB client
    return InfluxDBClient(
        url=url, token=token, org=org_param, timeout=timeout, verify_ssl=verify_ssl
    )

async def get_cmcd_data(query: str, url: str = INFLUXDB_URL, token: str = INFLUXDB_TOKEN, 
                      org: str = INFLUXDB_ORG, verify_ssl: bool = VERIFY_SSL) -> Dict[str, Any]:
    """Helper function to query data from InfluxDB using Flux query language."""
    logger.debug(f"Executing InfluxDB query: {query}")
    logger.debug(f"InfluxDB connection details: URL={url}, ORG={org}, VERIFY_SSL={verify_ssl}")
    
    try:
        client = get_influxdb_client(url, token, org, verify_ssl)
        query_api = client.query_api()

        # Return as JSON
        tables = query_api.query(org=org, query=query)
        logger.debug(f"Query executed successfully, processing results")
        
        # Process the tables into a more usable format
        result = []
        for table in tables:
            for record in table.records:
                # Log the raw record for debugging
                logger.debug(f"Raw record: {record}")
                logger.debug(f"Record values: {record.values}")
                
                # Extract values safely with fallbacks
                record_data = {}
                
                # Try to get standard fields
                try:
                    record_data['measurement'] = record.get_measurement()
                except Exception:
                    record_data['measurement'] = None
                    
                try:
                    record_data['field'] = record.get_field()
                except Exception:
                    record_data['field'] = None
                    
                # For mean queries, the value might be in _value instead of a named field
                try:
                    if '_value' in record.values:
                        record_data['value'] = record.values.get('_value')
                    else:
                        record_data['value'] = record.get_value()
                except Exception as e:
                    logger.debug(f"Error getting value: {e}")
                    # Try to find any value field in the record
                    for key, val in record.values.items():
                        if key.endswith('value') or key == '_value':
                            record_data['value'] = val
                            break
                    else:
                        record_data['value'] = None
                
                try:
                    record_data['time'] = record.get_time().isoformat() if record.get_time() else None
                except Exception:
                    record_data['time'] = None
                    
                record_data['tags'] = record.values.get('tags', {})
                
                # Include all raw values for debugging and flexibility
                record_data['raw_values'] = dict(record.values)
                
                result.append(record_data)
                logger.debug(f"Processed record: {record_data}")

        client.close()
        logger.info(f"Query returned {len(result)} records")
        return {'status': 'success', 'result': result, 'format': 'json'}

    except Exception as e:
        logger.error(f'Error querying InfluxDB: {str(e)}')
        return {'status': 'error', 'message': str(e)}

@mcp.tool(name='get_average_bitrate', description='Get average bitrate from CMCD metrics')
async def get_average_bitrate(
    time_range: str = Field(default="-24h", description="Time range for the query (e.g., -1h, -24h, -7d)"),
    session_id: str = Field(default=None, description="Optional session ID to filter by"),
    content_id: str = Field(default=None, description="Optional content ID to filter by")
) -> Dict[str, Any]:
    """Get the average bitrate from CMCD metrics over the specified time range.
    
    Returns:
        Average bitrate in kbps and related statistics.
    """
    logger.info(f"Getting average bitrate for time_range={time_range}, session_id={session_id}, content_id={content_id}")
    
    # Try a simpler query first to check if data exists
    check_query = f'''
    from(bucket: "cmcd-metrics")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_measurement"] == "cloudfront_logs")
      |> filter(fn: (r) => r["_field"] == "cmcd_br")
      |> limit(n: 1)
    '''
    
    check_result = await get_cmcd_data(check_query)
    logger.debug(f"Check query result: {check_result}")
    
    if check_result['status'] != 'success' or not check_result['result']:
        logger.warning("No bitrate data found in initial check")
        # Try with a different bucket name
        check_query = f'''
        from(bucket: "cmcd_metrics")
          |> range(start: {time_range})
          |> filter(fn: (r) => r["_measurement"] == "cloudfront_logs")
          |> filter(fn: (r) => r["_field"] == "cmcd_br")
          |> limit(n: 1)
        '''
        check_result = await get_cmcd_data(check_query)
        logger.debug(f"Second check query result: {check_result}")
        
        if check_result['status'] != 'success' or not check_result['result']:
            logger.warning("No bitrate data found in second check either")
            # List available buckets
            buckets_query = '''
            buckets()
            '''
            buckets_result = await get_cmcd_data(buckets_query)
            logger.info(f"Available buckets: {buckets_result}")
            return {'status': 'error', 'message': 'No bitrate data found. Please check database configuration.'}
    
    # Determine which bucket name to use
    bucket_name = "cmcd-metrics"
    if check_result['status'] == 'success' and check_result['result']:
        # Use the bucket that worked in the check query
        if "cmcd_metrics" in check_query:
            bucket_name = "cmcd_metrics"
    
    # Now build the actual query
    query = f'''
    from(bucket: "{bucket_name}")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_measurement"] == "cloudfront_logs")
      |> filter(fn: (r) => r["_field"] == "cmcd_br")
    '''
    
    if session_id:
        query += f'  |> filter(fn: (r) => r["session_id"] == "{session_id}")\n'
    
    if content_id:
        query += f'  |> filter(fn: (r) => r["content_id"] == "{content_id}")\n'
    
    query += '''
      |> group()
      |> mean()
      |> yield(name: "mean_bitrate")
    '''
    
    logger.debug(f"Final query: {query}")
    result = await get_cmcd_data(query)
    logger.debug(f"Final query result: {result}")
    
    if result['status'] == 'success' and result['result']:
        # Try to extract the average bitrate value from the result
        try:
            # First check if we have a value directly
            if 'value' in result['result'][0] and result['result'][0]['value'] is not None:
                avg_bitrate = result['result'][0]['value']
            # Then check in raw_values for _value
            elif 'raw_values' in result['result'][0] and '_value' in result['result'][0]['raw_values']:
                avg_bitrate = result['result'][0]['raw_values']['_value']
            # Finally check all raw_values for anything that might be a value
            else:
                for key, val in result['result'][0]['raw_values'].items():
                    if isinstance(val, (int, float)) and key != 'table':
                        avg_bitrate = val
                        logger.debug(f"Found value in field {key}: {val}")
                        break
                else:
                    raise ValueError("Could not find a numeric value in the result")
                    
            logger.info(f"Successfully calculated average bitrate: {avg_bitrate} kbps")
            return {
                'status': 'success',
                'average_bitrate_kbps': avg_bitrate,
                'time_range': time_range,
                'session_id': session_id,
                'content_id': content_id,
                'bucket_used': bucket_name,
                'raw_result': result['result'][0]['raw_values'] if 'raw_values' in result['result'][0] else {}
            }
        except Exception as e:
            logger.error(f"Error extracting average bitrate: {e}")
            logger.debug(f"Result structure: {result}")
            return {
                'status': 'error',
                'message': f'Error extracting average bitrate: {str(e)}',
                'raw_result': result['result']
            }
    else:
        logger.error("Failed to calculate average bitrate")
        return {
            'status': 'error', 
            'message': 'No bitrate data found for the specified criteria',
            'query_used': query,
            'bucket_tried': bucket_name
        }

@mcp.tool(name='get_session_details', description='Get detailed information about a streaming session')
async def get_session_details(
    session_id: str = Field(..., description="Session ID to analyze"),
    time_range: str = Field(default="-24h", description="Time range for the query (e.g., -1h, -24h, -7d)")
) -> Dict[str, Any]:
    """Get detailed information about a specific streaming session including bitrate changes,
    buffer levels, and other CMCD metrics.
    
    Returns:
        Detailed session information and metrics.
    """
    query = f'''
    from(bucket: "cmcd-metrics")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_measurement"] == "cloudfront_logs")
      |> filter(fn: (r) => r["session_id"] == "{session_id}")
      |> sort(columns: ["_time"])
    '''
    
    result = await get_cmcd_data(query)
    
    if result['status'] == 'success' and result['result']:
        # Process and organize session data
        session_data = {
            'session_id': session_id,
            'start_time': result['result'][0]['time'],
            'end_time': result['result'][-1]['time'],
            'metrics': {}
        }
        
        # Group metrics by field
        for record in result['result']:
            field = record['field']
            if field not in session_data['metrics']:
                session_data['metrics'][field] = []
            
            session_data['metrics'][field].append({
                'time': record['time'],
                'value': record['value']
            })
        
        return {'status': 'success', 'session_data': session_data}
    else:
        return {'status': 'error', 'message': f'No data found for session ID: {session_id}'}

@mcp.tool(name='analyze_buffer_events', description='Analyze buffer-related events from CMCD metrics')
async def analyze_buffer_events(
    time_range: str = Field(default="-24h", description="Time range for the query (e.g., -1h, -24h, -7d)"),
    session_id: str = Field(default=None, description="Optional session ID to filter by"),
    threshold_ms: int = Field(default=500, description="Buffer level threshold in milliseconds")
) -> Dict[str, Any]:
    """Analyze buffer-related events from CMCD metrics, identifying potential rebuffering events
    where buffer level drops below the specified threshold.
    
    Returns:
        Analysis of buffer events and potential rebuffering incidents.
    """
    query = f'''
    from(bucket: "cmcd-metrics")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_measurement"] == "cloudfront_logs")
      |> filter(fn: (r) => r["_field"] == "cmcd_bl")
    '''
    
    if session_id:
        query += f'  |> filter(fn: (r) => r["session_id"] == "{session_id}")\n'
    
    query += '''
      |> sort(columns: ["_time"])
    '''
    
    result = await get_cmcd_data(query)
    
    if result['status'] == 'success' and result['result']:
        # Analyze buffer events
        buffer_events = []
        low_buffer_events = []
        
        for i, record in enumerate(result['result']):
            buffer_level = record['value']
            event = {
                'time': record['time'],
                'buffer_level_ms': buffer_level,
                'session_id': record['tags'].get('session_id', 'unknown')
            }
            buffer_events.append(event)
            
            # Identify low buffer events
            if buffer_level < threshold_ms:
                low_buffer_events.append(event)
        
        return {
            'status': 'success',
            'total_buffer_events': len(buffer_events),
            'low_buffer_events': len(low_buffer_events),
            'low_buffer_events_details': low_buffer_events,
            'threshold_ms': threshold_ms
        }
    else:
        return {'status': 'error', 'message': 'No buffer level data found for the specified criteria'}

@mcp.tool(name='identify_playback_errors', description='Identify potential playback errors from CMCD metrics')
async def identify_playback_errors(
    time_range: str = Field(default="-24h", description="Time range for the query (e.g., -1h, -24h, -7d)"),
    session_id: str = Field(default=None, description="Optional session ID to filter by")
) -> Dict[str, Any]:
    """Identify potential playback errors by analyzing patterns in CMCD metrics such as
    sudden bitrate drops, buffer underruns, or unusual startup delays.
    
    Returns:
        Analysis of potential playback errors and their causes.
    """
    # Query for buffer levels to detect underruns
    buffer_query = f'''
    from(bucket: "cmcd-metrics")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_measurement"] == "cloudfront_logs")
      |> filter(fn: (r) => r["_field"] == "cmcd_bl")
    '''
    
    if session_id:
        buffer_query += f'  |> filter(fn: (r) => r["session_id"] == "{session_id}")\n'
    
    buffer_query += '  |> sort(columns: ["_time"])\n'
    
    # Query for startup delays
    startup_query = f'''
    from(bucket: "cmcd-metrics")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_measurement"] == "cloudfront_logs")
      |> filter(fn: (r) => r["_field"] == "cmcd_su")
    '''
    
    if session_id:
        startup_query += f'  |> filter(fn: (r) => r["session_id"] == "{session_id}")\n'
    
    startup_query += '  |> sort(columns: ["_time"])\n'
    
    # Execute queries
    buffer_result = await get_cmcd_data(buffer_query)
    startup_result = await get_cmcd_data(startup_query)
    
    errors = []
    
    # Analyze buffer underruns
    if buffer_result['status'] == 'success' and buffer_result['result']:
        prev_buffer = None
        for record in buffer_result['result']:
            current_buffer = record['value']
            
            # Detect buffer underruns (buffer level drops to zero or very low)
            if current_buffer < 100:  # Less than 100ms is considered critical
                errors.append({
                    'type': 'buffer_underrun',
                    'time': record['time'],
                    'buffer_level_ms': current_buffer,
                    'session_id': record['tags'].get('session_id', 'unknown'),
                    'severity': 'high' if current_buffer == 0 else 'medium'
                })
            
            # Detect sudden buffer drops
            if prev_buffer is not None and prev_buffer > 1000 and current_buffer < prev_buffer * 0.5:
                errors.append({
                    'type': 'sudden_buffer_drop',
                    'time': record['time'],
                    'previous_buffer_ms': prev_buffer,
                    'current_buffer_ms': current_buffer,
                    'session_id': record['tags'].get('session_id', 'unknown'),
                    'severity': 'medium'
                })
            
            prev_buffer = current_buffer
    
    # Analyze startup delays
    if startup_result['status'] == 'success' and startup_result['result']:
        for record in startup_result['result']:
            startup_delay = record['value']
            
            # Detect excessive startup delays (over 2 seconds)
            if startup_delay > 2000:
                errors.append({
                    'type': 'excessive_startup_delay',
                    'time': record['time'],
                    'startup_delay_ms': startup_delay,
                    'session_id': record['tags'].get('session_id', 'unknown'),
                    'severity': 'high' if startup_delay > 5000 else 'medium'
                })
    
    return {
        'status': 'success',
        'total_errors': len(errors),
        'errors': errors,
        'time_range': time_range,
        'session_id': session_id
    }


def main():
    """Main entry point for the MCP server application."""
    logger.info('Starting CMCD MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()