#!/bin/bash
set -e

# Domain to use
DOMAIN="example.com"

# Restart with plain HTTP first
echo "Restarting services with HTTP configuration..."
docker-compose down
COMPOSE_BAKE=true docker-compose up -d --build

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Stop Nginx to free port 80 for certbot
echo "Stopping Nginx to free port 80..."
docker-compose stop nginx

# Use certbot in standalone mode
echo "Requesting Let's Encrypt certificate..."
certbot certonly --standalone -d $DOMAIN --force-renewal

# Prepare directories
echo "Setting up certificate directories..."
mkdir -p /var/www/podcast-generator/certbot/conf/live/$DOMAIN/
cp -L /etc/letsencrypt/live/$DOMAIN/* /var/www/podcast-generator/certbot/conf/live/$DOMAIN/

#enable firewall
echo "Enabling firewall..."
ufw enable

# Create HTTPS Nginx configuration
echo "Creating HTTPS Nginx configuration..."
cat > ./nginx/app.conf << EOT
# HTTP server - redirects to HTTPS
server {
    listen 80;
    server_name example.com;
    server_tokens off;

    location /.well-known/acme-challenge/ {
        root /var/www/podcast-generator/certbot/www;
    }

    # Redirect all HTTP requests to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl;
    server_name example.com;
    server_tokens off;

    # SSL certificate paths
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    # Recommended SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Root location
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # Timeout settings
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Static files
    location /static/ {
        alias /var/www/podcast-generator/static/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    # Media files
    location /media/ {
        alias /var/www/podcast-generator/media/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }
}
EOT

# Restart services with HTTPS configuration
echo "Restarting services with HTTPS configuration..."
COMPOSE_BAKE=truedocker-compose up -d --build

echo "HTTPS setup completed!"
echo "Test with: curl -I https://$DOMAIN/"
EOF

# Make the script executable
chmod +x fix-ssl.sh

# Run it
./fix-ssl.sh

#3. Update Your Docker Compose Configuration
#If not already done, make sure your docker-compose.yml contains the proper volumes for SSL:

yaml
CopyInsert
nginx:
  image: nginx:1.21-alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/app.conf:/etc/nginx/conf.d/default.conf
    - ./certbot/conf:/etc/nginx/ssl
    - ./certbot/data:/var/www/certbot
