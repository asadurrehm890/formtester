import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from config.websites import WEBSITES

load_dotenv()

# ================== CONFIG ==================
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
WP_API_URL = os.getenv("WP_API_URL")
WP_SECRET_KEY = os.getenv("WP_SECRET_KEY")
TIMEOUT = 15
# ============================================

def send_discord(title: str, message: str, success: bool = True):
    if not DISCORD_WEBHOOK:
        return
    color = 5763719 if success else 15548997
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

def send_to_wordpress(results: list):
    if not WP_API_URL or not WP_SECRET_KEY:
        print("⚠️  WP_API_URL or WP_SECRET_KEY not set. Skipping WordPress update.")
        return

    payload = {
        "type": "uptime",
        "results": results
    }

    headers = {
        "Content-Type": "application/json",
        "X-WM-Secret": WP_SECRET_KEY
    }

    try:
        response = requests.post(WP_API_URL, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            print("✅ Uptime results sent to WordPress")
        else:
            print(f"❌ WordPress API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Failed to send to WordPress: {e}")

def check_website(url: str):
    try:
        start = datetime.now()
        response = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        response_time = (datetime.now() - start).total_seconds()

        if response.status_code < 400:
            return True, f"UP ({response.status_code}) - {response_time:.2f}s"
        else:
            return False, f"DOWN - Status Code: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "DOWN - Timeout"
    except requests.exceptions.ConnectionError:
        return False, "DOWN - Connection Error"
    except Exception as e:
        return False, f"DOWN - {str(e)}"

def run_uptime_check():
    print(f"\n=== Starting Uptime Check at {datetime.now()} ===\n")

    wp_results = []
    down_sites = []
    report_lines = []

    for site in WEBSITES:
        name = site["name"]
        url = site["url"]

        print(f"Checking: {name} ...", end=" ")
        is_up, message = check_website(url)
        print("✅" if is_up else "❌", message)

        status = "up" if is_up else "down"
        wp_results.append({
            "site_name": name,
            "status": status,
            "message": message
        })

        icon = "✅" if is_up else "❌"
        report_lines.append(f"{icon} **{name}**: {message}")

        if not is_up:
            down_sites.append(f"❌ **{name}** → {message}\n{url}")

    # Send to WordPress
    send_to_wordpress(wp_results)

    report = "\n".join(report_lines)
    print("\n" + report)

    if down_sites:
        send_discord("🚨 Website(s) Down!", "\n\n".join(down_sites), success=False)
    else:
        send_discord("✅ All Websites are UP", report, success=True)

if __name__ == "__main__":
    run_uptime_check()