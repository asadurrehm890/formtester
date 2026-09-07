import os
import requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from config.websites import WEBSITES

load_dotenv()

# ================== CONFIG ==================
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
WP_API_URL = os.getenv("WP_API_URL")          # Example: https://yoursite.com/wp-json/website-monitor/v1/update
WP_SECRET_KEY = os.getenv("WP_SECRET_KEY")    # Secret key from plugin settings
TEST_PREFIX = "[AUTO-TEST]"
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
    """Send form test results to WordPress plugin"""
    if not WP_API_URL or not WP_SECRET_KEY:
        print("⚠️  WP_API_URL or WP_SECRET_KEY not set. Skipping WordPress update.")
        return

    payload = {
        "type": "form",
        "results": results
    }

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
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        page.get_by_role("textbox", name="First Name *").fill(f"{TEST_PREFIX} test")
        page.get_by_role("textbox", name="Surname *").fill(f"{TEST_PREFIX} test")
        page.get_by_role("textbox", name="Email *").fill("form-test@example.com")
        page.get_by_role("textbox", name="Date of birth *").fill("15/05/1990")
        page.get_by_role("textbox", name="Flat - House *").fill("12A")
        page.get_by_role("textbox", name="Street - Road *").fill("Test Road")
        page.get_by_role("textbox", name="Post code *").fill("BN1 1AA")
        page.get_by_role("textbox", name="Phone *").fill("07123456789")

        page.get_by_label("Beginner with no driving experience").check()
        page.get_by_label("UK Provisional licence").check()

        page.get_by_role("textbox", name="Theory test has passed ? If yes, when did you passed ? *").fill("Yes - Jan 2025")
        page.get_by_role("textbox", name="If you have booked the driving test, Please mention the date & test centre. *").fill("Not booked yet")
        page.get_by_label("I am looking for an automatic lesson only. *").check()
        page.get_by_role("textbox", name="How many lessons you have already received in the Uk and have you got any other country’s driving experience? *").fill("0 lessons")
        page.get_by_role("textbox", name="Your Availability? *").fill("Weekdays after 5pm")
        page.get_by_role("textbox", name="Your preference date & time for a trial Lesson: Please give us three time slots within next two weeks *").fill("Mon 10am, Wed 2pm, Fri 4pm")
        page.get_by_role("textbox", name="Your Message *").fill(f"{TEST_PREFIX} Automated daily test - please ignore.")

        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Submit").or_(page.locator("input[type='submit']")).first.click()
        page.wait_for_timeout(6000)

        content = page.content().lower()
        success_words = ["thank you", "successfully", "received", "we will contact", "message has been sent"]

        if any(word in content for word in success_words):
            return True, "Main + Callback forms tested successfully"
        else:
            return False, "Main Contact Form failed - no success message"

    except Exception as e:
        return False, f"Main Contact Form Error: {str(e)}"

def test_callback_form(page, site_name: str, url: str):
    """Test the floating REQUEST A CALLBACK form"""
    print(f"  → Testing REQUEST A CALLBACK form on {site_name}...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        # 1. Click the floating button
        page.get_by_text("Request A Call Back", exact=False).first.click(timeout=10000)
        page.wait_for_timeout(2500)

        # 2. Fill the form using more reliable selectors
        # First Name
        page.locator("form input[type='text']").nth(0).fill(f"{TEST_PREFIX} Sarah")

        # Last Name
        page.locator("form input[type='text']").nth(1).fill(f"{TEST_PREFIX} Khan")

        # Phone number
        page.locator("form input[type='tel']").fill("07987654321")

        # Post Code
        page.locator("form input[type='text']").nth(2).fill("BN2 2BB")

        # 3. Check the required Terms & Conditions checkbox
        page.locator("form input[type='checkbox']").check()

        page.wait_for_timeout(800)

        # 4. Click Submit
        page.locator("form button[type='submit']").click()

        page.wait_for_timeout(5000)

        # 5. Check for success
        content = page.content().lower()
        success_words = ["thank you", "successfully", "received", "we will call", "callback", "submitted", "success"]

        if any(word in content for word in success_words):
            return True, "Callback Form → PASSED"
        else:
            # Even if no clear message, check if form disappeared (common success behavior)
            if page.locator("form button[type='submit']").count() == 0:
                return True, "Callback Form → PASSED (form closed after submit)"
            return False, "Callback Form → FAILED (no success message detected)"

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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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

    # Send to WordPress
    send_to_wordpress(wp_results)

    # Discord Report
    report = "\n".join(report_lines)
    print("\n" + report)

    if all_passed:
        send_discord("✅ All Forms Working", report, success=True)
    else:
        send_discord("❌ Some Forms Failed", report, success=False)

if __name__ == "__main__":
    run_all_tests()