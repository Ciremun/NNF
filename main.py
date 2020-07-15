from bs4 import BeautifulSoup
import requests
import logging

class foodItem:

    def __init__(self, title, weight, calories, price, link):
        self.title = title
        self.weight = weight
        self.calories = calories
        self.price = price
        self.link = link

foods = []
namnyamURL = "https://www.nam-nyam.ru/"

try:
    homepage = requests.get(namnyamURL).text
except Exception:
    logging.exception('e')

def getFoodHits(url: str):

    soup = BeautifulSoup(url, 'lxml')

    hits = soup.find_all('div', class_='catering_item_wrapper')

    for item in hits:

        # get food link
        soup = BeautifulSoup(str(item), 'lxml')
        match = soup.find('a', id='example1')
        link = f"{namnyamURL[:-1]}{match['href']}"

        # get food info
        foodpage = requests.get(link).text
        soup = BeautifulSoup(foodpage, 'lxml')
        match = soup.find('div', class_='right_pos')

        title = match.find('h1').text.strip()

        item_desc = soup.find('td', itemprop="offers")
        weight = None
        calories = None
        price = None

        for line in item_desc.find_all('p'):
            if line.text.startswith("Вес: "):
                weight = ' '.join(line.text.split(' ')[1:])
            elif line.text.startswith("Калорийность: "):
                calories = ' '.join(line.text.split(' ')[1:])

        price = ' '.join(item_desc.find('div', id="item_price_block").text.split(' ')[1:])

        foods.append(foodItem(title, weight, calories, price, link))

getFoodHits(homepage)

print()
for item in foods:
    print(item.title)
    print(item.weight)
    print(item.calories)
    print(item.price)
    print(item.link)
    print()