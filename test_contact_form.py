import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, expect
from dotenv import load_dotenv

load_dotenv()

FORM_URL = "https://akautomaticdrivingschool.com/contact/"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
TEST_PREFIX = "[AUTO-TEST]"

def send_discord(message: str, success: bool = True):
    if not DISCORD_WEBHOOK:
        print("No Discord webhook set")
        return

    color = 5763719 if success else 15548997  # green / red
    payload = {
        "embeds": [{
            "title": "✅ Contact Form Test Passed" if success else "❌ Contact Form Test FAILED",
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"Discord error: {e}")

def run_test():
    print(f"Starting form test at {datetime.now()}")
    success = False
    error_message = ""
    screenshot_path = "form-test-result.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            # 1. Go to form
            page.goto(FORM_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)  # Extra wait for Ninja Forms / JS

            # 2. Fill fields (using labels - most reliable)
            # You may need to adjust these after first run by inspecting the page

            page.get_by_label("First Name", exact=False).fill(f"{TEST_PREFIX} John")
            page.get_by_label("Surname", exact=False).fill(f"{TEST_PREFIX} Doe")
            page.get_by_label("Email", exact=False).fill("form-test@example.com")
            page.get_by_label("Date of birth", exact=False).fill("1990-05-15")

            # Address section
            page.get_by_label("Flat", exact=False).fill("12A")
            page.get_by_label("Street", exact=False).fill("Test Road")
            page.get_by_label("Post code", exact=False).fill("BN1 1AA")
            page.get_by_label("Phone", exact=False).fill("07123456789")

            # If there are more fields (message, etc.), add them here
            # Example:
            # page.get_by_label("Message", exact=False).fill(f"{TEST_PREFIX} Automated daily test - please ignore")

            page.wait_for_timeout(1000)

            # 3. Submit
            # Try common submit button texts
            submit_button = page.get_by_role("button", name="Submit").or_(
                page.get_by_role("button", name="Send")
            ).or_(
                page.locator("input[type='submit']")
            ).or_(
                page.locator("button[type='submit']")
            )
            submit_button.first.click()

            # 4. Wait and check for success
            page.wait_for_timeout(5000)

            # Success indicators (adjust after first real run)
            success_indicators = [
                "Thank you",
                "successfully",
                "We will contact you",
                "message has been sent",
                "received your"
            ]

            page_content = page.content().lower()
            if any(indicator.lower() in page_content for indicator in success_indicators):
                success = True
                error_message = "Form submitted successfully. Success message detected."
            else:
                # Check if still on form page with validation errors
                error_message = "No clear success message found after submission."

            # Take screenshot always
            page.screenshot(path=screenshot_path, full_page=True)

        except Exception as e:
            error_message = str(e)
            try:
                page.screenshot(path=screenshot_path, full_page=True)
            except:
                pass
        finally:
            browser.close()

    # Report
    if success:
        print("✅ TEST PASSED")
        send_discord(f"**Result:** Success\n**Time:** {datetime.now()}\n{error_message}", success=True)
    else:
        print("❌ TEST FAILED")
        print(error_message)
        send_discord(
            f"**Result:** FAILED\n**Time:** {datetime.now()}\n**Error:** {error_message}\n\nCheck the screenshot in GitHub Actions artifacts.",
            success=False
        )

    return success

if __name__ == "__main__":
    run_test()