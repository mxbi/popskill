from selenium import webdriver
from time import sleep
from io import BytesIO

class PopflashScreenshotter:
  def __init__(self):
    options = webdriver.ChromeOptions()
    options.headless = True
    self.browser = webdriver.Chrome(options=options)
    self.login_cookie = open("sid.txt", "r").read().strip()
    print('Started selenium.')


    def screenshot(match_id):
      match_url = ("https://popflash.site/match/" + str(match_id))
      

      print('opened webdriver')

      self.browser.get(match_url)
      sleep(0.5)
      self.browser.add_cookie({"name": "connect.sid", "value": self.login_cookie})
      self.browser.refresh()
      self.browser.set_window_size(1100, 1500)
      page_container = self.browser.find_element_by_xpath('//*[@id="page-container"]')
      img = page_container.screenshot_as_png

      return img

if __name__ == "__main__":
  print(PopflashScreenshotter().screenshot("1148142"))
