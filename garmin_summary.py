import json
from datetime import date, timedelta, datetime
from garminconnect import Garmin

TOKEN_DIR = "~/.garminconnect"


def safe_get(data, *keys, default=None):
    """Safely walk through nested dictionaries."""
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def seconds_to_hours(seconds):
    if seconds is None:
        return None

    return round(seconds / 3600, 2)


def get_day(client, day):
    day_string = day.isoformat()

    stats = client.get_stats(day_string)

    try:
        sleep = client.get_sleep_data(day_string)
    except Exception as exc:
        print(f"Warning: sleep unavailable for {day_string}: {exc}")
        sleep = {}

    try:
        hrv = client.get_hrv_data(day_string)
    except Exception as exc:
        print(f"Warning: HRV unavailable for {day_string}: {exc}")
        hrv = {}

    sleep_dto = sleep.get("dailySleepDTO", {})

    return {
        "date": day_string,

        "steps": stats.get("totalSteps"),

        "heart_rate": {
            "resting_bpm": stats.get("restingHeartRate"),
            "min_bpm": stats.get("minHeartRate"),
            "max_bpm": stats.get("maxHeartRate"),
        },

        "stress": {
            "average": stats.get("averageStressLevel"),
            "max": stats.get("maxStressLevel"),
        },

        "body_battery": {
            "highest": stats.get("bodyBatteryHighestValue"),
            "lowest": stats.get("bodyBatteryLowestValue"),
        },

        "sleep": {
            "seconds": sleep_dto.get("sleepTimeSeconds"),
            "hours": seconds_to_hours(
                sleep_dto.get("sleepTimeSeconds")
            ),
            "start": sleep_dto.get("sleepStartTimestampLocal"),
            "end": sleep_dto.get("sleepEndTimestampLocal"),
            "score": safe_get(
                sleep_dto,
                "sleepScores",
                "overall",
                "value"
            ),
        },

        "hrv": {
            "weekly_average": safe_get(
                hrv,
                "hrvSummary",
                "weeklyAvg"
            ),
            "last_night_average": safe_get(
                hrv,
                "hrvSummary",
                "lastNightAvg"
            ),
            "last_night_5min_high": safe_get(
                hrv,
                "hrvSummary",
                "lastNight5MinHigh"
            ),
            "status": safe_get(
                hrv,
                "hrvSummary",
                "status"
            ),
        },
    }


def get_activities(client, start_date, end_date):
    try:
        activities = client.get_activities_by_date(
            start_date.isoformat(),
            end_date.isoformat()
        )
    except Exception as exc:
        print(f"Warning: activities unavailable: {exc}")
        return []

    cleaned = []

    for activity in activities:
        cleaned.append({
            "id": activity.get("activityId"),
            "name": activity.get("activityName"),
            "type": safe_get(
                activity,
                "activityType",
                "typeKey"
            ),
            "start_local": activity.get("startTimeLocal"),
            "duration_seconds": activity.get("duration"),
            "distance_metres": activity.get("distance"),
            "calories": activity.get("calories"),
            "average_hr": activity.get("averageHR"),
            "max_hr": activity.get("maxHR"),
        })

    return cleaned


def print_day(day):
    print()
    print(day["date"])
    print("-------------------------")
    print("Steps:", day["steps"])
    print("Resting HR:", day["heart_rate"]["resting_bpm"])
    print("Average stress:", day["stress"]["average"])
    print(
        "Body Battery:",
        day["body_battery"]["lowest"],
        "→",
        day["body_battery"]["highest"]
    )
    print("Sleep hours:", day["sleep"]["hours"])
    print("Sleep score:", day["sleep"]["score"])
    print("Sleep start:", day["sleep"]["start"])
    print("Sleep end:", day["sleep"]["end"])
    print(
        "Overnight HRV:",
        day["hrv"]["last_night_average"]
    )


# -------------------------
# Connect to Garmin
# -------------------------

client = Garmin()

# Uses the token we already saved on the Pixel.
client.login(TOKEN_DIR)

today = date.today()
yesterday = today - timedelta(days=1)

print("Connected to Garmin using saved token.")

# -------------------------
# Collect daily context
# -------------------------

days = [
    get_day(client, yesterday),
    get_day(client, today),
]

# -------------------------
# Collect activities
# -------------------------

activities = get_activities(
    client,
    yesterday,
    today
)

# -------------------------
# Final dataset
# -------------------------

report = {
    "generated_at": datetime.now().astimezone().isoformat(),
    "period": {
        "start_date": yesterday.isoformat(),
        "end_date": today.isoformat(),
    },

    "interpretation_notes": [
        "Garmin wearable data provides contextual information only.",
        "Activity, stress, sleep, heart-rate and HRV associations do not prove causation of glucose changes.",
        "Daily totals may be incomplete for the current day.",
        "Garmin sleep metrics are Garmin-derived estimates.",
    ],

    "daily": days,
    "activities": activities,
}

# -------------------------
# Human-readable output
# -------------------------

print()
print("GARMIN 48-HOUR CONTEXT")
print("======================")

for day_data in days:
    print_day(day_data)

print()
print("Activities")
print("-------------------------")

if activities:
    for activity in activities:
        print(
            activity["start_local"],
            "|",
            activity["type"],
            "|",
            activity["name"],
            "|",
            activity["duration_seconds"],
            "sec",
            "| avg HR",
            activity["average_hr"]
        )
else:
    print("No activities recorded.")

# -------------------------
# Save machine-readable JSON
# -------------------------

with open("garmin_summary.json", "w") as file:
    json.dump(
        report,
        file,
        indent=2,
        default=str
    )

print()
print("Saved: garmin_summary.json")
