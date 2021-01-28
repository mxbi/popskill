import requests
from bs4 import BeautifulSoup
import pandas as pd

def _strip_links_from_table(table):
  links = []
  for row in table.find_all('tr')[1:]:
    links.append(row.find_all('td')[0].find('a')['href'])
  return links

def get_profile(url):
  # df = pd.read_html(url)
  page = requests.get(url)
  soup = BeautifulSoup(page.text, 'html.parser')

  name = soup.select('#page-container > div:nth-child(2) > div > div:nth-child(1) > h3 > span:nth-child(1)')[0].text

  tab = soup.find_all(class_='latest-matches')
  assert len(tab) == 1
  tab = tab[0].find_all('table')
  assert len(tab) == 1
  tab = tab[0]

  df = pd.read_html(str(tab), header=0)[0]
  df['match_link'] = _strip_links_from_table(tab)

  return {'match_table': df, 'id': url.split('/')[-1], 'name': name}

def get_match(url):
  if url.startswith('/match'):
    url = 'https://popflash.site' + url
  if url.isnumeric():
    url = 'https://popflash.site/match/' + url
  
  print(url)
  page = requests.get(url)
  soup = BeautifulSoup(page.text, 'html.parser')

  assert "Match is final" in page.text, "Tried adding non-final match"

  response = {}
  response['team1score'] = int(soup.select('#match-container > div:nth-child(2) > div:nth-child(1) > div > div.score.score-1')[0].text.strip())
  response['team2score'] = int(soup.select('#match-container > div:nth-child(2) > div:nth-child(1) > div > div.score.score-2')[0].text.strip())

  team1table = soup.select('#match-container > div.scoreboards > div:nth-child(1) > table:nth-child(1)')[0]
  team2table = soup.select('#match-container > div.scoreboards > div:nth-child(2) > table:nth-child(1)')[0]

  df1 = pd.read_html(str(team1table), header=0)[0]
  df2 = pd.read_html(str(team2table), header=0)[0]
  df1['player_link'] = _strip_links_from_table(team1table)
  df2['player_link'] = _strip_links_from_table(team2table)
  df1['id'] = df1['player_link'].apply(lambda x: x.split('/')[-1])
  df2['id'] = df2['player_link'].apply(lambda x: x.split('/')[-1])

  response['team1table'] = df1
  response['team2table'] = df2
  
  response['date'] = soup.select('#match-container > h2 > span')[0]['data-date']
  response['match_id'] = url.split('/')[-1]

  response['map_image'] = soup.select('#match-container > div:nth-child(2) > div:nth-child(2) > img')[0]['src']

  return response


if __name__ == '__main__':
  print(get_profile('https://popflash.site/user/1598215'))
  print(get_match('https://popflash.site/match/1147113'))

