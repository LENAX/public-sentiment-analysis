#!/bin/bash

python3 -m uvicorn data_services.news.app.server:app --port 8082