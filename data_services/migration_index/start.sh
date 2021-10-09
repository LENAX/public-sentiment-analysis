#!/bin/bash

python3 -m uvicorn data_services.migration_index.app.server:app --port 8084