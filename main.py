from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_KORISNIK")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENT = os.getenv("GMAIL_PRIMALAC")
MAX_PRICE_EUR = float(400)


def send_email(listings: list[dict]):
    subject = f"🎯 KP: Found {len(listings)} listing(s) below {MAX_PRICE_EUR:.0f}€"

    lines = []
    for listing in listings:
        lines.append(f"• {listing['title']}")
        lines.append(f"  Price: {listing['price_text']}")
        lines.append(f"  Link: {listing['link']}")
        lines.append("")

    body = f"""Hey!

I found {len(listings)} listing(s) for Tamron 28-75 f2.8 below {MAX_PRICE_EUR:.0f}€:

{"\n".join(lines)}
-- KP Tracker
"""

    message = MIMEMultipart()
    message["From"] = GMAIL_USER
    message["To"] = GMAIL_RECIPIENT
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, GMAIL_RECIPIENT, message.as_string())

    print(f"✅ Email sent to {GMAIL_RECIPIENT}")


class KupujemProdajemBot:
    RSD_TO_EUR = 117.0

    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 35)

    def parse_price(self, price_text: str) -> tuple[float, str] | None:
        text = price_text.strip()

        if "€" in text:
            number_str = text.replace("€", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(number_str), "EUR"
            except ValueError:
                return None

        if "din" in text.lower() or "rsd" in text.lower():
            number_str = text.lower().replace("din", "").replace("rsd", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(number_str) / self.RSD_TO_EUR, "RSD"
            except ValueError:
                return None

        return None

    def get_tamron(self):
        self.driver.get("https://www.kupujemprodajem.com/pretraga?keywords=tamron+28-75+f2.8")
        self.wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "article")))

        listings = self.driver.find_elements(By.CSS_SELECTOR, "article")
        affordable = []

        for listing in listings:
            try:
                title = listing.find_element(By.CSS_SELECTOR, "a[href*='/oglas/']").text.strip()
                price_el = listing.find_element(By.XPATH, ".//div[contains(@class,'price')]//div")
                price_text = price_el.text.strip()
                link = listing.find_element(By.CSS_SELECTOR, "a[href*='/oglas/']").get_attribute("href")

                parsed = self.parse_price(price_text)
                if parsed is None:
                    print(f"  ⚠️  Could not parse price: '{price_text}' — skipping")
                    continue

                price_in_eur, currency = parsed
                converted = f" ({price_in_eur:.0f}€)" if currency == "RSD" else ""
                print(f"{title} | {price_text}{converted} | {link}")

                if price_in_eur <= MAX_PRICE_EUR:
                    affordable.append({
                        "title": title,
                        "price_text": price_text,
                        "price_number": price_in_eur,
                        "link": link,
                    })

            except Exception as e:
                print(f"  ⚠️  Skipping listing: {e}")
                continue

        print(f"\nTotal listings: {len(listings)} | Below {MAX_PRICE_EUR:.0f}€: {len(affordable)}")

        if affordable:
            send_email(affordable)
        else:
            print("No listings below the limit — email not sent.")


bot = KupujemProdajemBot()
bot.get_tamron()
bot.driver.quit()
