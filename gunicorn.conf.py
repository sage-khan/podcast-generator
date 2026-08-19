# Proposed content for gunicorn.conf.py
import os
import multiprocessing

bind = "0.0.0.0:8000"
workers = 5 # multiprocessing.cpu_count() * 2 + 1
threads = 4 #multiprocessing.cpu_count() * 2 # Relevant for gthread worker
worker_class = "gthread" # Good for I/O bound tasks
timeout = 300 # 5 minutes
max_requests = 1000
max_requests_jitter = 50
preload_app = False
loglevel = "debug" #or use info for less log volume
accesslog = "-" # Log to stdout
errorlog = "-"  # Log to stderr