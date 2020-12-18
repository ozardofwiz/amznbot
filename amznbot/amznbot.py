from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from twilio.rest import Client
from time import sleep
from datetime import datetime
from amazoncaptcha import AmazonCaptcha
from threading import Thread
import random
import re


class AmznBot:
    """
    TODO:
        * re-run the whole app if the item hasn´t been added to the basket
        * TODO: Add handler for captcha landing page and login required that runs
        * say every 5 secs and checks the two conditions and joins the thread if
        * at least one is true then handles the resolving
    """

    def __init__(self, website, include_whd=False):
        # TODO: Open existing chrome session to make it obsolete to login

        # options = webdriver.ChromeOptions()
        # options.add_argument(
        #     "user-data-dir=/Users/Tobias/Library/Application Support/Google/Chrome/"
        # )  # Path to your chrome profile
        # self.driver = webdriver.Chrome(
        #     chrome_options=options,
        # )

        # User Agent:
        # Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36

        self.driver = webdriver.Chrome()
        self.website = website
        self.include_whd = include_whd

        self.link = ""
        if self.website.isamazonde():
            self.link = "https://www.amazon.de/product/dp/B08H93ZRK9"
        elif self.website.isamazoncouk():
            self.link = "https://www.amazon.co.uk/product/dp/B08H95Y452"

    def run(self):
        self.__load_site()

        self.run_i = 1
        if self.run_i == 1:
            # Einloggen manuell
            print(
                "Please log-in to your Amazon account.\nMake sure your basket is empty."
            )
            input("Press Enter to continue...")

            print("Script is running..")
        self.run_i += 1

        self.__check_in_stock()

        # Send SMS notification in new Thread
        msg = "Playsi is in stock on Amazon!\n" + str(datetime.now()) + "\n" + self.link
        self.sms_thread = Thread(target=self.__send_sms_message, args=[msg])
        self.sms_thread.start()

        # In stock!
        exec_start_time = datetime.now()

        order_1_click_success = self.__try_order_1_click()

        if not order_1_click_success:
            self.__try_order_regular()

        congrats = "CONGRATS, YOU'VE GOT YASELF A PLAYSI MATE!\n" + str(datetime.now())
        print(congrats)

        # Succesfully Ordered!
        exec_end_time = datetime.now()
        exec_delta = exec_start_time - exec_end_time
        print(f"Order took: {exec_delta.total_seconds():.2f} seconds to complete.")

        self.__send_sms_message(congrats)

        self.sms_thread.join()

        input("Press Enter to exit...")

    def __load_site(self):
        try:
            # Open Chrome and load website
            self.driver.get(self.link)
        except Exception as e:
            print(e)

            sleep(2)
            self.__load_site()

    # Recursive
    def __check_in_stock(self):
        availability_text = self.driver.find_element_by_xpath(
            "//div[@id='availability']/span"
        ).text

        print("Playstation 5:", availability_text, "\n", datetime.now())

        if "Currently unavailable." in availability_text:
            # wait random secs (between x and y)
            sleep_random_secs = random.uniform(1, 2)
            sleep(sleep_random_secs)

            # refresh page
            self.driver.refresh()

            self.__check_captcha_landingpage()

            # recursion/ try again
            self.__check_in_stock()
        elif "In stock." in availability_text:
            return
        else:
            # f.e. Available from these resellers
            # Only x left in stock

            # Send SMS notification in new Thread
            msg = (
                "Playsi is AVAILABLE FROM THESE RESELLERS on Amazon!\n"
                + str(datetime.now())
                + "\n"
                + self.link
            )
            sms_thread2 = Thread(target=self.__send_sms_message, args=[msg])
            sms_thread2.start()

            # Load List of Sellers
            list_of_sellers_link = ""
            if self.website.isamazonde():
                list_of_sellers_link = "https://www.amazon.de/gp/offer-listing/B08H93ZRK9/ref=dp_olp_afts?ie=UTF8&condition=all"
            elif self.website.isamazoncouk():
                list_of_sellers_link = "https://www.amazon.co.uk/gp/offer-listing/B08H95Y452/ref=dp_olp_afts?ie=UTF8&condition=all"

            # Refresh page as long as it is displayed properly
            i = 1
            while True:
                if i > 50:
                    break
                i += 1
                self.driver.get(list_of_sellers_link)

                if self.__check_element_exist("//input[@name='submit.addToCart']"):
                    break

                # wait random secs (between x and y)
                sleep_random_secs = random.uniform(1, 2)
                sleep(sleep_random_secs)
                self.driver.refresh()

                self.__check_captcha_landingpage()
            if i > 50:
                self.run()

            row = self.driver.find_element_by_xpath(
                "//div[@id='olpOfferList']//div[@role='row' and contains(@class,'olpOffer')][1]"
            )

            offer_price = 0.0

            if self.website.isamazonde():
                offer_price_text = row.find_element_by_xpath(
                    "//span[contains(text(), 'EUR')]"
                ).text

                # Get substring price as float
                matches = re.findall(r"[+-]?\d+\,\d+", offer_price_text)
                offer_price = float(matches[0].replace(",", "."))

                print(f"offer price: EUR {offer_price}")
            elif self.website.isamazoncouk():
                offer_price_text = row.find_element_by_xpath(
                    "//span[contains(text(), '£')]"
                ).text

                # Get substring price as float
                matches = re.findall(r"[+-]?\d+\.\d+", offer_price_text)
                offer_price = float(matches[0])

                print(f"offer price: £ {offer_price}")

            if offer_price < 500 and offer_price > 400:
                print("Price between 500 and 400!")
                row.find_element_by_xpath("//input[@name='submit.addToCart']").click()
            else:
                print("Price not in the given price range.")

            self.__check_login_required()

            self.__click_element_savely("//span[@id='hlb-ptc-btn']")

            self.__check_login_required()

            # ATTENTION WILL BUY PRODUCT
            self.__click_element_savely("//input[@name='placeYourOrder1']")

            sms_thread2.join()

    def __check_available_from_these_sellers(self):
        if self.include_whd:
            whd_in_stock = self.__check_element_exist(
                "//div[@id='availability']/span[contains(text(), \
                    'Available from these sellers')]"
            )

            if not whd_in_stock:
                return

            print("PLAYSTATION 5: AVAILABLE FROM THESE SELLERS\n", datetime.now())
            # Send SMS notification in new Thread
            msg = (
                "Playsi is AVAILABLE FROM THESE RESELLERS on Amazon!\n"
                + str(datetime.now())
                + "\n"
                + self.link
            )
            sms_thread2 = Thread(target=self.__send_sms_message, args=[msg])
            sms_thread2.start()

            # Load List of Sellers
            list_of_sellers_link = ""
            if self.website.isamazonde():
                list_of_sellers_link = "https://www.amazon.de/gp/offer-listing/B08H93ZRK9/ref=dp_olp_afts?ie=UTF8&condition=all"
            elif self.website.isamazoncouk():
                list_of_sellers_link = "https://www.amazon.co.uk/gp/offer-listing/B08H95Y452/ref=dp_olp_afts?ie=UTF8&condition=all"

            # Refresh page as long as it is displayed properly
            while True:
                self.driver.get(list_of_sellers_link)

                if self.__check_element_exist("//input[@name='submit.addToCart']"):
                    break

                sleep(1)
                self.driver.refresh()

                self.__check_captcha_landingpage()

            row = self.driver.find_element_by_xpath(
                "//div[@id='olpOfferList']//div[@role='row' and contains(@class,'olpOffer')][1]"
            )

            offer_price_text = row.find_element_by_xpath(
                "//span[contains(text(), 'EUR')]"
            ).text

            # Get substring price as float
            offer_price = float(re.findall(r"[+-]?\d+\.\d+", offer_price_text)[0])
            print(f"offer price: EUR {offer_price}")

            if offer_price < 500 and offer_price > 400:
                row.find_element_by_xpath("//input[@name='submit.addToCart']").click()

            self.__check_login_required()

            # //a[text()[contains(.,'Proceed to checkout')]]
            self.driver.find_element_by_xpath(
                "//a[text()[contains(.,'Proceed to checkout')]]"
            ).click()

            self.__check_login_required()

            # ATTENTION WILL BUY PRODUCT
            self.__click_element_savely("//input[@name='placeYourOrder1']")

            sms_thread2.join()
        else:
            return

    def __check_captcha_landingpage(self):
        # Check if captchacharacters Input exists
        captcha_exist = self.__check_element_exist("//input[@id='captchacharacters']")

        if captcha_exist:
            captchafield = self.__click_element_savely(
                "//input[@id='captchacharacters']"
            )

            try:
                # Need to solve Captcha
                captchaimglink = self.driver.find_element_by_xpath(
                    "//*[contains(@src,'/captcha/')]"
                ).get_attribute("src")
                captcha = AmazonCaptcha.fromlink(captchaimglink)
                solution = captcha.solve()

                print("captcha solution was: ", solution)

                captchafield.send_keys(solution)
                sleep(1)

                self.__click_element_savely("//button[@type='submit']")
                print("Captcha solved at", datetime.now())
            except Exception as e:
                print("Exception raised, check_captcha_landingpage")
                print(e)

    def __try_order_1_click(self):
        self.__check_captcha_landingpage()

        # Check if 1-Click Button exist
        one_click = self.__check_element_exist("//input[@id='buy-now-button']")

        if one_click:
            # TODO try except block
            # if TimeoutException navigate to
            print("One Click is available.")

            self.__click_element_savely("//input[@id='buy-now-button']")

            self.__check_login_required()

            checkout_success = self.__1_click_checkout()

            if not checkout_success:
                self.__fallback_strategy_checkout()

            return True
        else:
            print("One Click not available.")
            return False

    def __1_click_checkout(self):
        try:
            if self.website.isamazonde():
                # Switch to the iframe
                WebDriverWait(self.driver, 10).until(
                    EC.frame_to_be_available_and_switch_to_it(
                        (By.XPATH, "//iframe[@id='turbo-checkout-iframe']")
                    )
                )

                # Make sure button is loaded properly
                clickable = EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//input[@id='turbo-checkout-pyo-button']",
                    )
                )
                turbo_checkout_button = WebDriverWait(self.driver, 10).until(clickable)
                # ATTENTION!
                turbo_checkout_button.click()

                # switch back to default frame
                self.driver.switch_to.default_content()
                return True
            elif self.website.isamazoncouk():
                # ATTENTION!
                self.__click_element_savely(
                    "//input[@name='placeYourOrder1']", timeout=6
                )
                return True
        except (TimeoutException, NoSuchElementException):
            return False
        except Exception as e:
            print(e)
            return False

    def __try_order_regular(self):
        self.__check_captcha_landingpage()

        # Add to Cart
        self.__click_element_savely("//input[@id='add-to-cart-button']")

        self.__check_captcha_landingpage()

        # Proceed to checkout
        sidesheet_checkout_success = self.__sidesheet_checkout()

        # -> loads basket manually.
        if not sidesheet_checkout_success:
            self.__fallback_strategy_checkout()

        self.__check_captcha_landingpage()

        self.__check_login_required()

        # ATTENTION WILL BUY PRODUCT
        self.__click_element_savely("//input[@name='placeYourOrder1']")

        if self.__check_element_exist("//input[@name='forcePlaceOrder']"):
            self.__click_element_savely("//input[@name='forcePlaceOrder']", timeout=2)

    def __sidesheet_checkout(self):
        """Tries to proceed the order via the sidesheet.

        Returns:
            True: If sidesheet process runs smoothly.
            False: If process fails (f.e. page redirection occurs) or takes
            too much time.

        """
        try:
            sidesheet_loaded = EC.element_to_be_clickable(
                (By.XPATH, "//span[@id='attach-sidesheet-checkout-button']/span/input")
            )
            checkout_button = WebDriverWait(self.driver, 7).until(sidesheet_loaded)
            checkout_button.click()

            return True
        except (TimeoutException, NoSuchElementException):
            return False
        except Exception as e:
            print(e)
            return False

    def __fallback_strategy_checkout(self):
        # TODO: Check if item is in basket, otherwise start from beginning

        self.__check_captcha_landingpage()

        basket_link = ""
        if self.website.isamazonde():
            basket_link = "https://www.amazon.de/gp/cart/view.html?ref_=nav_cart"
        elif self.website.isamazoncouk():
            basket_link = "https://www.amazon.co.uk/gp/cart/view.html?ref_=nav_cart"

        # Navigate to Basket
        self.driver.get(basket_link)

        self.__click_element_savely("//input[@name='proceedToRetailCheckout']")

    # Recursive
    def __check_login_required(self):
        if self.__check_element_exist("//input[@id='ap_password']"):
            self.driver.find_element_by_xpath("//input[@id='ap_password']").send_keys(
                "<password>"
            )

            if self.__check_element_exist("//input[@id='auth-captcha-guess']"):
                # Need to solve Captcha
                captchaimglink = self.driver.find_element_by_xpath(
                    "//img[@id='auth-captcha-image']"
                ).get_attribute("src")

                captcha = AmazonCaptcha.from_webdriver(captchaimglink)
                solution = captcha.solve()

                print("captcha solution was: ", solution)

                self.driver.find_elment_by_xpath(
                    "//input[@id='auth-captcha-guess']"
                ).send_keys(solution)
                sleep(1)

                self.__click_element_savely("//button[@type='submit']")
                print("Captcha solved at", datetime.now())

            self.__click_element_savely("//input[@id='signInSubmit']")
            sleep(1)
            self.__check_login_required()
        else:
            return

    def __click_element_savely(self, xpath, timeout=60):
        """Tries to click on webelement asap in a safe way.

        Args:
            xpath (str): XPath query to locate element.
            timeout (float): wait x seconds before TimeoutException is raised.

        Returns:
            WebElement: if clicked successfully returns the WebElement. Otherwise
                        returns None.

        """

        try:
            clickable = EC.element_to_be_clickable((By.XPATH, xpath))
            webelement = WebDriverWait(self.driver, timeout).until(clickable)

            if clickable:
                webelement.click()
                return webelement
            else:
                return None
        except TimeoutException:
            print("TimeoutException raised, click_element_savely:", xpath)
            return None
        except Exception as e:
            print("Exception raised, click_element_savely", xpath)
            print(e)
            return None

    def __click_element(self, xpath):
        try:
            webelement = self.driver.find_element_by_xpath(xpath)
            webelement.click()
            return webelement
        except NoSuchElementException:
            return None
        except Exception as e:
            print(e)
            return None

    def __check_element_exist(self, xpath):
        try:
            self.driver.find_element_by_xpath(xpath)
            return True
        except NoSuchElementException:
            return False
        except Exception as e:
            print("Exception raised, check_element_exist", xpath)
            print(e)
            return False

    def __send_sms_message(self, msg):
        acc_sid = ""
        auth_token = ""
        client = Client(acc_sid, auth_token)

        client.messages.create(
            body=msg,
            from_="",
            to="",
        )