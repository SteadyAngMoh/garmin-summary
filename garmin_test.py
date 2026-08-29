import os
from datetime import date
from garminconnect import Garmin

email = os.environ["GARMIN_EMAIL"]
password = os.environ["GARMIN_PASSWORD"]

client = Garmin(email, password)
client.login()

today = date.today().isoformat()

print(f"Connected to Garmin successfully")
print(f"Fetching stats for {today}...")

stats = client.get_stats(today)

print("Steps:", stats.get("totalSteps"))
print("Resting HR:", stats.get("restingHeartRate"))
print("Stress:", stats.get("averageStressLevel"))
print("Body Battery high:", stats.get("bodyBatteryHighestValue"))
print("Body Battery low:", stats.get("bodyBatteryLowestValue"))

sleep = client.get_sleep_data(today)

print("Sleep score:", sleep.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value"))
print("Sleep seconds:", sleep.get("dailySleepDTO", {}).get("sleepTimeSeconds"))

print("Garmin test complete")
