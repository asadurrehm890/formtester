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
        page.wait_for_timeout(6000)

        page.wait_for_selector("input", timeout=15000)

        page.get_by_label("First Name", exact=False).fill(f"{TEST_PREFIX} John", timeout=10000)
        page.get_by_label("Surname", exact=False).fill(f"{TEST_PREFIX} Doe")
        page.get_by_label("Email", exact=False).fill("form-test@example.com")

        # Fixed Date of birth (targets only visible field)
        page.get_by_role("textbox", name="Date of birth *").fill("15/05/1990")

        page.get_by_label("Flat", exact=False).fill("12A")
        page.get_by_label("Street", exact=False).fill("Test Road")
        page.get_by_label("Post code", exact=False).fill("BN1 1AA")
        page.get_by_label("Phone", exact=False).fill("07123456789")

        page.get_by_text("Beginner with no driving experience", exact=False).click()
        page.get_by_text("UK Provisional licence", exact=False).click()

        page.get_by_label("Theory test", exact=False).fill("Yes - Jan 2025")
        page.get_by_label("driving test", exact=False).fill("Not booked yet")
        page.get_by_text("I am looking for an automatic lesson only", exact=False).click()
        page.get_by_label("How many lessons", exact=False).fill("0 lessons")
        page.get_by_label("Your Availability", exact=False).fill("Weekdays after 5pm")
        page.get_by_label("preference date", exact=False).fill("Mon 10am, Wed 2pm")
        page.get_by_label("Your Message", exact=False).fill(f"{TEST_PREFIX} Automated test - please ignore")

        page.wait_for_timeout(1000)
        page.locator("input[type='submit'], button:has-text('Submit')").first.click()
        page.wait_for_timeout(7000)

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
        page.wait_for_timeout(5000)

        # Click floating button
        try:
            page.get_by_text("Request A Call Back", exact=False).first.click(timeout=8000)
        except:
            try:
                page.get_by_text("Request A Callback", exact=False).first.click(timeout=5000)
            except:
                page.locator("text=/Call Back/i").last.click(timeout=5000)

        page.wait_for_timeout(3000)

        # Wait for phone field
        page.wait_for_selector("input[type='tel']", timeout=10000)

        # Fill fields
        text_inputs = page.locator("form input[type='text']")
        text_inputs.nth(0).fill(f"{TEST_PREFIX} Sarah")
        text_inputs.nth(1).fill(f"{TEST_PREFIX} Khan")
        page.locator("input[type='tel']").fill("07987654321")
        text_inputs.nth(2).fill("BN2 2BB")

        # Check terms checkbox
        page.locator("form input[type='checkbox']").last.check()

        page.wait_for_timeout(1500)

        # More reliable ways to click Submit
        try:
            page.get_by_role("button", name="Submit").last.click(timeout=8000)
        except:
            try:
                page.locator("button[type='submit']").last.click(timeout=5000)
            except:
                page.locator("form button").last.click(timeout=5000)

        page.wait_for_timeout(6000)

        content = page.content().lower()
        if any(word in content for word in ["thank you", "successfully", "received", "we will call", "callback", "success"]):
            return True, "Callback Form → PASSED"

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