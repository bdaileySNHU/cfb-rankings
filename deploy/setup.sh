#!/bin/bash
# Initial setup script for VPS deployment
# Run this ONCE on your VPS to set everything up

set -e  # Exit on error

echo "=========================================="
echo "College Football Rankings - Initial Setup"
echo "=========================================="
echo ""

# Configuration - CHANGE THESE
DOMAIN="cfb.yourdomain.com"  # Change to your subdomain
APP_DIR="/var/www/cfb-rankings"
REPO_URL="https://github.com/yourusername/cfb-rankings.git"  # Change if using git

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "This script will set up College Football Rankings on:"
echo "  Domain: $DOMAIN"
echo "  Directory: $APP_DIR"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "📦 Installing dependencies..."
apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Create app directory
echo "📁 Creating application directory..."
mkdir -p $APP_DIR
cd $APP_DIR

# Clone repository OR copy files manually
echo "📁 Getting application files..."
if [ -d ".git" ]; then
    echo "Git repository already exists, pulling latest..."
    git pull
else
    echo "MANUAL STEP REQUIRED:"
    echo "Please copy your application files to $APP_DIR"
    echo "Or initialize git repository and clone from remote"
    read -p "Press enter when files are in place..."
fi

# Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements-prod.txt

# Create log directories
echo "📝 Creating log directories..."
mkdir -p /var/log/cfb-rankings
chown -R www-data:www-data /var/log/cfb-rankings

# Set up environment file
echo "⚙️  Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env file and add your CFBD_API_KEY"
    read -p "Press enter to edit .env file..."
    nano .env
fi

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "from database import init_db; init_db()"

# Import initial data (optional)
read -p "Do you want to import real data now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 import_real_data.py
fi

# Set permissions
echo "🔐 Setting permissions..."
chown -R www-data:www-data $APP_DIR

# Install systemd service
echo "⚙️  Installing systemd service..."
cp deploy/cfb-rankings.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable cfb-rankings
systemctl start cfb-rankings

# Install Nginx configuration
echo "🌐 Installing Nginx configuration..."
# Update domain in config
sed "s/cfb.yourdomain.com/$DOMAIN/g" deploy/nginx.conf > /etc/nginx/sites-available/cfb-rankings
ln -sf /etc/nginx/sites-available/cfb-rankings /etc/nginx/sites-enabled/

# Test Nginx config
nginx -t

# Get SSL certificate
echo "🔒 Setting up SSL certificate..."
certbot --nginx -d $DOMAIN

# Reload Nginx
systemctl reload nginx

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Your site should now be accessible at:"
echo "  https://$DOMAIN"
echo ""
echo "Useful commands:"
echo "  - Check service status: systemctl status cfb-rankings"
echo "  - View logs: journalctl -u cfb-rankings -f"
echo "  - Restart service: systemctl restart cfb-rankings"
echo "  - Deploy updates: cd $APP_DIR && sudo ./deploy/deploy.sh"
echo ""
echo "Next steps:"
echo "  1. Visit https://$DOMAIN to test"
echo "  2. Set up a cron job to update rankings weekly"
echo "  3. Configure automatic backups of the database"
echo ""
