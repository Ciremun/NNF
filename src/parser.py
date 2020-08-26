import logging

import requests
import pandas as pd
from bs4 import BeautifulSoup

from .structure import FoodItem, ShortFoodItem


namnyamURL = "https://www.nam-nyam.ru/catering/"


# def createExcel():
#     try:
#         dailycomplex, dailyMenu = getDailyMenu(requests.get(namnyamURL).text)
#         dailyMenu = {k: [f'{x.title}, {x.weight}, {x.calories}, {x.price}' for x in v] for k, v in dailyMenu.items()}

#         columns = [pd.Series(foods, name=mealType) for mealType, foods in dailyMenu.items()]

#         writer = pd.ExcelWriter("result.xlsx", engine='xlsxwriter')

#         result = pd.concat(columns, axis=1)
#         result.to_excel(writer, sheet_name='Main', index=False)

#         worksheet = writer.sheets['Main']
#         worksheet.set_column('A:D', 55, None)

#         writer.save()

#         print('.xlsx created')
#     except Exception:
#         logging.exception('e')

def getDailyMenu(url: str):

    catering = {'complex': {}, 'items': {}}
    dailyMenuSoup = BeautifulSoup(url, 'lxml')
    dailyMealTypes = dailyMenuSoup.find_all('div', class_='catering_item included_item')

    for mealType in dailyMealTypes:

        typeLabel = mealType.find('div', class_='catering_item_name catering_item_name_complex').text.strip()

        typeLabel+= f". {' '.join(mealType.find('div', class_='catering_item_price').text.split(' ')[1:])}"

        catering['complex'][typeLabel] = []

        foods = mealType.find('ul', class_='list_included_item').find_all('li')

        for item in foods:

            link = f"https://www.nam-nyam.ru{item.a['href']}"
            image_link = f"https://www.nam-nyam.ru{item.find('div', class_='img')['data-src']}"
            catering['complex'] = parseFoodPage(item, link, image_link, typeLabel, catering['complex'], itemGroup='complex')

    dailyMealsMenuGroups = [x.parent for x in dailyMenuSoup.find_all('div', class_="catering-sm-slider")]

    for group in dailyMealsMenuGroups:

        typeLabel = group.find('div', class_="h2").text.strip()
        groupFoods = group.find('div', class_="catering-sm-slider").find_all('div', class_="catering_item")

        catering['items'][typeLabel] = []

        for item in groupFoods:

            item = item.find('div', class_="catering_item_wrapper")
            link = f"https://www.nam-nyam.ru{item.a['href']}"
            image_link = f"https://www.nam-nyam.ru{item.a.find('img')['src']}"

            catering['items'] = parseFoodPage(item, link, image_link, typeLabel, catering['items'], itemGroup='menu')

    return catering

def parseFoodPage(item, foodPageLink, image_link, typeLabel, items_dict, itemGroup=None):

    title = "Без имени"
    weight = '?'
    calories = '?'
    price = 0

    print(foodPageLink)

    foodPage = requests.get(foodPageLink).text
    foodPageSoup = BeautifulSoup(foodPage, 'lxml')

    match = foodPageSoup.find('div', class_='right_pos')
    title = match.find('h1').text.strip()

    if title == 'Страница не найдена':
        if itemGroup == 'complex':
            title = item.find('span', class_='complex_tooltip').text.strip()
            weight = ' '.join(item.find('span', class_='catering_item_weight').text.split(' ')[1:])
        elif itemGroup == 'menu':
            title = item.find('div', class_="catering_item_name _showtooltip").text.strip()
            weight = ' '.join(item.find('div', class_="catering_item_weight").text.strip().split(' ')[1:])
            price = ''.join(item.find('div', class_="catering_item_price").text.strip().split(' ')[1:-1])

        items_dict[typeLabel].append(FoodItem(title, weight, calories, price, foodPageLink, image_link))
        return items_dict

    if title.startswith('.'):
        title = title[1:]

    item_desc = foodPageSoup.find('td', itemprop="offers")

    if not item_desc:
        items_dict[typeLabel].append(FoodItem('?', weight, calories, price, foodPageLink, image_link))
        return items_dict

    for line in item_desc.find_all('p'):
        if line.text.startswith("Вес: "):
            weight = ' '.join(line.text.split(' ')[1:])
        elif line.text.startswith("Калорийность: "):
            calories = f"{' '.join(line.text.split(' ')[1:])} ккал"

    price = ''.join(item_desc.find('div', id="item_price_block").text.split(' ')[1:-1])

    items_dict[typeLabel].append(FoodItem(title, weight, calories, price, foodPageLink, image_link))
    return items_dict
