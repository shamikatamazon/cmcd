import json
import base64
import boto3
import os
from datetime import datetime
import urllib.parse

timestream = boto3.client('timestream-write')

DATABASE_NAME = os.environ['TIMESTREAM_DATABASE']
TABLE_NAME = os.environ['TIMESTREAM_TABLE']

def lambda_handler(event, context):
    records = []
    
    for record in event['Records']:
        # Decode Kinesis data
        payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
        log_data = parse_cloudfront_log(payload)
        
        if log_data and log_data.get('cmcd_data'):
            records.extend(create_timestream_records(log_data))
    
    if records:
        timestream.write_records(
            DatabaseName=DATABASE_NAME,
            TableName=TABLE_NAME,
            Records=records
        )
    
    return {'statusCode': 200, 'body': f'Processed {len(records)} records'}

def parse_cloudfront_log(log_line):
    fields = log_line.strip().split('\t')
    if len(fields) < 10:
        return None
    
    headers = urllib.parse.unquote(fields[6]) if len(fields) > 6 else ''
    cmcd_data = extract_cmcd_headers(headers)
    
    return {
        'timestamp': int(float(fields[0]) * 1000),  # Convert to milliseconds
        'client_ip': fields[1],
        'status': fields[2],
        'uri': fields[4],
        'time_taken': int(fields[7]) if fields[7].isdigit() else 0,
        'edge_location': fields[8],
        'cmcd_data': cmcd_data
    }

def extract_cmcd_headers(headers_str):
    cmcd_data = {}
    for header in headers_str.split('\n'):
        if 'CMCD-' in header:
            parts = header.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip().replace('CMCD-', '').lower()
                value = parts[1].strip()
                cmcd_data[key] = parse_cmcd_value(value)
    return cmcd_data

def parse_cmcd_value(value):
    # Parse CMCD key-value pairs
    parsed = {}
    for pair in value.split(','):
        if '=' in pair:
            k, v = pair.split('=', 1)
            parsed[k.strip()] = v.strip().strip('"')
    return parsed

def create_timestream_records(log_data):
    records = []
    timestamp = str(log_data['timestamp'])
    
    # Base dimensions
    dimensions = [
        {'Name': 'client_ip', 'Value': log_data['client_ip']},
        {'Name': 'edge_location', 'Value': log_data['edge_location']},
        {'Name': 'status', 'Value': log_data['status']}
    ]
    
    # Add time taken metric
    records.append({
        'Time': timestamp,
        'TimeUnit': 'MILLISECONDS',
        'Dimensions': dimensions,
        'MeasureName': 'time_taken',
        'MeasureValue': str(log_data['time_taken']),
        'MeasureValueType': 'BIGINT'
    })
    
    # Add CMCD metrics
    for cmcd_type, cmcd_values in log_data['cmcd_data'].items():
        for key, value in cmcd_values.items():
            if value.isdigit():
                records.append({
                    'Time': timestamp,
                    'TimeUnit': 'MILLISECONDS',
                    'Dimensions': dimensions + [{'Name': 'cmcd_type', 'Value': cmcd_type}],
                    'MeasureName': f'cmcd_{key}',
                    'MeasureValue': value,
                    'MeasureValueType': 'BIGINT'
                })
    
    return records