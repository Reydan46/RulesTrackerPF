import datetime
import os
import pickle

__cache_folder = "cache_data"


def cache_get(cache_file, days=0, hours=0, minutes=0):
    cache_expiry = datetime.timedelta(days=days, hours=hours, minutes=minutes)
    cache_file = os.path.join(__cache_folder, cache_file)
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as file:
            cache_data = pickle.load(file)
            timestamp = cache_data.get("timestamp")
            if (
                    cache_data is not None
                    and "timestamp" in cache_data
                    and isinstance(timestamp, datetime.datetime)
                    and datetime.datetime.now() - timestamp <= cache_expiry
                    and "value" in cache_data
            ):
                return cache_data["value"]
    return None


def cache_set(value, cache_file):
    cache_file = os.path.join(__cache_folder, cache_file)
    cache_data = {"value": value, "timestamp": datetime.datetime.now()}

    if not os.path.exists(__cache_folder):
        os.makedirs(__cache_folder)

    with open(cache_file, "wb") as file:
        pickle.dump(cache_data, file)
