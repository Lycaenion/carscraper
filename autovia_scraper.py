import logging
import time
import sys
import pickle
from dataclasses import dataclass
from typing import Optional
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

AUTOVIA_URL = "https://www.autovia.sk/osobne-auta/?p%5Border%5D=1"
AUTOVIA_COOKIES_FILE = 'cookies/autovia.pkl'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_out = logging.StreamHandler(sys.stdout)
filehandler = logging.FileHandler('autovia_scraper.log', encoding='utf-8')
logger.addHandler(console_out)
logger.addHandler(filehandler)


@dataclass
class CarData:
    url: str
    brand: str
    model_ver: Optional[str]
    price: int
    year: str
    location: Optional[str]
    fuel: Optional[str]
    engine_power: str
    gearbox: str
    mileage: str

class AutoviaScraper:
    def __init__(self, url: str, cookies_file: str):
        self.url = url
        self.cookies_file = cookies_file
        self.driver = None
        self.base_window = None

    def setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("window-size=1920,1080")
        self.driver = webdriver.Chrome(options = options)
        self.driver.get(self.url)
        self.handle_cookies()

        try:
            selectors = [
                (By.CLASS_NAME, 'sc-btn-primary'),
                (By.CLASS_NAME, 'privacy-consent-accept'),
                (By.CSS_SELECTOR, '[data-testid="consent-button"]'),
                (By.XPATH, '//button[contains(text(), "Accept All")]'),
            ]

            for by, selector in selectors:
                try:
                    cookie_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    cookie_button.click()
                    break
                except:
                    continue

            self.load_cookies()
            self.driver.refresh()
            self.base_window = self.driver.window_handles[0]
        except Exception as e:
            logger.error(f"Error setting up driver: {e}")
            self.driver.quit()
            raise

    def handle_cookies(self):
        if not self.load_cookies():
            try:
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe'))
                )
                self.driver.switch_to.frame('sp_message_iframe_1235490')
                settings_btn = WebDriverWait(self.driver, 2).until(
                     EC.element_to_be_clickable((By.XPATH, '//*[@id="notice"]/div[2]/button'))
                 )
                settings_btn.click()
                self.driver.switch_to.default_content()

            except Exception as e:
                logger.error(f"Error handling cookie consent: {e}")

    def load_cookies(self):
        try:
            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            return True
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False

    def save_cookies(self):
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'wb') as file:
            pickle.dump(cookies, file)

    def extract_car_data(self) -> Optional[CarData]:
        try:
            url = self.driver.current_url
            brand = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/main/div[2]/div[1]/div/h1'))
            ).text
            model_ver  = None
            price_text = self.driver.find_element(By.CLASS_NAME, 'resp-price-main').text
            price_text = price_text.strip('€').replace(',', '').replace(' ', '')
            price = int(price_text)
            year_text = self.driver.find_element(By.XPATH, "//strong[contains(text(),'Rok:')]/parent::div").text
            year = year_text.strip().replace('Rok: ', '')
            location = self.driver.find_element(By.XPATH, "//div[@title='Lokalita']").text
            fuel = self.driver.find_element(By.XPATH, "//strong[contains(text(), 'Palivo:')]/parent::div").text
            engine_power = self.driver.find_element(By.XPATH, "//strong[contains(text(),'Výkon motora:')]/parent::div").text
            gearbox = self.driver.find_element(By.XPATH, "//strong[contains(text(),'Prevodovka:')]/parent::div").text
            mileage = self.driver.find_element(By.XPATH, "//strong[contains(text(), 'Počet km:')]/parent::div").text

            return CarData(
                url=url,
                brand=brand,
                model_ver=model_ver,
                price=price,
                year=year,
                location=location,
                fuel=fuel,
                engine_power=engine_power,
                gearbox=gearbox,
                mileage=mileage
            )
        except Exception as e:
            logger.error(f"Error extracting car data: {e}")
            return None

    def scrape(self):
        self.setup_driver()
        time.sleep(20)
        self.base_window = self.driver.current_window_handle
        items = self.driver.find_elements(By.CSS_SELECTOR, 'section.resp-search-results div.resp-item')
        print(len(items))
        links = []
        for item in items:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                links.append(link)
            except NoSuchElementException as e:
                logger.error(f"Error extracting link: {e}")

        batch_size = 5
        for i in range (0, len(links), batch_size):
            batch = links[i:i + batch_size]
            self.process_batch(batch)
        self.driver.quit()

    def process_batch(self, batch):
        for link in batch:
            self.driver.execute_script("window.open('{}');".format(link))
            time.sleep(1)

        window_handles = self.driver.window_handles[1:]

        for window in window_handles:
            self.driver.switch_to.window(window)
            WebDriverWait(self.driver, 30).until(
                lambda x: x.execute_script("return document.readyState") == "complete"
            )

            if 'autovia' not in self.driver.current_url:
                logger.info("Not an autovia link, closing tab.")
                self.driver.quit()
                continue

            car_data = self.extract_car_data()
            if car_data:
                logger.info(car_data)
            self.driver.close()
            self.driver.switch_to.window(self.base_window)
def main():
    scraper = AutoviaScraper(AUTOVIA_URL, AUTOVIA_COOKIES_FILE)
    scraper.scrape()

if __name__ == '__main__':
    main()
