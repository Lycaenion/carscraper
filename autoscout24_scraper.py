import pickle
import time
import sys
import logging
import project_db
from dataclasses import dataclass
from typing import Optional
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

AUTOSCOUT24_URL = "https://www.autoscout24.com/lst?atype=C&cy=D%2CA%2CB%2CE%2CF%2CI%2CL%2CNL&damaged_listing=exclude&desc=1&powertype=kw&search_id=1wuxwwg2mq5&sort=age&source=homepage_search-mask&ustate=N%2CU"
AUTOSCOUT24_COOKIES_FILE = 'cookies/autoscout24.pkl'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_out = logging.StreamHandler(sys.stdout)
filehandler = logging.FileHandler('autoscout24_scraper.log', encoding='utf-8')
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

class Autoscout24Scraper:
    def __init__(self, url: str, cookies_file: str):
        self.url = url
        self.cookies_file = cookies_file
        self.driver = None
        self.base_window = None

    def setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("window-size=1920,4080")
        self.driver = webdriver.Chrome(options = options)
        self.driver.get(self.url)
        if self.load_cookies() is not True:
            self.handle_cookies()
        self.driver.refresh()
        self.base_window = self.driver.window_handles[0]

    def handle_cookies(self):
        if not self.load_cookies():
            cookie_banner = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.ID, 'as24-cmp-popup'))
            )
            privacy_button = self.driver.find_element(By.XPATH, "//button[contains(@class,'_consent-settings_1lphq_103')]")
            privacy_button.click()

            save_button = self.driver.find_element(By.XPATH, '//*[@id="root"]/div/article/section[1]/button[2]')
            save_button.click()
            self.save_cookies()
        else:
            self.load_cookies()


    def load_cookies(self):
        try:
            with open(self.cookies_file, 'rb') as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            return True
        except FileNotFoundError:
            logger.info("Cookies file not found. Proceeding without loading cookies.")
            return False

    def save_cookies(self):
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'wb') as file:
            pickle.dump(cookies, file)

    def extract_car_data(self) -> Optional[CarData]:
        try:
            wait = WebDriverWait(self.driver, 5)
            brand = wait.until(EC.presence_of_element_located(
                (By.CLASS_NAME, 'StageTitle_makeModelContainer__RyjBP'))).text
            model_ver = self.driver.find_element(By.CLASS_NAME, 'StageTitle_modelVersion__Yof2Z').text
            price_text = self.driver.find_element(By.CLASS_NAME, 'PriceInfo_price__XU0aF').text
            if len(price_text) > 8:
                price_text = price_text[:-1]
            price = int(price_text.strip('€').replace(' ', '').replace(',', ''))

            try:
                year = self.driver.find_element(By.XPATH, "(//div[contains(@class, 'StageArea_overviewContainer__UyZ9n')]//div[contains(@class,'VehicleOverview_itemText__AI4dA')])[3]").text
            except NoSuchElementException as e:
                logger.exception(self.driver.page_source.encode('utf-8'))
                self.driver.save_screenshot('screen.png')
                year = None

            try:
                location_element = self.driver.find_element(By.XPATH,"//*[@id='vendor-and-cta-section']//*[starts-with(@class,'Department_departmentContainer')]/a")
            except NoSuchElementException:
                location_element = None
                logger.exception(self.driver.page_source.encode('utf-8'))
                self.driver.save_screenshot('location_screen.png')

            if location_element is not None:
                location = location_element.text
            else:
                location = None

            try:
                fuel = self.driver.find_element(By.XPATH, "(//div[contains(@class, 'StageArea_overviewContainer__UyZ9n')]//div[contains(@class,'VehicleOverview_itemText__AI4dA')])[4]").text
            except NoSuchElementException:
                fuel = None

            try:
                engine_power = self.driver.find_element(By.XPATH, "(//div[contains(@class, 'StageArea_overviewContainer__UyZ9n')]//div[contains(@class,'VehicleOverview_itemText__AI4dA')])[5]").text
            except NoSuchElementException as e:
                logger.exception(self.driver.page_source.encode('utf-8'))
                self.driver.save_screenshot('screen.png')
                engine_power = None

            try:
                gearbox = self.driver.find_element(By.XPATH, "(//div[contains(@class, 'StageArea_overviewContainer__UyZ9n')]//div[contains(@class,'VehicleOverview_itemText__AI4dA')])[2]").text
            except NoSuchElementException as e:
                logger.exception(self.driver.page_source.encode('utf-8'))
                self.driver.save_screenshot('screen.png')
                gearbox = None

            try:
                mileage = self.driver.find_element(By.XPATH, "(//div[contains(@class, 'StageArea_overviewContainer__UyZ9n')]//div[contains(@class,'VehicleOverview_itemText__AI4dA')])[1]").text
            except NoSuchElementException as e:
                logger.exception(self.driver.page_source.encode('utf-8'))
                self.driver.save_screenshot('screen.png')
                mileage = None

            return CarData(
                url=self.driver.current_url,
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
            logger.info(f"Error extracting car data: {e}")
            return None

    def scrape(self):
        self.setup_driver()
        self.base_window = self.driver.current_window_handle

        items = WebDriverWait(self.driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article'))
        )
        links = []
        for item in items:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                links.append(link)
            except NoSuchElementException:
                continue

        batch_size = 5
        for i in range(0, len(links), batch_size):
            batch = links[i:i + batch_size]
            self.process_batch(batch)

        self.driver.quit()

    def process_batch(self, batch):
        # Open new tabs for each link
        for link in batch:
            self.driver.execute_script("window.open('{}');".format(link))
            time.sleep(0.5)

        # Get all windows except the main window
        window_handles = self.driver.window_handles[1:]  # Skip the main/first window

        # Process each window
        for window in window_handles:
            # Switch to the specific window
            self.driver.switch_to.window(window)

            # Wait for page to load completely
            WebDriverWait(self.driver, 5).until(
                lambda x: x.execute_script("return document.readyState") == "complete"
            )

            # Check if we're on the correct site
            if 'autoscout24.com' not in self.driver.current_url:
                logger.info("Not an autoscout24 page, closing tab.")
                self.driver.close()
                continue

            # Extract and process car data
            car_data = self.extract_car_data()
            if car_data:
                logger.info(car_data)
                project_db.add_to_db(
                    url=car_data.url,
                    webpage_name='autoscout24',
                    brand=car_data.brand,
                    model_version=car_data.model_ver,
                    year=car_data.year,
                    price=car_data.price,
                    mileage=car_data.mileage,
                    gearbox=car_data.gearbox,
                    fuel_type=car_data.fuel,
                    engine_power=car_data.engine_power,
                    location=car_data.location
                )

            # Close the current window
            self.driver.close()

        # Return to the main window
        self.driver.switch_to.window(self.base_window)

def main():
    scraper = Autoscout24Scraper(AUTOSCOUT24_URL, AUTOSCOUT24_COOKIES_FILE)
    scraper.scrape()

if __name__ == '__main__':
    print(logger.handlers)
    main()