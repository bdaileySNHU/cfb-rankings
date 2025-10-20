#!/bin/bash
# Fix permissions for EPIC-004 deployment

echo "Fixing file permissions..."

# Fix ownership of all files
sudo chown -R www-data:www-data /var/www/cfb-rankings

# Fix database permissions
sudo chmod 664 /var/www/cfb-rankings/cfb_rankings.db

# Fix any backup files
sudo chown www-data:www-data /var/www/cfb-rankings/*.backup* 2>/dev/null || true

# Fix .env file
sudo chown www-data:www-data /var/www/cfb-rankings/.env
sudo chmod 640 /var/www/cfb-rankings/.env

echo "✓ Permissions fixed"
