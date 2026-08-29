import json
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from garminconnect import Garmin

TOKEN_DIR = "~/.garminconnect"
UK_TZ = ZoneInfo("Europe/London")


def safe_get(data, *keys, default=None):
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


def timestamp_to_uk(timestamp):
    """Convert Garmin millisecond Unix timestamp to UK local time."""
    if not timestamp:
        return None

    try:
        return datetime.fromtimestamp(
            timestamp / 1000,
            tz=UK_TZ
        ).isoformat()
    except (TypeError, ValueError, OSError):
        return timestamp


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
            "start": timestamp_to_uk(
                sleep_dto.get("sleepStartTimestampLocal")
            ),
            "end": timestamp_to_uk(
                sleep_dto.get("sleepEndTimestampLocal")
            ),
            "score": safe_get(
                sleep_dto,
                "sleepScores",
                "overall",
                "value"
            ),
        },

        "hrv": {
            "weekly_average": safe_get(
                hrv, "hrvSummary", "weeklyAvg"
            ),
            "last_night_average": safe_get(
                hrv, "hrvSummary", "lastNightAvg"
            ),
            "last_night_5min_high": safe_get(
                hrv, "hrvSummary", "lastNight5MinHigh"
            ),
            "status": safe_get(
                hrv, "hrvSummary", "status"
            ),
        },
    }


def get_intraday(client, day):
    day_string = day.isoformat()

    result = {
        "date": day_string,
        "heart_rate": None,
        "stress_body_battery": None,
    }

    try:
        result["heart_rate"] = client.get_heart_rates(day_string)
    except Exception as exc:
        print(
            f"Warning: heart-rate timeline unavailable "
            f"for {day_string}: {exc}"
        )

    try:
        result["stress_body_battery"] = (
            client.get_stress_data(day_string)
        )
    except Exception as exc:
        print(
            f"Warning: stress/Body Battery timeline unavailable "
            f"for {day_string}: {exc}"
        )

    return result


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
    print("Overnight HRV:", day["hrv"]["last_night_average"])


# Connect using saved authentication
client = Garmin()
client.login(TOKEN_DIR)

print("Connected to Garmin using saved token.")

today = date.today()
yesterday = today - timedelta(days=1)

days = [
    get_day(client, yesterday),
    get_day(client, today),
]

print("Fetching intraday Garmin timelines...")

intraday = [
    get_intraday(client, yesterday),
    get_intraday(client, today),
]

activities = get_activities(
    client,
    yesterday,
    today
)

report = {
    "generated_at": datetime.now(UK_TZ).isoformat(),

    "period": {
        "start_date": yesterday.isoformat(),
        "end_date": today.isoformat(),
    },

    "interpretation_notes": [
        "Garmin wearable data provides contextual information only.",
        "Associations between Garmin metrics and glucose changes do not prove causation.",
        "Current-day Garmin totals may be incomplete.",
        "Sleep, stress, Body Battery and HRV are Garmin-derived estimates.",
    ],

    "daily": days,
    "activities": activities,
    "intraday": intraday,
}


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


print()
print("Intraday data")
print("-------------------------")

for day_data in intraday:
    hr_ok = day_data["heart_rate"] is not None
    stress_ok = day_data["stress_body_battery"] is not None

    print(
        day_data["date"],
        "| HR:",
        "OK" if hr_ok else "Unavailable",
        "| Stress/Body Battery:",
        "OK" if stress_ok else "Unavailable"
    )


with open("garmin_summary.json", "w") as file:
    json.dump(
        report,
        file,
        indent=2,
        default=str
    )

print()
print("Saved: garmin_summary.json")
