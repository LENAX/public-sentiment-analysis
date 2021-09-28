#!/bin/bash

python3 -m uvicorn app.server:app --reload --port 8006
