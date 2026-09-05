import os
import requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from config.websites import WEBSITES

load_dotenv()

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
TEST_PREFIX = "[AUTO-TEST]"

def send_discord(title: str, message: str, success: bool = True):
    if not DISCORD_WEBHOOK:
        print("No Discord webhook set")
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

def test_main_contact_form(page, site_name: str, url: str):
    """Test the full Contact Form"""
    print(f"  → Testing Main Contact Form on {site_name}...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        # Text Fields
        page.get_by_role("textbox", name="First Name *").fill(f"{TEST_PREFIX} John")
        page.get_by_role("textbox", name="Surname *").fill(f"{TEST_PREFIX} Doe")
        page.get_by_role("textbox", name="Email *").fill("form-test@example.com")
        page.get_by_role("textbox", name="Date of birth *").fill("15/05/1990")
        page.get_by_role("textbox", name="Flat - House *").fill("12A")
        page.get_by_role("textbox", name="Street - Road *").fill("Test Road")
        page.get_by_role("textbox", name="Post code *").fill("BN1 1AA")
        page.get_by_role("textbox", name="Phone *").fill("07123456789")

        # Radio Buttons
        page.get_by_label("Beginner with no driving experience").check()
        page.get_by_label("UK Provisional licence").check()

        # Other fields
        page.get_by_role("textbox", name="Theory test has passed ? If yes, when did you passed ? *").fill("Yes - Jan 2025")
        page.get_by_role("textbox", name="If you have booked the driving test, Please mention the date & test centre. *").fill("Not booked yet")
        page.get_by_label("I am looking for an automatic lesson only. *").check()
        page.get_by_role("textbox", name="How many lessons you have already received in the Uk and have you got any other country’s driving experience? *").fill("0 lessons")
        page.get_by_role("textbox", name="Your Availability? *").fill("Weekdays after 5pm")
        page.get_by_role("textbox", name="Your preference date & time for a trial Lesson: Please give us three time slots within next two weeks *").fill("Mon 10am, Wed 2pm, Fri 4pm")
        page.get_by_role("textbox", name="Your Message *").fill(f"{TEST_PREFIX} Automated daily test - please ignore.")

        page.wait_for_timeout(1000)

        # Submit
        page.get_by_role("button", name="Submit").or_(
            page.locator("input[type='submit']")
        ).first.click()

        page.wait_for_timeout(6000)

        content = page.content().lower()
        success_words = ["thank you", "successfully", "received", "we will contact", "message has been sent"]

        if any(word in content for word in success_words):
            return True, "Main Contact Form → PASSED"
        else:
            return False, "Main Contact Form → FAILED (no success message)"

    except Exception as e:
        return False, f"Main Contact Form → ERROR: {str(e)}"

def test_callback_form(page, site_name: str, url: str):
    """Test the floating REQUEST A CALLBACK form"""
    print(f"  → Testing REQUEST A CALLBACK form on {site_name}...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        # Click floating button
        page.get_by_text("Request A Call Back", exact=False).first.click(timeout=10000)
        page.wait_for_timeout(2500)

        # Fill popup form
        page.get_by_role("textbox", name="First Name").or_(
            page.locator("input[placeholder*='First']")
        ).first.fill(f"{TEST_PREFIX} Sarah")

        page.get_by_role("textbox", name="Last Name").or_(
            page.get_by_role("textbox", name="Surname")
        ).or_(
            page.locator("input[placeholder*='Last']")
        ).first.fill(f"{TEST_PREFIX} Khan")

        page.get_by_role("textbox", name="Phone").or_(
            page.locator("input[type='tel']")
        ).first.fill("07987654321")

        page.get_by_role("textbox", name="Postcode").or_(
            page.get_by_role("textbox", name="Post code")
        ).first.fill("BN2 2BB")

        page.wait_for_timeout(800)

        page.get_by_role("button", name="Submit").or_(
            page.locator("button[type='submit']")
        ).first.click()

        page.wait_for_timeout(5000)

        content = page.content().lower()
        if any(word in content for word in ["thank you", "successfully", "received", "we will call", "callback"]):
            return True, "Callback Form → PASSED"
        else:
            return False, "Callback Form → FAILED (no success message)"

    except Exception as e:
        return False, f"Callback Form → ERROR: {str(e)}"

def run_all_tests():
    print(f"\n=== Starting Multi-Website Form Tests at {datetime.now()} ===\n")

    all_results = []
    overall_success = True

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

            print(f"\n🌐 Testing Website: {site_name}")
            print("-" * 50)

            # Test Main Form
            success1, msg1 = test_main_contact_form(page, site_name, url)
            all_results.append((site_name, "Main Contact Form", success1, msg1))
            if not success1:
                overall_success = False

            # Test Callback Form
            success2, msg2 = test_callback_form(page, site_name, url)
            all_results.append((site_name, "Callback Form", success2, msg2))
            if not success2:
                overall_success = False

            # Optional: Save screenshots per website
            # page.screenshot(path=f"screenshots/{site_name.replace(' ', '_')}.png", full_page=True)

        browser.close()

    # Build Report
    report = ""
    for site_name, form_name, success, msg in all_results:
        status = "✅" if success else "❌"
        report += f"{status} **{site_name}** → {form_name}: {msg}\n"

    print("\n" + "="*60)
    print(report)
    print("="*60)

    # Send to Discord
    if overall_success:
        send_discord("✅ All Forms Working on All Websites", report, success=True)
    else:
        send_discord("❌ Some Forms Failed", report, success=False)

    return overall_success

if __name__ == "__main__":
    run_all_tests()