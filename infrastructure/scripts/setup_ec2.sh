#!/bin/bash

# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y \
    nginx \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    postgresql-client \
    git \
    curl \
    unzip

# Install Node.js version manager (nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Install Node.js LTS
nvm install --lts
nvm use --lts

# Create application directory
sudo mkdir -p /var/www/marketing-strategist-ai
sudo chown ubuntu:ubuntu /var/www/marketing-strategist-ai

# Clone the repository
cd /var/www/marketing-strategist-ai
git clone https://github.com/yourusername/marketing-strategist-ai.git .

# Setup Python environment
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup frontend
cd ../frontend
npm install
npm run build

# Configure Nginx
sudo tee /etc/nginx/sites-available/marketing-strategist-ai << EOF
server {
    listen 80;
    server_name _;

    location / {
        root /var/www/marketing-strategist-ai/frontend/.next;
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/marketing-strategist-ai /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Setup systemd service for backend
sudo tee /etc/systemd/system/marketing-strategist-ai.service << EOF
[Unit]
Description=Marketing Strategist AI Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/marketing-strategist-ai/backend
Environment="PATH=/var/www/marketing-strategist-ai/backend/venv/bin"
ExecStart=/var/www/marketing-strategist-ai/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable marketing-strategist-ai
sudo systemctl start marketing-strategist-ai

# Setup SSL with Let's Encrypt
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com --non-interactive --agree-tos --email your-email@example.com

# Setup automatic renewal for SSL
(crontab -l 2>/dev/null; echo "0 0 * * * certbot renew --quiet") | crontab -

# Setup logging
sudo mkdir -p /var/log/marketing-strategist-ai
sudo chown ubuntu:ubuntu /var/log/marketing-strategist-ai

# Setup backup
sudo mkdir -p /var/backups/marketing-strategist-ai
sudo chown ubuntu:ubuntu /var/backups/marketing-strategist-ai

# Add backup script
sudo tee /usr/local/bin/backup-marketing-strategist-ai << EOF
#!/bin/bash
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/marketing-strategist-ai"
pg_dump -h localhost -U postgres marketing_strategist > \$BACKUP_DIR/db_backup_\$TIMESTAMP.sql
tar -czf \$BACKUP_DIR/app_backup_\$TIMESTAMP.tar.gz /var/www/marketing-strategist-ai
find \$BACKUP_DIR -type f -mtime +7 -delete
EOF

sudo chmod +x /usr/local/bin/backup-marketing-strategist-ai

# Add backup to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-marketing-strategist-ai") | crontab -

# Setup monitoring
sudo apt-get install -y prometheus-node-exporter

# Setup firewall
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

echo "Setup completed successfully!" 