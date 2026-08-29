from datetime import date
from garminconnect import Garmin

TOKEN_DIR = "~/.garminconnect"

client = Garmin()
client.login(TOKEN_DIR)

today = date.today().isoformat()

stats = client.get_stats(today)
sleep = client.get_sleep_data(today)

sleep_dto = sleep.get("dailySleepDTO", {})
sleep_scores = sleep_dto.get("sleepScores", {})
overall_sleep = sleep_scores.get("overall", {})

sleep_seconds = sleep_dto.get("sleepTimeSeconds")
sleep_hours = round(sleep_seconds / 3600, 2) if sleep_seconds else None

print(f"Garmin summary for {today}")
print("-------------------------")
print("Steps:", stats.get("totalSteps"))
print("Resting HR:", stats.get("restingHeartRate"))
print("Average stress:", stats.get("averageStressLevel"))
print("Body Battery high:", stats.get("bodyBatteryHighestValue"))
print("Body Battery low:", stats.get("bodyBatteryLowestValue"))
print("Sleep score:", overall_sleep.get("value"))
print("Sleep hours:", sleep_hours)
