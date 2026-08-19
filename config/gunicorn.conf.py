# Gunicorn configuration for AI Image Generation and Fine-tuning
# This file should be placed in the config directory

# Server socket binding
bind = "0.0.0.0:8000"

# Worker processes - recommended formula is 2-4 × number_of_cores
workers = 4
worker_class = "sync"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Timeout settings (in seconds)
timeout = 120
keepalive = 5
