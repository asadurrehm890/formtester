import os
import requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from config.websites import WEBSITES

load_dotenv()

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
WP_API_URL = os.getenv("WP_API_URL")
WP_SECRET_KEY = os.getenv("WP_SECRET_KEY")
TEST_PREFIX = "[AUTO-TEST]"

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

    payload = {"type": "form", "results": results}
    headers = {
        "Content-Type": "application/json",
        "X-WM-Secret": WP_SECRET_KEY
    }

    try:
        response = requests.post(WP_API_URL, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            print("✅ Results successfully sent to WordPress")
        else:
            print(f"❌ WordPress API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Failed to send to WordPress: {e}")

def test_main_contact_form(page, site_name: str, url: str):
    print(f"  → Testing Main Contact Form on {site_name}...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # More flexible field filling
        page.locator("input").filter(has=page.get_by_text("First Name", exact=False)).first.fill(f"{TEST_PREFIX} John")
        page.get_by_label("First Name", exact=False).fill(f"{TEST_PREFIX} John")
        page.get_by_label("Surname", exact=False).fill(f"{TEST_PREFIX} Doe")
        page.get_by_label("Email", exact=False).fill("form-test@example.com")
        page.get_by_label("Date of birth", exact=False).fill("15/05/1990")
        page.get_by_label("Flat", exact=False).fill("12A")
        page.get_by_label("Street", exact=False).fill("Test Road")
        page.get_by_label("Post code", exact=False).fill("BN1 1AA")
        page.get_by_label("Phone", exact=False).fill("07123456789")

        # Radio buttons
        page.get_by_text("Beginner with no driving experience", exact=False).click()
        page.get_by_text("UK Provisional licence", exact=False).click()

        # Other required fields
        page.get_by_label("Theory test", exact=False).fill("Yes - Jan 2025")
        page.get_by_label("driving test", exact=False).fill("Not booked yet")
        page.get_by_text("I am looking for an automatic lesson only", exact=False).click()
        page.get_by_label("How many lessons", exact=False).fill("0 lessons")
        page.get_by_label("Your Availability", exact=False).fill("Weekdays after 5pm")
        page.get_by_label("preference date", exact=False).fill("Mon 10am, Wed 2pm, Fri 4pm")
        page.get_by_label("Your Message", exact=False).fill(f"{TEST_PREFIX} Automated daily test - please ignore.")

        page.wait_for_timeout(1000)

        # Submit
        page.locator("input[type='submit'], button[type='submit']").first.click()
        page.wait_for_timeout(6000)

        content = page.content().lower()
        if any(word in content for word in ["thank you", "successfully", "received", "we will contact"]):
            return True, "Main Contact Form → PASSED"
        return False, "Main Contact Form → FAILED (no success message)"

    except Exception as e:
        return False, f"Main Contact Form Error: {str(e)}"

def test_callback_form(page, site_name: str, url: str):
    print(f"  → Testing REQUEST A CALLBACK form on {site_name}...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        # Try multiple possible texts for the floating button
        button_selectors = [
            "Request A Call Back",
            "Request A Callback",
            "Request a Call Back",
            "Call Back",
            "Callback"
        ]

        clicked = False
        for text in button_selectors:
            try:
                btn = page.get_by_text(text, exact=False).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            # Fallback: try clicking the red phone icon button
            page.locator("button, div, a").filter(has_text="Call Back").first.click(timeout=5000)

        page.wait_for_timeout(2500)

        # Fill popup form
        popup = page.locator("form").filter(has_text="Phone number").first

        popup.locator("input[type='text']").nth(0).fill(f"{TEST_PREFIX} Sarah")
        popup.locator("input[type='text']").nth(1).fill(f"{TEST_PREFIX} Khan")
        popup.locator("input[type='tel']").fill("07987654321")
        popup.locator("input[type='text']").nth(2).fill("BN2 2BB")

        # Check terms checkbox
        popup.locator("input[type='checkbox']").check()

        page.wait_for_timeout(800)
        popup.locator("button[type='submit']").click()
        page.wait_for_timeout(5000)

        content = page.content().lower()
        if any(word in content for word in ["thank you", "successfully", "received", "we will call", "callback", "success"]):
            return True, "Callback Form → PASSED"

        if page.locator("form").filter(has_text="Phone number").count() == 0:
            return True, "Callback Form → PASSED (form closed)"

        return False, "Callback Form → FAILED (no success message)"

    except Exception as e:
        return False, f"Callback Form Error: {str(e)}"

def run_all_tests():
    print(f"\n=== Starting Multi-Website Form Tests at {datetime.now()} ===\n")

    wp_results = []
    all_passed = True
    report_lines = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for site in WEBSITES:
            site_name = site["name"]
            url = site["url"]
            print(f"\n🌐 Testing: {site_name}")

            success1, msg1 = test_main_contact_form(page, site_name, url)
            success2, msg2 = test_callback_form(page, site_name, url)

            final_success = success1 and success2
            final_message = f"{msg1} | {msg2}"

            if not final_success:
                all_passed = False

            status = "passed" if final_success else "failed"
            wp_results.append({
                "site_name": site_name,
                "status": status,
                "message": final_message
            })

            icon = "✅" if final_success else "❌"
            report_lines.append(f"{icon} **{site_name}**: {final_message}")

        browser.close()

    send_to_wordpress(wp_results)

    report = "\n".join(report_lines)
    print("\n" + report)

    if all_passed:
        send_discord("✅ All Forms Working", report, success=True)
    else:
        send_discord("❌ Some Forms Failed", report, success=False)

if __name__ == "__main__":
    run_all_tests()