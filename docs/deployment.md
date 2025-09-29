# SimpleCMS - Production Deployment Guide

This guide covers the complete process of building and deploying SimpleCMS in a production environment.

## Production Build

### Backend Build
1. **Install production dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   pip install gunicorn  # For production WSGI server
   ```

2. **Collect static files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Run database migrations**:
   ```bash
   python manage.py migrate
   ```

### Frontend Build
1. **Build web application**:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. **Build Electron application** (optional):
   ```bash
   cd electron
   npm install
   npm run build:linux  # or build:win, build:mac
   ```

## Production Deployment

### System Requirements
- Ubuntu 20.04+ or CentOS 7+
- Python 3.8+
- Node.js 20.19.0+
- Nginx
- Systemd

### Installation Steps

1. **Create application directory**:
   ```bash
   sudo mkdir -p /opt/SimpleCms
   sudo chown $USER:nginx /opt/SimpleCms
   ```

2. **Deploy application files**:
   ```bash
   # Copy your application to /opt/SimpleCms/
   cp -r backend/ /opt/SimpleCms/
   cp -r frontend/dist/ /opt/SimpleCms/frontend/
   ```

3. **Set up Python virtual environment**:
   ```bash
   cd /opt/SimpleCms/backend
   python3 -m venv /opt/venv
   source /opt/venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn
   ```

4. **Configure Django settings**:
   ```bash
   # Update settings.py for production
   DEBUG = False
   ALLOWED_HOSTS = ['your-domain.com', '192.168.1.100']
   STATIC_ROOT = '/opt/SimpleCms/backend/static/'
   ```

5. **Collect static files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

### Systemd Service Setup

1. **Copy service file**:
   ```bash
   sudo cp deployment/simplecms.service.sample /etc/systemd/system/simplecms.service
   ```

2. **Edit service file** (update paths as needed):
   ```bash
   sudo nano /etc/systemd/system/simplecms.service
   ```

3. **Enable and start service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable simplecms
   sudo systemctl start simplecms
   sudo systemctl status simplecms
   ```

### Nginx Configuration

1. **Copy nginx configuration**:
   ```bash
   sudo cp deployment/nginx_simplecms.conf.sample /etc/nginx/sites-available/simplecms
   ```

2. **Edit configuration** (update server_name and paths):
   ```bash
   sudo nano /etc/nginx/sites-available/simplecms
   ```

3. **Enable site and restart nginx**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/simplecms /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Service Management

**Start/Stop/Restart SimpleCMS**:
```bash
sudo systemctl start simplecms
sudo systemctl stop simplecms
sudo systemctl restart simplecms
```

**View logs**:
```bash
sudo journalctl -u simplecms -f
```

**Check service status**:
```bash
sudo systemctl status simplecms
```

### Access Points

- **Backend API**: `http://your-domain.com:8001`
- **Frontend Web App**: `http://your-domain.com:8002`
- **Admin Interface**: `http://your-domain.com:8001/admin/`

### Security Considerations

1. **Firewall configuration**:
   ```bash
   sudo ufw allow 8001
   sudo ufw allow 8002
   ```

2. **SSL/TLS setup** (recommended):
   - Use Let's Encrypt for free SSL certificates
   - Update nginx configuration to redirect HTTP to HTTPS

3. **File permissions**:
   ```bash
   sudo chown -R root:nginx /opt/SimpleCms/
   sudo chmod -R 755 /opt/SimpleCms/
   sudo chmod 660 /opt/SimpleCms/backend/db.sqlite3  # if using SQLite
   ```

### Monitoring and Maintenance

**Log rotation** (add to `/etc/logrotate.d/simplecms`):
```
/var/log/simplecms/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 root root
}
```

**Backup database**:
```bash
# For SQLite
cp /opt/SimpleCms/backend/db.sqlite3 /backup/db-$(date +%Y%m%d).sqlite3

# For PostgreSQL/MySQL - use appropriate dump commands
```

## Troubleshooting

### Common Issues

1. **Service fails to start**:
   - Check logs: `sudo journalctl -u simplecms -f`
   - Verify file permissions and paths
   - Ensure virtual environment is activated

2. **Nginx 502 Bad Gateway**:
   - Check if gunicorn is running: `sudo systemctl status simplecms`
   - Verify socket file exists: `ls -la /run/simplecms.sock`
   - Check nginx error logs: `sudo tail -f /var/log/nginx/error.log`

3. **Static files not loading**:
   - Run `python manage.py collectstatic --noinput`
   - Check nginx configuration for static file serving
   - Verify STATIC_ROOT setting in Django

4. **Database connection issues**:
   - Check database file permissions
   - Verify database configuration in settings.py
   - Run migrations: `python manage.py migrate`

### Performance Optimization

1. **Gunicorn workers**:
   - Adjust worker count in service file based on CPU cores
   - Monitor memory usage and adjust accordingly

2. **Nginx caching**:
   - Add caching headers for static files
   - Consider using nginx caching for API responses

3. **Database optimization**:
   - Regular database maintenance
   - Consider using PostgreSQL for better performance
   - Monitor database query performance
