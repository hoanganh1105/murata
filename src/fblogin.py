from selenium import webdriver
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pickle
browser = webdriver.Chrome()

browser.get("http://facebook.com")
txtUser = browser.find_element(By.ID, "email")
txtUser.send_keys("")
txtPassword = browser.find_element(By.ID, "pass")
txtPassword.send_keys("")
txtPassword.send_keys(Keys.ENTER)

pickle.dump(browser.get_cookies(), open("my_cookie.pkl", "wb"))


sleep(100)   
browser.close()