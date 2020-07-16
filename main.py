from bs4 import BeautifulSoup
import requests
import logging

namnyamURL = "https://www.nam-nyam.ru/catering/"

class foodItem:

    def __init__(self, title, weight, calories, price, link):
        self.title = title
        self.weight = weight
        self.calories = calories
        self.price = price
        self.link = link

    def __str__(self):
        return f"""
{self.title}
{self.weight}
{self.calories}
{self.price}
{self.link}\n
        """


def getDailyMenu(url: str):

    dailyMenu = {}

    dailyMenuSoup = BeautifulSoup(url, 'lxml')

    dailyMealTypes = dailyMenuSoup.find_all('div', class_='catering_item included_item')

    for mealType in dailyMealTypes:
        typeLabel = mealType.find('div', class_='catering_item_name catering_item_name_complex').text.strip()
        if not typeLabel:
            continue
        dailyMenu[typeLabel] = []
        foods = mealType.find('ul', class_='list_included_item').find_all('li')
        for item in foods:

            weight = None
            calories = None
            price = None
            link = f"https://www.nam-nyam.ru{item.a['href']}"

            foodPage = requests.get(link).text

            foodPageSoup = BeautifulSoup(foodPage, 'lxml')

            match = foodPageSoup.find('div', class_='right_pos')

            title = match.find('h1').text.strip()

            if title == 'Страница не найдена':
                title = item.find('span', class_='complex_tooltip').text.strip()
                weight = ' '.join(item.find('span', class_='catering_item_weight').text.split(' ')[1:])
                dailyMenu[typeLabel].append(foodItem(title, weight, calories, price, link))
                continue

            item_desc = foodPageSoup.find('td', itemprop="offers")

            for line in item_desc.find_all('p'):
                if line.text.startswith("Вес: "):
                    weight = ' '.join(line.text.split(' ')[1:])
                elif line.text.startswith("Калорийность: "):
                    calories = ' '.join(line.text.split(' ')[1:])

            price = ' '.join(item_desc.find('div', id="item_price_block").text.split(' ')[1:])

            dailyMenu[typeLabel].append(foodItem(title, weight, calories, price, link))

    return dailyMenu

import pandas as pd

try:
    dailyMenu = getDailyMenu(requests.get(namnyamURL).text)
    dailyMenu = {k: [x.title for x in v] for k, v in dailyMenu.items()}

    writer = pd.ExcelWriter("result.xlsx", engine='xlsxwriter') # pylint: disable=abstract-class-instantiated

    columns = []

    for mealType, foods in dailyMenu.items():
        columns.append(pd.Series(foods, name=mealType))

    result = pd.concat(columns, axis=1)

    # Convert the dataframe to an XlsxWriter Excel object.
    result.to_excel(writer, sheet_name='Main', index=False)

    # Get the xlsxwriter workbook and worksheet objects.
    workbook  = writer.book
    worksheet = writer.sheets['Main']

    # Set the column width and format.
    worksheet.set_column('A:D', 30, None)

    # Close the Pandas Excel writer and output the Excel file.
    writer.save()


except Exception:
    logging.exception('e')
