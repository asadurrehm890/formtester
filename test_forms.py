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
from selenium.webdriver.common.action_chains import ActionChains
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
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

def safe_send_keys(driver, element, value):
    """Safely type into an element"""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)
        element.clear()
        element.send_keys(value)
    except:
        # JavaScript fallback
        driver.execute_script("arguments[0].value = arguments[1];", element, value)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)

def test_main_contact_form(driver, site_name: str, url: str):
    print(f"  → Testing Main Contact Form on {site_name}...")
    try:
        driver.get(url)
        time.sleep(6)

        wait = WebDriverWait(driver, 20)

        def fill_visible_input(label_part, value):
            # Find visible text inputs near the label
            xpath = f"//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label_part.lower()}')]/following::input[@type='text' or @type='email' or @type='tel'][1]"
            try:
                el = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
                safe_send_keys(driver, el, value)
                return True
            except:
                # Alternative: find by aria-labelledby or nearby text
                try:
                    el = driver.find_element(By.XPATH, f"//*[contains(text(), '{label_part}')]/following::input[not(@type='hidden')][1]")
                    safe_send_keys(driver, el, value)
                    return True
                except:
                    return False

        fill_visible_input("First Name", f"{TEST_PREFIX} John")
        fill_visible_input("Surname", f"{TEST_PREFIX} Doe")
        fill_visible_input("Email", "form-test@example.com")

        # Date of birth - specifically target visible textbox
        try:
            dob = driver.find_element(By.CSS_SELECTOR, "input.form-control.input[type='text']")
            safe_send_keys(driver, dob, "15/05/1990")
        except:
            fill_visible_input("Date of birth", "15/05/1990")

        fill_visible_input("Flat", "12A")
        fill_visible_input("Street", "Test Road")
        fill_visible_input("Post code", "BN1 1AA")
        fill_visible_input("Phone", "07123456789")

        # Radio buttons
        for text in ["Beginner with no driving experience", "UK Provisional licence"]:
            try:
                el = driver.find_element(By.XPATH, f"//*[contains(text(), '{text}')]")
                driver.execute_script("arguments[0].click();", el)
            except:
                pass

        fill_visible_input("Theory test", "Yes - Jan 2025")
        fill_visible_input("driving test", "Not booked yet")

        try:
            el = driver.find_element(By.XPATH, "//*[contains(text(), 'I am looking for an automatic lesson only')]")
            driver.execute_script("arguments[0].click();", el)
        except:
            pass

        fill_visible_input("How many lessons", "0 lessons")
        fill_visible_input("Your Availability", "Weekdays after 5pm")
        fill_visible_input("preference date", "Mon 10am, Wed 2pm")
        fill_visible_input("Your Message", f"{TEST_PREFIX} Automated test - please ignore")

        time.sleep(1)

        # Submit
        try:
            submit = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            driver.execute_script("arguments[0].click();", submit)
        except:
            submit = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit') or contains(@class, 'submit')]")
            driver.execute_script("arguments[0].click();", submit)

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
            btn = WebDriverWait(driver, 12).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Request A Call Back') or contains(text(), 'Request A Callback') or contains(text(), 'Call Back')]"))
            )
            driver.execute_script("arguments[0].click();", btn)
        except Exception as e:
            return False, f"Callback Form Error: Could not click button - {str(e)}"

        time.sleep(3)

        # Wait for phone field (unique to this form)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))
        )

        # Fill text fields
        text_inputs = driver.find_elements(By.CSS_SELECTOR, "form input[type='text']")
        if len(text_inputs) >= 3:
            safe_send_keys(driver, text_inputs[0], f"{TEST_PREFIX} Sarah")
            safe_send_keys(driver, text_inputs[1], f"{TEST_PREFIX} Khan")
            safe_send_keys(driver, text_inputs[2], "BN2 2BB")
        else:
            return False, "Callback Form Error: Could not find text inputs"

        # Phone
        phone = driver.find_element(By.CSS_SELECTOR, "input[type='tel']")
        safe_send_keys(driver, phone, "07987654321")

        # Terms checkbox
        try:
            checkboxes = driver.find_elements(By.CSS_SELECTOR, "form input[type='checkbox']")
            if checkboxes:
                driver.execute_script("arguments[0].click();", checkboxes[-1])
        except:
            pass

        time.sleep(1)

        # Submit button - multiple strategies
        submitted = False
        selectors = [
            (By.XPATH, "//button[contains(text(), 'Submit')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "form button"),
            (By.XPATH, "//button[contains(@class, 'muiButton') or contains(@class, 'submit')]"),
        ]

        for by, selector in selectors:
            try:
                btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))
                driver.execute_script("arguments[0].click();", btn)
                submitted = True
                break
            except:
                continue

        if not submitted:
            return False, "Callback Form Error: Could not find/click Submit button"

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