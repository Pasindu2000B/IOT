#!/bin/bash

########################################
# Nginx Reverse Proxy Setup
# Makes http://142.93.220.152 show dashboard
# Dashboard runs on your PC via Cloudflare Tunnel
########################################

echo "========================================"
echo "Nginx Reverse Proxy Setup"
echo "VM IP: 142.93.220.152"
echo "========================================"
echo ""

# Install nginx
echo "[1/3] Installing Nginx..."
apt-get update -qq
apt-get install -y nginx

# Get Cloudflare Tunnel URL from user
echo ""
echo "You need your Cloudflare Tunnel URL from your PC."
echo ""
echo "On your PC, run:"
echo "  cd C:\Users\Asus\Desktop\IOT"
echo "  .\start-dashboard.ps1"
echo ""
echo "Copy the tunnel URL (e.g., https://abc-xyz-123.trycloudflare.com)"
echo ""
read -p "Enter your Cloudflare Tunnel URL: " TUNNEL_URL

# Validate URL
if [[ ! $TUNNEL_URL =~ ^https:// ]]; then
    echo "❌ Invalid URL. Must start with https://"
    exit 1
fi

# Create nginx config
echo "[2/3] Configuring Nginx..."
cat > /etc/nginx/sites-available/iot-dashboard << EOF
server {
    listen 80;
    listen [::]:80;
    server_name 142.93.220.152;

    # Increase timeouts for long-running predictions
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;

    location / {
        proxy_pass $TUNNEL_URL;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/iot-dashboard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test config
echo "[3/3] Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    # Restart nginx
    systemctl restart nginx
    systemctl enable nginx
    
    # Configure firewall
    if command -v ufw &> /dev/null; then
        ufw allow 80/tcp
        ufw allow 22/tcp  # Keep SSH open!
    fi
    
    echo ""
    echo "========================================"
    echo "✓ Nginx Reverse Proxy Setup Complete!"
    echo "========================================"
    echo ""
    echo "Public Access URL:"
    echo "  http://142.93.220.152"
    echo ""
    echo "How it works:"
    echo "  1. User visits http://142.93.220.152"
    echo "  2. Nginx on VM forwards to: $TUNNEL_URL"
    echo "  3. Cloudflare Tunnel connects to your PC"
    echo "  4. Dashboard loads from your PC"
    echo ""
    echo "Important:"
    echo "  - Keep your PC running with dashboard and tunnel"
    echo "  - Run: .\start-dashboard.ps1 on your PC"
    echo "  - If tunnel URL changes, update nginx config"
    echo ""
    echo "Test now:"
    echo "  curl http://142.93.220.152"
    echo "  Or open in browser: http://142.93.220.152"
    echo ""
    echo "Service Management:"
    echo "  Restart: systemctl restart nginx"
    echo "  Status:  systemctl status nginx"
    echo "  Logs:    tail -f /var/log/nginx/access.log"
    echo ""
else
    echo "❌ Nginx configuration test failed!"
    exit 1
fi
