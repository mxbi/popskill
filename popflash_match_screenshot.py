from selenium import webdriver
from time import sleep
from io import BytesIO

class PopflashScreenshotter:
  def __init__(self):
    self.

def screenshot(match_id):
  match_url = ("https://popflash.site/match/" + str(match_id))
  login_cookie = open("sid.txt", "r").read().strip()

  options = webdriver.ChromeOptions()
  options.headless = True
  browser = webdriver.Chrome(options=options)

  print('opened webdriver')

  browser.get(match_url)
  sleep(1)
  browser.add_cookie({"name": "connect.sid", "value": login_cookie})
  browser.refresh()
  browser.set_window_size(1100, 1500)
  page_container = browser.find_element_by_xpath('//*[@id="page-container"]')
  img = page_container.screenshot_as_png

  return img

if __name__ == "__main__":
  print(screenshot("1148142"))
