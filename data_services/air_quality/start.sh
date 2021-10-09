#!/bin/bash

python3 -m uvicorn data_services.air_quality.app.server:app --port 8080