import requests
from datetime import datetime, timedelta
from mongo import insert_data
import schedule
import time
from metricsPromet import (
    api_requests,
    api_successful_requests,
    api_failed_requests,
    api_data_read,
    api_request_duration,
    api_temperature,
    api_pressure,
    api_humidity,
    api_aqi,
    api_iaqi,
    api_pm25,
    api_pm10,
    api_pm25_mcp
)

def get_formatted_time(hours_ago):
    return (datetime.utcnow() - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")

@api_request_duration.time()
def fetch_data(api_url, collection, time_begin, time_end):
    params = {
        "sites": "3837",
        "time_begin": time_begin,
        "time_end": time_end,
        "time_interval": "hour"
    }
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        if 'data' in data:
            data_count = len(data['data'])
            api_data_read.inc(data_count)
            for entry in data['data']:

                insert_data(collection, entry)


                api_temperature.set(entry.get('t', 0))
                api_pressure.set(entry.get('p', 0))
                api_humidity.set(entry.get('h', 0))
                api_aqi.set(entry.get('aqi', 0))
                api_iaqi.set(entry.get('iaqi', 0))
                api_pm25.set(entry.get('pm25', 0))
                api_pm10.set(entry.get('pm10', 0))
                api_pm25_mcp.set(entry.get('pm25_mcp', 0))

            api_successful_requests.inc()
        else:
            print(f"No 'data' field in the API response. Response: {data}")
            api_failed_requests.inc()
    except requests.RequestException as e:
        print(f"Failed to fetch data from API for time range {time_begin} to {time_end}: {e}")
        api_failed_requests.inc()

def fetch_initial_data(api_url, collection):
    time_end = get_formatted_time(0)
    time_begin = get_formatted_time(2)
    fetch_data(api_url, collection, time_begin, time_end)

def fetch_and_store_api_data(api_url, collection):
    api_requests.inc()
    time_end = get_formatted_time(0)
    time_begin = get_formatted_time(1)
    fetch_data(api_url, collection, time_begin, time_end)

def start_api_client(api_url, collection):
    fetch_initial_data(api_url, collection)
    schedule.every().hour.at(":00").do(fetch_and_store_api_data, api_url, collection)
    while True:
        schedule.run_pending()
        time.sleep(1)