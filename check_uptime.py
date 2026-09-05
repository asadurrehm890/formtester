import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from config.websites import WEBSITES

load_dotenv()

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
TIMEOUT = 15  # seconds

def send_discord(title: str, message: str, success: bool = True):
    if not DISCORD_WEBHOOK:
        print("No Discord webhook set")
        return

    color = 5763719 if success else 15548997  # Green / Red
    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"Discord error: {e}")

def check_website(url: str) -> tuple[bool, str, float]:
    """
    Returns: (is_up, message, response_time)
    """
    try:
        start = datetime.now()
        response = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        response_time = (datetime.now() - start).total_seconds()

        if response.status_code < 400:
            return True, f"UP ({response.status_code}) - {response_time:.2f}s", response_time
        else:
            return False, f"DOWN - Status Code: {response.status_code}", response_time

    except requests.exceptions.Timeout:
        return False, "DOWN - Timeout", 0
    except requests.exceptions.ConnectionError:
        return False, "DOWN - Connection Error", 0
    except Exception as e:
        return False, f"DOWN - Error: {str(e)}", 0

def run_uptime_check():
    print(f"\n=== Starting Uptime Check at {datetime.now()} ===\n")

    results = []
    down_sites = []

    for site in WEBSITES:
        name = site["name"]
        url = site["url"]

        print(f"Checking: {name} ...", end=" ")
        is_up, message, response_time = check_website(url)

        status_icon = "✅" if is_up else "❌"
        print(f"{status_icon} {message}")

        results.append({
            "name": name,
            "url": url,
            "is_up": is_up,
            "message": message
        })

        if not is_up:
            down_sites.append(f"❌ **{name}** → {message}\n{url}")

    # Build Report
    report = ""
    for r in results:
        icon = "✅" if r["is_up"] else "❌"
        report += f"{icon} **{r['name']}**: {r['message']}\n"

    print("\n" + "="*50)
    print(report)
    print("="*50)

    # Send Discord notification
    if down_sites:
        # Only alert if something is down
        down_message = "\n\n".join(down_sites)
        send_discord("🚨 Website(s) Down!", down_message, success=False)
    else:
        # Optional: Send success summary (you can comment this if you only want alerts on failure)
        send_discord("✅ All Websites are UP", report, success=True)

    return len(down_sites) == 0

if __name__ == "__main__":
    run_uptime_check()