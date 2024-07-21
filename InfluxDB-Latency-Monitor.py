import re
import asyncio
from pythonping import ping
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

###########################################################################
# Extract target IPs from the text file

def extract_targets_from_config(file_path):
    targets = []
    with open(file_path, 'r') as file:
        config = file.read()
        matches = re.findall(r'host\s*=\s*([\d\.]+)', config)
        targets = [match for match in matches]
        print(targets)
    return targets

###########################################################################
# Ping a target and return latency and packet loss

async def ping_target_async(target):
    responses = await asyncio.to_thread(ping, target, count=20, timeout=4, verbose=False)

    # Check if there were successful responses
    if responses.rtt_min is None:
        avg_latency = None
        packet_loss = 100.0 
    else:
        avg_latency = round(responses.rtt_avg * 1000)
        packet_loss = responses.packet_loss * 100.0

    return avg_latency, packet_loss

###########################################################################
# Insert data into InfluxDB 

async def update_async(host, client, bucket):
    avg_latency, packet_loss = await ping_target_async(host)

    if avg_latency is not None:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        point = (
            Point("latency")
            .tag("host", host)
            .field("latency", avg_latency)
            .field("packet_loss", packet_loss)  
        )
        write_api.write(bucket=bucket, org="Networks", record=point, write_precision=WritePrecision.NS)

###########################################################################
# Initialize InfluxDB client

client = InfluxDBClient(url="http://localhost:8086", token="", org="Networks", debug=False)
bucket = "Bucket1"

###########################################################################
# Initialize data sources

targets = extract_targets_from_config("server_ips_config.txt")

async def main():
    while True:
        tasks = [update_async(target, client, bucket) for target in targets]
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())