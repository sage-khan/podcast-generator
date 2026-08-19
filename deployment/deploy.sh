#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration (should be in .env)
if [ -z "$DO_DROPLET_IP" ]; then
    echo -e "${RED}DO_DROPLET_IP is not set. Add it to your .env or export it before running this script.${NC}"
    exit 1
fi
DOMAIN=${DOMAIN:-$DO_DROPLET_IP}
GITHUB_REPO=${GITHUB_REPO:-"your-org/podcast-generator"}
GITHUB_BRANCH=${GITHUB_BRANCH:-"main"}

# SSH key path
SSH_KEY=${SSH_KEY:-"~/.ssh/id_rsa"}

# Check if DOMAIN is an IP address
IS_IP=0
if [[ $DOMAIN =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    IS_IP=1
    echo -e "${GREEN}Using IP address $DOMAIN with HTTP configuration${NC}"
else
    echo -e "${GREEN}Using domain name $DOMAIN - will set up HTTPS${NC}"
fi

echo -e "${GREEN}Starting deployment to $DO_DROPLET_IP...${NC}"

# Check if SSH key exists
if [ ! -f $(eval echo $SSH_KEY) ]; then
    echo -e "${RED}SSH key not found at $SSH_KEY${NC}"
    echo "Please generate an SSH key pair or specify the correct path."
    exit 1
fi

# First, ensure /var/www directory exists on the server
echo -e "${GREEN}Ensuring base directory exists...${NC}"
ssh -i $(eval echo $SSH_KEY) root@$DO_DROPLET_IP "mkdir -p /var/www"

# Connect to the server and setup the environment (only if needed)
echo -e "${GREEN}Checking server environment...${NC}"
ssh -i $(eval echo $SSH_KEY) root@$DO_DROPLET_IP << EOF
    # Create a flag file to track first-time setup
    if [ ! -f "/var/www/.env_setup_complete" ]; then
        echo "First-time setup: Installing dependencies..."
        
        # Update package lists
        apt-get update
        
        # Install Docker if not already installed
        if ! command -v docker &> /dev/null; then
            echo "Installing Docker..."
            apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io
        fi
        
        # Install Docker Compose if not already installed
        if ! command -v docker compose &> /dev/null; then
            echo "Installing Docker Compose..."
            # Install the new Docker Compose as a plugin
            mkdir -p ~/.docker/cli-plugins/
            curl -SL https://github.com/docker/compose/releases/download/v2.16.0/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
            chmod +x ~/.docker/cli-plugins/docker-compose
            
            # Verify installation
            docker compose version
        fi
        
        # Install Git if not already installed
        if ! command -v git &> /dev/null; then
            echo "Installing Git..."
            apt-get install -y git
        fi
        
        # Mark setup as complete
        touch /var/www/.env_setup_complete
    else
        echo "Dependencies already installed, skipping..."
    fi

    # Create app directory if it doesn't exist (always check)
    if [ ! -d "/var/www/podcast-generator" ]; then
        mkdir -p /var/www/podcast-generator
    fi
EOF

# Clone or update the repository on the server
echo -e "${GREEN}Updating the repository...${NC}"
ssh -i $(eval echo $SSH_KEY) root@$DO_DROPLET_IP << EOF
    cd /var/www/podcast-generator
    
    # Check if the repository has been cloned before
    if [ -d ".git" ]; then
        # Repository exists, update it
        echo "Repository exists, updating..."
        git fetch origin
        git reset --hard origin/${GITHUB_BRANCH}
    else
        # Repository doesn't exist, clone it
        echo "Repository doesn't exist, cloning..."
        git clone --branch ${GITHUB_BRANCH} https://github.com/${GITHUB_REPO}.git .
    fi
EOF

# Copy .env file to the server
echo -e "${GREEN}Copying .env file to the server...${NC}"
scp -i $(eval echo $SSH_KEY) .env root@$DO_DROPLET_IP:/var/www/podcast-generator/

# Ensure Nginx and Certbot directories exist (only create if missing)
echo -e "${GREEN}Checking Nginx and Certbot directories...${NC}"
ssh -i $(eval echo $SSH_KEY) root@$DO_DROPLET_IP << EOF
    cd /var/www/podcast-generator
    
    # Only create directories if they don't exist
    mkdir -p certbot/conf certbot/www nginx
    mkdir -p nginx/acme_challenge
    
    # Only create Nginx configuration if it doesn't exist or if we need to force IP-based config
    if [ ! -f "nginx/app.conf" ] || [ "$IS_IP" == "1" ]; then
        echo "Creating initial Nginx configuration..."
        echo "server {
        listen 80;
        server_name $DOMAIN;
        server_tokens off;

        location /.well-known/acme-challenge/ {
            root /var/www/podcast-generator/certbot/www;
        }

        location / {
            proxy_pass http://web:8000;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }" > nginx/app.conf
    fi
EOF

# Start the application with Docker Compose
echo -e "${GREEN}Deploying the application...${NC}"
ssh -i $(eval echo $SSH_KEY) root@$DO_DROPLET_IP << EOF
    cd /var/www/podcast-generator

    # Create a first-time deployment flag
    FIRST_DEPLOYMENT=0
    if [ ! -f ".deployed" ]; then
        FIRST_DEPLOYMENT=1
        touch .deployed
    fi

    # Check if .env file exists and update settings if needed
    if grep -q "DJANGO_SETTINGS_MODULE=" .env; then
        # Replace only if it's not already set correctly
        if ! grep -q "DJANGO_SETTINGS_MODULE=config.settings" .env; then
            sed -i 's/DJANGO_SETTINGS_MODULE=.*/DJANGO_SETTINGS_MODULE=config.settings/' .env
        fi
    else
        # Add the setting if it doesn't exist
        echo "DJANGO_SETTINGS_MODULE=config.settings" >> .env
    fi
    
    # First time deployment needs a full build
    if [ $FIRST_DEPLOYMENT -eq 1 ]; then
        echo "First-time deployment: Building all containers..."
        docker compose up -d --build
        sleep 10  # Give containers time to start on first deploy
    else
        # Apply database migrations before restarting containers (this prevents downtime)
        echo "Applying database migrations..."
        # Try to pull the image if it exists (or it will be built locally)
        docker pull "${DOCKER_IMAGE:-podcast-generator}:latest" 2>/dev/null || echo "Will build image locally"
        
        # Run migrations
        docker compose run --rm web python manage.py migrate
        
        # Restart the containers with minimal downtime
        echo "Restarting containers..."
        docker compose up -d --no-deps
    fi
EOF

# After deployment, set up SSL if using a domain name
if [ $IS_IP -eq 0 ]; then
    echo -e "${GREEN}Setting up SSL for domain $DOMAIN...${NC}"
    ssh -i $(eval echo $SSH_KEY) root@$DO_DROPLET_IP << EOF
        cd /var/www/podcast-generator
        
        # Check if fix-ssl.sh exists
        if [ -f "fix-ssl.sh" ]; then
            echo "Running SSL fix script..."
            ./fix-ssl.sh $DOMAIN
        else
            # Initial SSL setup
            echo "Running initial SSL setup..."
            ./deployment/init-ssl.sh $DOMAIN
        fi
EOF
    echo -e "${GREEN}SSL setup completed! The application is now running at https://$DOMAIN${NC}"
else
    echo -e "${GREEN}Deployment complete! The application is now running at http://$DO_DROPLET_IP${NC}"
echo -e "SSL can be with Certbot using:"
echo -e "${GREEN}ssh -i $(eval echo $SSH_KEY) root@$DO_DROPLET_IP${NC}"
echo -e "${GREEN}cd /var/www/podcast-generator${NC}"
echo -e "${GREEN}docker compose run --rm certbot certonly --webroot -w /var/www/certbot/www -d $DOMAIN${NC}"
echo -e "Then use shared/misc/app-nginx.conf to update nginx/app.conf to use SSL if needed and restart the containers."

# Usually simple app.conf is built so the original is saved as app-nginx.conf which is then copied back
# Comment line below if not using HTTPS and domain name not available
#rm nginx/app.conf
#cp nginx/app-nginx.conf shared/misc/app-nginx.conf
#docker compose down
#docker compose up -d --build
fi
exit 0