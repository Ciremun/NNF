from bs4 import BeautifulSoup
import requests
import logging
import pandas as pd
import threading

namnyamURL = "https://www.nam-nyam.ru/catering/"

class namnyamParser(threading.Thread):

    class foodItem:

        def __init__(self, title, weight, calories, price, link, image_link):
            self.title = title
            self.weight = weight
            self.calories = calories
            self.price = price
            self.link = link
            self.image_link = image_link

        def __str__(self):
            return f"\n{self.title}\n{self.weight}\n{self.calories}\n{self.price}\n{self.link}\n"

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

    def createExcel(self):
        try:
            dailyMenu = self.getDailyMenu(requests.get(namnyamURL).text)
            dailyMenu = {k: [f'{x.title}, {x.weight}, {x.calories}, {x.price}' for x in v] for k, v in dailyMenu.items()}

            columns = [pd.Series(foods, name=mealType) for mealType, foods in dailyMenu.items()]

            writer = pd.ExcelWriter("result.xlsx", engine='xlsxwriter')

            result = pd.concat(columns, axis=1)
            result.to_excel(writer, sheet_name='Main', index=False)

            worksheet = writer.sheets['Main']
            worksheet.set_column('A:D', 55, None)

            writer.save()

            print('.xlsx created')
        except Exception:
            logging.exception('e')

    def getDailyMenu(self, url: str):

        dailyMenu = {}
        dailyMenuSoup = BeautifulSoup(url, 'lxml')
        dailyMealTypes = dailyMenuSoup.find_all('div', class_='catering_item included_item')

        for mealType in dailyMealTypes:

            typeLabel = mealType.find('div', class_='catering_item_name catering_item_name_complex').text.strip()
            if not typeLabel:
                continue
            typeLabel+= f". {' '.join(mealType.find('div', class_='catering_item_price').text.split(' ')[1:])}"

            dailyMenu[typeLabel] = []

            foods = mealType.find('ul', class_='list_included_item').find_all('li')

            for item in foods:

                weight = '? гр.'
                calories = '? ккал'
                price = '? руб.'
                link = f"https://www.nam-nyam.ru{item.a['href']}"
                image_link = f"https://www.nam-nyam.ru{item.find('div', class_='img')['data-src']}"

                foodPage = requests.get(link).text
                foodPageSoup = BeautifulSoup(foodPage, 'lxml')

                match = foodPageSoup.find('div', class_='right_pos')

                title = match.find('h1').text.strip()

                if title == 'Страница не найдена':
                    title = item.find('span', class_='complex_tooltip').text.strip()
                    weight = ' '.join(item.find('span', class_='catering_item_weight').text.split(' ')[1:])
                    dailyMenu[typeLabel].append(self.foodItem(title, weight, calories, price, link, image_link))
                    continue

                if title.startswith('.'):
                    title = title[1:]

                item_desc = foodPageSoup.find('td', itemprop="offers")

                for line in item_desc.find_all('p'):
                    if line.text.startswith("Вес: "):
                        weight = ' '.join(line.text.split(' ')[1:])
                    elif line.text.startswith("Калорийность: "):
                        calories = f"{' '.join(line.text.split(' ')[1:])} ккал"

                price = ' '.join(item_desc.find('div', id="item_price_block").text.split(' ')[1:])

                dailyMenu[typeLabel].append(self.foodItem(title, weight, calories, price, link, image_link))

        return dailyMenu
