import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import json
import re
import os
import time
from kafka import KafkaProducer



SERVER_HOST = os.getenv('SERVER_HOST')
main_url = os.getenv('MAIN_URL')

# Kafka 프로듀서 설정
producer = KafkaProducer(bootstrap_servers=[f'{SERVER_HOST}:19094'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))  # 데이터를 JSON 문자열로 직렬화

# 전송된 기사 URL를 추적하기 위한 집합
sent_urls = set()

def fetch_html(url):
    """주어진 URL에서 HTML을 가져오는 함수"""
    response = requests.get(url)
    return response.text

def parse_article_urls(html):
    """HTML에서 기사 URL을 파싱하는 함수"""
    soup = BeautifulSoup(html, 'html.parser')
    articles = soup.select(".articleSubject a")
    article_urls = []
    
    for article in articles:
        relative_url = article.get('href')
        parsed_url = urlparse(relative_url)
        query_components = parse_qs(parsed_url.query)
        
        office_id = query_components['office_id'][0]
        article_id = query_components['article_id'][0]
        absolute_url = f"https://n.news.naver.com/mnews/article/{office_id}/{article_id}"
        article_urls.append(absolute_url)
    
    return article_urls

def clean_text(text):
    """텍스트에서 불필요한 문자를 제거하는 함수"""
    text = re.sub('\s{2,}', ' ', text)  # 두 개 이상의 공백을 하나로 줄임
    text = re.sub('\n', ' ', text)  # 줄바꿈 문자를 공백으로 대체
    text = re.sub(r'\\', '', text)  # 백슬래시 제거
    text = re.sub(r'\"', '', text)  # 따옴표 제거
    return text.strip()

def fetch_article_data(url):
    """기사 URL에서 제목, 날짜, 본문을 추출하는 함수"""
    html = fetch_html(url)
    soup = BeautifulSoup(html, 'html.parser')
    
    title = clean_text(soup.select_one("#title_area > span").text)
    date = clean_text(soup.select_one("span.media_end_head_info_datestamp_time._ARTICLE_DATE_TIME")['data-date-time'])
    content = clean_text(soup.select_one("article#dic_area").text)
    
    return {
        'title': title,
        'date': date,
        'content': content,
        'url': url
    }

def main():
    """메인 실행 함수"""
    main_url = os.getenv('MAIN_URL')
    main_html = fetch_html(main_url)
    article_urls = parse_article_urls(main_html)
    
    for url in article_urls:
        # 이미 전송된 URL은 건너뛰기
        if url in sent_urls:
            continue
        
        article_data = fetch_article_data(url)
        # Kafka 토픽에 데이터 전송
        producer.send('news_1', article_data)  
        producer.flush()  # 데이터가 전송되도록 보장
        
        # URL을 전송된 URL 집합에 추가
        sent_urls.add(url)

# if __name__ == '__main__':
#     while True:
#         main()
#         print("데이터 업데이트 완료. 60초 후 다시 실행됩니다.")
#         time.sleep(60)  # 60초 대기 후 다시 실행

