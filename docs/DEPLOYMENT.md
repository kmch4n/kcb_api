# Deployment Guide

## Apache Configuration

### 1. Copy Apache Configuration File

```bash
sudo cp /home/your-username/dev/kcb_api/apache/api.example.com.conf /etc/apache2/sites-available/
```

### 2. Enable Proxy Modules

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
```

### 3. Enable Site

```bash
sudo a2ensite api.example.com.conf
sudo systemctl reload apache2
```

### 4. Verify Configuration

```bash
sudo apache2ctl configtest
```

If no errors:

```bash
sudo systemctl restart apache2
```

## systemd Configuration (Auto-start)

### 1. Copy Service File

```bash
sudo cp /home/your-username/dev/kcb_api/systemd/kcb_api.service /etc/systemd/system/
```

### 2. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable kcb_api
sudo systemctl start kcb_api
```

### 3. Check Status

```bash
sudo systemctl status kcb_api
```

### 4. View Logs

```bash
# Real-time logs
sudo journalctl -u kcb_api -f

# Last 100 lines
sudo journalctl -u kcb_api -n 100
```

## DNS Configuration

Configure A record for `api.example.com` in Cloudflare to point to your server IP.

## Testing

### Local Test (On Server)

```bash
curl http://localhost:8000/kcb_api/health
```

### Test via Apache

```bash
curl http://api.example.com/kcb_api/health
```

### HTTPS Test (via Cloudflare)

```bash
curl https://api.example.com/kcb_api/health
```

### Bus Search Test

```bash
curl -X POST https://api.example.com/kcb_api/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "from_stop": "京都駅前",
    "to_stop": "四条河原町",
    "current_time": "09:00",
    "day_type": "weekday"
  }'
```

## Service Management Commands

```bash
# Start service
sudo systemctl start kcb_api

# Stop service
sudo systemctl stop kcb_api

# Restart service
sudo systemctl restart kcb_api

# Check service status
sudo systemctl status kcb_api

# Disable service
sudo systemctl disable kcb_api
```

## Troubleshooting

### Service Won't Start

1. Check logs:

```bash
sudo journalctl -u kcb_api -n 50
```

2. Check .env file:

```bash
cat /home/your-username/dev/kcb_api/.env
```

3. Start manually to see errors:

```bash
cd /home/your-username/dev/kcb_api
source .venv/bin/activate
python main.py
```

### Apache Errors

Check Apache logs:

```bash
sudo tail -f /var/log/apache2/api-error.log
```

### Port Already in Use

Check which process is using the port:

```bash
sudo lsof -i :8000
```

Stop the process:

```bash
sudo kill <PID>
```
