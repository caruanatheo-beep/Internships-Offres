"""Keep scheduled collections inside the combined Paris / New York day."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os


def collection_window_open(now: datetime) -> bool:
    paris = now.astimezone(ZoneInfo("Europe/Paris"))
    new_york = now.astimezone(ZoneInfo("America/New_York"))
    return paris.hour >= 8 or (new_york.date() < paris.date() and new_york.hour <= 22)


if __name__ == "__main__":
    active = os.environ.get("GITHUB_EVENT_NAME") != "schedule" or collection_window_open(datetime.now(timezone.utc))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"active={str(active).lower()}\n")
    print("Collection window: open" if active else "Collection window: closed")
