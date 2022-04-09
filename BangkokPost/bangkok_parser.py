import requests
import json
from time import sleep
import pandas as pd
import datetime as dt
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright

#функция преобразоаания даты публикации из "published : 31 Mar 2022 at 16:17" в "2022-03-31 16:17:00"
def date_transform(str):
    words = str.split()
    day = words[2]
    months_name = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_str = words[3]
    month = months_name.index(month_str.upper())+1
    year = words[4]
    time = words[6].split(":")
    hour = time[0]
    minute = time[1]
    return [year, month, day, hour, minute]

#сбор ифнормации со страницы новости
def get_one_news(news):
    try:
        title = news.find('div', class_ = "article-headline").text.strip()
    except:
        title = ""
    try:
        article_info = news.find('div', class_ = "article-info").findAll('p')
    except:
        article_info = ""
    try:
        str_tmp_date = article_info[0].text.strip().replace("\n", "")
        new_date = date_transform(str_tmp_date)
        num_date = dt.datetime(int(new_date[0]), int(new_date[1]), int(new_date[2]), int(new_date[3]), int(new_date[4]))
        str_date = str(num_date)
    except:
        str_date = ""
    try:
        author_html = [item for item in article_info if "writer" in item.text]
        author = author_html[0].find('a').find('span').text.strip().replace("\n", "")
    except:
        author = ""
    try:
        tags_html = news.find_all('div', class_ = "breadcrumb-item")
        tags = list()
        for tag_tmp in tags_html:
            tags.append(tag_tmp.find('a').text.strip())
    except:
        tags = list()

    article_text = news.find('div', "articl-content")
    try:
        main_text = article_text.findAll('p')
        news_text = '\n'.join([item_text.text for item_text in main_text])
    except:
        news_text = ""
    
    try:
        imgs_html = news.find('div', 'articl-content').findAll('img')
        images = list()
        for img_tmp in imgs_html:
            images.append(img_tmp.get("src"))
    except:
        images = list()
    data_row = {
        "Title": title,
        "Tags": tags,
        "Author": author,
        "Text": news_text,
        "Date": str_date,
        "Images": images
    }
    return data_row

#функция, которая собирает только данные по новости из архива
def get_news_info(news):
    try:
        title = news.find('h3').find('a').text.strip()
    except:
        title = ""
    try:
        writer_info = news.find('p', class_ = "writerdetail")
    except:
        writer_info = ""
    author = ""
    if ',' in writer_info.text:
        try:
            author = writer_info.find('a').text.strip()
        except:
            author = ""
    try:
        str_date = writer_info.find('span').find('a').text.strip()
        #print(str_date)
        num_date = dt.datetime.strptime(str_date, '%d/%m/%Y').date()
        #print(num_date)
        str_date = str(num_date)
    except:
        str_date = ""
   
    try:
        tags_html = news.find('p', class_ = "Category").find_all('a')
        tags = list()
        for tag_tmp in tags_html:
            tags.append(tag_tmp.text.strip())
    except:
        tags = list()
    try:
        all_p_selectors = news.find_all('p')
        news_text = all_p_selectors[len(all_p_selectors)-1].text.strip()
    except:
        news_text = ""
    data_row = {
        "Title": title,
        "Tags": tags,
        "Author": author,
        "Text": news_text,
        "Date": str_date,
    }
    return data_row


with sync_playwright() as p:
    print("Введите дату начала в формате ДД/ММ/ГГГГ:")
    date_beg = input()
    print("Введите дату конца в формате ДД/ММ/ГГГГ:")
    date_end = input()
    browser = p.chromium.launch(headless=False, slow_mo=50)
    page = browser.new_page()
    page.set_default_timeout(90000)
    page.goto("https://www.bangkokpost.com/archive")

    #date_beg = "08/03/2022"
    #date_end = "08/04/2022"
    page.fill('#xDateFrom', date_beg)
    page.fill('#xDateTo', date_end)
    page.click('input[title=Search]')#выбираем необходимые даты, чтобы по ним отфильтровать новости
    
    #Здесь я собирал данные только из архива, потому что не получилось собрать из страницы каждой новости, ибо сайт очень сильно замедлял работу краулера
    news_arr = list()#массив итоговых данных
    news_links = list()#массив ссылок
    flag_next_page = True
    while flag_next_page:#в цикле идём по каждой страничке со списком новостей и собираем ссылки на каждую новость
        page.wait_for_load_state()
        html = page.query_selector('#content').inner_html()
        data = BeautifulSoup(html, 'html.parser')
        news = data.findAll('div', class_ = 'detail')
        for item_news in news:
            link = item_news.find('h3').find('a').get("href")
            news_arr.append(get_news_info(item_news))
            news_links.append(link)
        sleep(10)
        try:
            ref_next = data.find('p', class_="page-Navigation").find('a', string="Next").get("href")
        except:
            ref_next = ""
        if ref_next: 
            page.goto(ref_next)
        else:
            flag_next_page = False
    #print(len(news_links))
    #Этот кусок кода необходим, если нужно пройтись по каждой странице новости
    # for item_link in news_links: #переходим по каждой ссылке и собираем информацию по каждой новости
    #     sleep(3)
    #     page.goto(item_link)
    #     try:
    #         html = page.query_selector('div.article-news').inner_html()
    #         data = BeautifulSoup(html, 'html.parser')
    #         news_arr.append(get_one_news(data))
    #     except:
    #         print(item_link)
    print(len(news_arr))
    
    with open("bangkokpost_news.json", 'w') as json_file:
        json.dump(news_arr, json_file)
    news_DataFrame = pd.read_json("bangkokpost_news.json")
    print(news_DataFrame)
    news_DataFrame.to_csv("bangkokpost_news.csv", sep = ';', encoding = 'utf8')
    browser.close()