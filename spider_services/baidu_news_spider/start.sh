#!/bin/bash

uvicorn spider_services.baidu_news_spider.app.main:app --port 5002 --reload