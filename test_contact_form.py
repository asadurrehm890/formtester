import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, expect
from dotenv import load_dotenv

load_dotenv()

FORM_URL = "https://akautomaticdrivingschool.com/contact-us/"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
TEST_PREFIX = "[AUTO-TEST]"

def send_discord(title: str, message: str, success: bool = True):
    if not DISCORD_WEBHOOK:
        print("No Discord webhook set")
        return

    color = 5763719 if success else 15548997  # green / red
    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"Discord error: {e}")

def test_main_contact_form(page):
    """Test the big contact form on the page"""
    print("→ Testing Main Contact Form...")
    
    try:
        page.goto(FORM_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Fill main form
        page.get_by_label("First Name", exact=False).fill(f"{TEST_PREFIX} John")
        page.get_by_label("Surname", exact=False).fill(f"{TEST_PREFIX} Doe")
        page.get_by_label("Email", exact=False).fill("form-test@example.com")
        page.get_by_label("Date of birth", exact=False).fill("1990-05-15")
        page.get_by_label("Flat", exact=False).fill("12A")
        page.get_by_label("Street", exact=False).fill("Test Road")
        page.get_by_label("Post code", exact=False).fill("BN1 1AA")
        page.get_by_label("Phone", exact=False).fill("07123456789")

        # Submit
        submit = page.get_by_role("button", name="Submit").or_(
            page.locator("input[type='submit']")
        ).or_(page.locator("button[type='submit']"))
        submit.first.click()
        page.wait_for_timeout(5000)

        content = page.content().lower()
        if any(word in content for word in ["thank you", "successfully", "received", "we will contact"]):
            return True, "Main Contact Form submitted successfully"
        else:
            return False, "Main Contact Form: No success message found"

    except Exception as e:
        return False, f"Main Contact Form Error: {str(e)}"

def test_callback_form(page):
    """Test the floating REQUEST A CALLBACK form"""
    print("→ Testing REQUEST A CALLBACK form...")

    try:
        page.goto(FORM_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Click the floating "Request A Call Back" button
        # We try multiple possible selectors
        callback_button = page.get_by_text("Request A Call Back", exact=False).or_(
            page.get_by_text("Request A Callback", exact=False)
        ).or_(
            page.locator("text=Request A Call Back")
        ).or_(
            page.locator("[aria-label*='Call Back'], [title*='Call Back']")
        )

        callback_button.first.click(timeout=10000)
        page.wait_for_timeout(2000)  # Wait for popup to open

        # Now fill the popup form
        # These selectors are common for Buttonizer / popup forms
        page.get_by_label("First Name", exact=False).or_(
            page.locator("input[name*='first'], input[placeholder*='First']")
        ).first.fill(f"{TEST_PREFIX} Sarah")

        page.get_by_label("Last Name", exact=False).or_(
            page.get_by_label("Surname", exact=False)
        ).or_(
            page.locator("input[name*='last'], input[placeholder*='Last']")
        ).first.fill(f"{TEST_PREFIX} Khan")

        page.get_by_label("Phone", exact=False).or_(
            page.locator("input[type='tel'], input[name*='phone'], input[placeholder*='Phone']")
        ).first.fill("07987654321")

        page.get_by_label("Postcode", exact=False).or_(
            page.get_by_label("Post code", exact=False)
        ).or_(
            page.locator("input[name*='post'], input[placeholder*='Post']")
        ).first.fill("BN2 2BB")

        page.wait_for_timeout(1000)

        # Submit the popup form
        submit_btn = page.get_by_role("button", name="Submit").or_(
            page.get_by_role("button", name="Send")
        ).or_(
            page.locator("button[type='submit'], input[type='submit']")
        )
        submit_btn.first.click()
        page.wait_for_timeout(4000)

        content = page.content().lower()
        if any(word in content for word in ["thank you", "successfully", "received", "we will call", "callback"]):
            return True, "Callback Form submitted successfully"
        else:
            return False, "Callback Form: No clear success message found"

    except Exception as e:
        return False, f"Callback Form Error: {str(e)}"

def run_all_tests():
    print(f"\n=== Starting Form Tests at {datetime.now()} ===\n")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Test 1: Main Contact Form
        success1, msg1 = test_main_contact_form(page)
        results.append(("Main Contact Form", success1, msg1))
        page.screenshot(path="main-form-result.png", full_page=True)

        # Test 2: Callback Form
        success2, msg2 = test_callback_form(page)
        results.append(("REQUEST A CALLBACK Form", success2, msg2))
        page.screenshot(path="callback-form-result.png", full_page=True)

        browser.close()

    # Final Report
    all_passed = all(r[1] for r in results)

    report = ""
    for name, success, msg in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        report += f"**{name}**: {status}\n{msg}\n\n"

    print(report)

    if all_passed:
        send_discord("✅ All Forms Working", report, success=True)
    else:
        send_discord("❌ Some Forms Failed", report, success=False)

    return all_passed

if __name__ == "__main__":
    run_all_tests()