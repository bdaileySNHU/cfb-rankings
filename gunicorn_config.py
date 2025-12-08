"""Gunicorn configuration for production deployment"""

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 60
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout (systemd will capture it)
errorlog = "-"  # Log to stderr (systemd will capture it)
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "cfb-rankings"

# Server mechanics
daemon = False
pidfile = None  # Don't use pidfile, systemd manages the process
user = None
group = None
tmp_upload_dir = None

# SSL (if terminating SSL at Gunicorn instead of Nginx)
# keyfile = None
# certfile = None
