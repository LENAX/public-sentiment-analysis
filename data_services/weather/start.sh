#!/bin/bash

python3 -m uvicorn data_services.weather.app.server:app --port 8083