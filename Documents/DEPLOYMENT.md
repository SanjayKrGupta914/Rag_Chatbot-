# PDF Ink - Production Deployment Guide

## Quick Start - Local Development

### 1. Setup (Windows)

```bash
# Navigate to project
cd "Pdf Extractor"

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

Visit `http://localhost:8000` in your browser.

### 2. Setup (macOS/Linux)

```bash
cd "Pdf Extractor"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Docker Deployment

### Quick Deploy with Docker Compose

```bash
cd "Pdf Extractor"

# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f pdf-extractor

# Stop services
docker-compose down
```

The application will be available at `http://localhost:8000`

### Production-Grade setup (with Nginx)

```bash
# Create SSL certificates (self-signed for testing)
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365

# Start with Nginx
docker-compose --profile production up -d

# Access via Nginx
https://localhost
```

## Cloud Deployment

### AWS EC2

1. **Launch Instance**
   - Ubuntu 22.04 LTS
   - t3.medium or larger
   - Security group: Allow 80, 443

2. **SSH into Instance**
   ```bash
   ssh -i your-key.pem ubuntu@your-instance-ip
   ```

3. **Install Docker**
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker ubuntu
   newgrp docker
   ```

4. **Deploy Application**
   ```bash
   git clone your-repo
   cd "Pdf Extractor"
   docker-compose --profile production up -d
   ```

5. **Setup Domain**
   - Update Route53 DNS records
   - Point to Elastic IP
   - Update nginx.conf with domain

### Heroku

1. **Install Heroku CLI**
   ```bash
   curl https://cli.heroku.com/install.sh | sh
   ```

2. **Create Procfile**
   ```
   web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
   ```

3. **Deploy**
   ```bash
   heroku login
   heroku create your-app-name
   git push heroku main
   ```

### DigitalOcean App Platform

1. Create App
2. Connect GitHub repo
3. Configure environment variables
4. Deploy

## Manual Server Deployment (Linux)

### Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip nginx

# Create application user
sudo useradd -m -s /bin/bash pdfapp

# Switch to app user
sudo su - pdfapp

# Clone repository
git clone your-repo
cd "Pdf Extractor"

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Systemd Service

Create `/etc/systemd/system/pdf-extractor.service`:

```ini
[Unit]
Description=PDF Text Extractor Service
After=network.target

[Service]
Type=notify
User=pdfapp
WorkingDirectory=/home/pdfapp/Pdf\ Extractor
Environment="PATH=/home/pdfapp/Pdf Extractor/venv/bin"
ExecStart=/home/pdfapp/Pdf\ Extractor/venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000 \
    main:app

Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf-extractor
sudo systemctl start pdf-extractor
sudo systemctl status pdf-extractor
```

### Nginx Proxy

Update `/etc/nginx/sites-available/pdf-extractor`:

```nginx
upstream pdf_extractor {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 50M;

    location / {
        proxy_pass http://pdf_extractor;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias /home/pdfapp/Pdf\ Extractor/static/;
        expires 7d;
    }
}
```

Enable and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/pdf-extractor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL Setup (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

## Monitoring & Maintenance

### View Logs

```bash
# Docker
docker-compose logs -f pdf-extractor

# Systemd
sudo journalctl -u pdf-extractor -f

# Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Health Monitoring

```bash
# Check service health
curl http://localhost:8000/api/health

# Check via Nginx
curl https://your-domain.com/api/health
```

### Resource Monitoring

```bash
# Docker stats
docker stats pdf-extractor

# System resources
free -h
df -h
ps aux | grep python
```

### Backup Important Data

```bash
# Backup uploads directory
tar -czf uploads-backup-$(date +%Y%m%d).tar.gz uploads/

# Backup to remote storage
aws s3 cp uploads-backup-*.tar.gz s3://your-bucket/backups/
```

## Auto-scaling & Load Balancing

### Multiple Instances

```bash
# Scale to 3 instances
docker-compose up -d --scale pdf-extractor=3
```

### Load Balancer Configuration

Use HAProxy or AWS ALB to distribute traffic:

```nginx
upstream pdf_extractor {
    server instance1:8000 weight=1;
    server instance2:8000 weight=1;
    server instance3:8000 weight=1;
}
```

## Performance Tuning

### Gunicorn Workers

```bash
# Recommended: (2 × CPU cores) + 1
# For 4-core server: 9 workers
gunicorn -w 9 -k uvicorn.workers.UvicornWorker main:app
```

### System Limits

```bash
# Increase file descriptors
sudo sysctl -w fs.file-max=2097152
sudo sysctl -w net.core.somaxconn=65535

# Persistent changes in /etc/sysctl.conf
fs.file-max=2097152
net.core.somaxconn=65535
```

### Nginx Caching

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;

location /static/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 7d;
}
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :8000

# Kill process
kill -9 <PID>
```

### High Memory Usage

```bash
# Check memory
docker stats
free -h

# Restart service
docker-compose restart pdf-extractor
```

### PDF Extraction Fails

1. Check file is valid PDF
2. Verify file size < 50MB
3. Check page count < 10 pages
4. Review logs for specific errors

### CORS Errors

Update environment variable:
```env
CORS_ORIGINS="https://your-domain.com,https://www.your-domain.com"
```

## Cost Optimization

- Use cloud storage for uploads (S3, GCS)
- Enable CDN for static files (CloudFront, Cloudflare)
- Auto-scale based on traffic (AWS Auto Scaling)
- Use spot instances for non-critical workloads
- Monitor and optimize database queries

## Security Best Practices

1. **Always use HTTPS** in production
2. **Keep dependencies updated**
   ```bash
   pip list --outdated
   pip install --upgrade <package-name>
   ```

3. **Use strong passwords** for server access
4. **Enable firewall** rules
5. **Regular backups** of application and data
6. **Monitor logs** for suspicious activity
7. **Rate limiting** already configured in Nginx

## Disaster Recovery

### Backup Strategy

```bash
#!/bin/bash
# Daily backup script

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/backups"

# Backup uploads
tar -czf $BACKUP_DIR/uploads-$DATE.tar.gz uploads/

# Upload to S3
aws s3 cp $BACKUP_DIR/uploads-$DATE.tar.gz s3://your-bucket/backups/

# Keep only 30 days
find $BACKUP_DIR -name "uploads-*.tar.gz" -mtime +30 -delete
```

### Recovery Procedures

1. **Restore from backup**
2. **Redeploy application**
3. **Verify functionality**
4. **Monitor closely**

## Support & Maintenance

- Regular security updates
- Monitor application logs
- Track performance metrics
- Plan capacity upgrades
- Document configuration changes

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)

---

For issues or questions, refer to the main README.md file.
