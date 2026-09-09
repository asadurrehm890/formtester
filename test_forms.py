import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from config.websites import WEBSITES

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

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

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,900")
    options.add_argument("--disable-gpu")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

def test_main_contact_form(driver, site_name: str, url: str):
    print(f"  → Testing Main Contact Form on {site_name}...")
    try:
        driver.get(url)
        time.sleep(6)

        wait = WebDriverWait(driver, 20)

        # Fill fields using labels (Ninja Forms)
        def fill_by_label(label_text, value):
            try:
                el = wait.until(EC.presence_of_element_located(
                    (By.XPATH, f"//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label_text.lower()}')]/following::input[1]")
                ))
                el.clear()
                el.send_keys(value)
            except:
                # Fallback
                el = driver.find_element(By.XPATH, f"//*[contains(text(), '{label_text}')]/following::input[1]")
                el.clear()
                el.send_keys(value)

        fill_by_label("First Name", f"{TEST_PREFIX} John")
        fill_by_label("Surname", f"{TEST_PREFIX} Doe")
        fill_by_label("Email", "form-test@example.com")

        # Date of birth - target visible textbox
        try:
            dob = driver.find_element(By.CSS_SELECTOR, "input.form-control.input[type='text']")
            dob.clear()
            dob.send_keys("15/05/1990")
        except:
            fill_by_label("Date of birth", "15/05/1990")

        fill_by_label("Flat", "12A")
        fill_by_label("Street", "Test Road")
        fill_by_label("Post code", "BN1 1AA")
        fill_by_label("Phone", "07123456789")

        # Radio buttons
        try:
            driver.find_element(By.XPATH, "//*[contains(text(), 'Beginner with no driving experience')]").click()
        except:
            pass
        try:
            driver.find_element(By.XPATH, "//*[contains(text(), 'UK Provisional licence')]").click()
        except:
            pass

        fill_by_label("Theory test", "Yes - Jan 2025")
        fill_by_label("driving test", "Not booked yet")

        try:
            driver.find_element(By.XPATH, "//*[contains(text(), 'I am looking for an automatic lesson only')]").click()
        except:
            pass

        fill_by_label("How many lessons", "0 lessons")
        fill_by_label("Your Availability", "Weekdays after 5pm")
        fill_by_label("preference date", "Mon 10am, Wed 2pm")
        fill_by_label("Your Message", f"{TEST_PREFIX} Automated test - please ignore")

        time.sleep(1)

        # Submit
        try:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        except:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]").click()

        time.sleep(7)

        content = driver.page_source.lower()
        if any(word in content for word in ["thank you", "successfully", "received", "we will contact"]):
            return True, "Main Contact Form → PASSED"
        return False, "Main Contact Form → FAILED (no success message)"

    except Exception as e:
        return False, f"Main Contact Form Error: {str(e)}"

def test_callback_form(driver, site_name: str, url: str):
    print(f"  → Testing REQUEST A CALLBACK form on {site_name}...")
    try:
        driver.get(url)
        time.sleep(5)

        # Click floating button
        try:
            btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Request A Call Back') or contains(text(), 'Request A Callback')]"))
            )
            btn.click()
        except:
            driver.find_element(By.XPATH, "//*[contains(text(), 'Call Back') or contains(text(), 'Callback')]").click()

        time.sleep(3)

        # Wait for phone field
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))
        )

        # Fill fields
        text_inputs = driver.find_elements(By.CSS_SELECTOR, "form input[type='text']")
        if len(text_inputs) >= 3:
            text_inputs[0].clear()
            text_inputs[0].send_keys(f"{TEST_PREFIX} Sarah")
            text_inputs[1].clear()
            text_inputs[1].send_keys(f"{TEST_PREFIX} Khan")
            text_inputs[2].clear()
            text_inputs[2].send_keys("BN2 2BB")

        phone = driver.find_element(By.CSS_SELECTOR, "input[type='tel']")
        phone.clear()
        phone.send_keys("07987654321")

        # Terms checkbox
        try:
            checkboxes = driver.find_elements(By.CSS_SELECTOR, "form input[type='checkbox']")
            if checkboxes:
                checkboxes[-1].click()
        except:
            pass

        time.sleep(1)

        # Submit
        try:
            submit = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit') or @type='submit']"))
            )
            submit.click()
        except:
            driver.find_element(By.CSS_SELECTOR, "form button").click()

        time.sleep(6)

        content = driver.page_source.lower()
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

    driver = create_driver()

    try:
        for site in WEBSITES:
            site_name = site["name"]
            url = site["url"]
            print(f"\n🌐 Testing: {site_name}")

            success1, msg1 = test_main_contact_form(driver, site_name, url)
            success2, msg2 = test_callback_form(driver, site_name, url)

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

    finally:
        driver.quit()

    send_to_wordpress(wp_results)

    report = "\n".join(report_lines)
    print("\n" + report)

    if all_passed:
        send_discord("✅ All Forms Working", report, success=True)
    else:
        send_discord("❌ Some Forms Failed", report, success=False)

if __name__ == "__main__":
    run_all_tests()