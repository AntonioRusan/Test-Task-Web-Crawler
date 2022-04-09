import requests
import json
from time import sleep
import pandas as pd
import datetime as dt
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright

#переводим дату из формата '23 февраля 2022' в '2022-02-23'
def date_transform(str):
    words = str.split()
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    ind = months.index(str)
    return(ind+1)

#сбор ифнормации со страницы новости
def get_one_news(news):
    try:
        title = news.find('h1', id = "pagetitle").text
    except:
        title = ""
    try:
        str_tmp = news.find('span', class_="media-date").text.strip()
        date_comp = str_tmp.split()
        day = int(date_comp[0])
        year = int(date_comp[2])
        month = date_transform(date_comp[1])
        num_date = dt.date(year, month, day)
        str_date = str(num_date)
    except:
        str_date = ""
    try:
        article_text = news.find('div', "content-detail-wrap")
        main_text = article_text.findAll('p')
        news_text = '\n'.join([item_text.text.strip() for item_text in main_text])
    except:
        news_text = ""
    try:
        imgs_html = news.findAll('img')
        images = list()
        for img_tmp in imgs_html:
            images.append("https://eabr.org" + img_tmp.get("src"))
    except:
        images = list()
    data_row = {
        "Title": title,
        "Text": news_text,
        "Date": str_date,
        "Images": images
    }
    return data_row

with sync_playwright() as p:
    print("Введите дату начала в формате ДД.ММ.ГГГГ:")
    date_beg = input()
    print("Введите дату конца в формате ДД.ММ.ГГГГ:")
    date_end = input()
    browser = p.chromium.launch(headless=False, slow_mo=50)
    page = browser.new_page()
    page.set_default_timeout(90000)
    page.goto("https://eabr.org/press/releases/")
    #date_beg = "01.03.2022"
    #date_end = "02.04.2022"
    page.fill('#datepicker', date_beg)
    page.fill('#datepicker2', date_end)
    page.click('input.button-search') #выбираем необходимые даты, чтобы по ним отфильтровать новости
    news_arr = list()#массив итоговых данных
    links_arr = list()#массив ссылок
    flag_next_page = True
    while flag_next_page: #в цикле идём по каждой страничке со списком новостей и собираем ссылки на каждую новость
        page.wait_for_load_state()
        html = page.query_selector('div.cd-main-content').inner_html()
        data = BeautifulSoup(html, 'html.parser')
        news = data.findAll('div', class_='media-item')
        for item_news in news:
            link = "https://eabr.org" + item_news.find('div', class_ = "media-name").find('a').get("href")
            links_arr.append(link)
        sleep(5)
        try:
            ref_next = data.find('li', class_="next").find('a', class_="tab_id").get('href')
        except:
            ref_next = ""
        if ref_next: #переход на следующую
            next = "https://eabr.org" + ref_next
            page.goto(next)
        else: #дошли до конца
            flag_next_page = False
            

    
    for item_link in links_arr: #переходим по каждой ссылке и собираем информацию по каждой новости
        sleep(20)
        page.goto(item_link)
        page.wait_for_load_state()
        html = page.query_selector('div.content-wrap').inner_html()
        data = BeautifulSoup(html, 'html.parser')
        news_arr.append(get_one_news(data))

    
    with open("eabr_news.json", 'w') as json_file: #сохраняем данные в json файл
        json.dump(news_arr, json_file)
    news_DataFrame = pd.read_json("eabr_news.json")
    print(news_DataFrame)
    news_DataFrame.to_csv("eabr_news.csv", sep=';', encoding = 'utf8')#сохраняем в csv файл
    browser.close()
    