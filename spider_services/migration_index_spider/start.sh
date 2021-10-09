#!/bin/bash

python3 -m uvicorn spider_services.migration_index_spider.app.main:app --port 5006
