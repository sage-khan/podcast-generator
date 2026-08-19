#!/bin/bash
set -e

# Check if domain is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <domain>"
    exit 1
fi

DOMAIN=$1

# Create a temporary nginx conf for certbot challenge
cat > ./nginx/app.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;
    server_tokens off;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Reload the environment to apply changes
docker-compose down
COMPOSE_BAKE=true docker-compose up -d --build

# Wait for nginx to start
echo "Waiting for Nginx to start..."
sleep 5

# Run certbot
echo "Requesting Let's Encrypt certificate for $DOMAIN..."
docker-compose run -d --rm certbot certonly --webroot -w /var/www/certbot \
    --email admin@$DOMAIN --agree-tos --no-eff-email \
    -d $DOMAIN

# Wait for certbot to finish (check if certificates exist)
echo "Waiting for certificates to be generated..."
CERT_PATH="/var/www/podcast-generator/certbot/conf/live/$DOMAIN/fullchain.pem"
ATTEMPTS=0
MAX_ATTEMPTS=30

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if docker-compose exec -T nginx test -f $CERT_PATH; then
        echo "Certificate found!"
        break
    fi
    echo "Waiting for certificates... ($((ATTEMPTS+1))/$MAX_ATTEMPTS)"
    sleep 10
    ATTEMPTS=$((ATTEMPTS+1))
done

if [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    echo "Certificate generation timed out. Check logs with: docker-compose logs certbot"
    exit 1
fi

# Create the final nginx conf with SSL configuration
# This is the fixed HTTPS configuration that should be preserved
fix_ssl_config() {
    local domain=$1
    
    echo "Applying SSL configuration fix for $domain..."
    cat > ./nginx/app.conf << EOF
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
EOF

    # Reload nginx to apply the new configuration
    if command -v docker-compose &> /dev/null; then
        docker-compose exec -T nginx nginx -s reload
    else
        docker compose exec -T nginx nginx -s reload
    fi
    
    echo "SSL configuration fixed and applied successfully!"
}

# Apply SSL config the first time
fix_ssl_config $DOMAIN

# Check if this script is being run for initial SSL setup or as a fix
if [ "$2" == "fix" ]; then
    echo "SSL fix script completed"
    exit 0
fi

echo "SSL certificate obtained successfully!"
echo "Your site is now available at https://$DOMAIN"

# Create a fix script that can be run after deployment
cat > ./fix-ssl.sh << 'EOT'
#!/bin/bash
set -e

DOMAIN=${1:-"example.com"}
echo "Fixing SSL configuration for $DOMAIN..."

# Call the init-ssl script with the fix parameter
./init-ssl.sh $DOMAIN fix
EOT

chmod +x ./fix-ssl.sh
echo "Created fix-ssl.sh script for post-deployment fixes"

# Usually simple app.conf is built so the original is saved as app-nginx.conf which is then copied back
# Comment lines below if not using HTTPS and domain name not available
rm nginx/app.conf
cp nginx/app-nginx.conf nginx/app.conf 
docker compose down
docker compose up -d --build
