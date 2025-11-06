# Student Achievement Management Panel ZCS-RP-010

A web application for managing and tracking student achievements in competitions and olympiads.

> 🇷🇺 **Русская версия документации**: [README.ru.md](README.ru.md)

## Features

- 📊 **Student Card Management** - Create, edit, and manage student profiles
- 🏆 **Detailed Achievement Tracking** - Record achievements with:
  - Competition/Olympiad name
  - Level (School/District/Regional/National/International)
  - Result (Participant/Prize Winner/Winner)
  - Academic year (format: 25/26, 26/27, etc.)
  - Participation date
- 📈 **Excel Export** - Export data in multiple formats:
  - Export all students
  - Export by class (dropdown selection)
  - All achievements exported with full details
- 🔍 **Search & Filter** - Search by name, filter by class
- 👥 **Public View** - Public-facing page to view student achievements
- 🔐 **Admin Panel** - Secure admin interface for management
- 🚀 **Production Ready** - Systemd service support for 24/7 operation

## Requirements

- Python 3.8 or higher
- pip (Python package manager)
- Ubuntu Server 18.04+ / Debian 10+ (for automated installation)

## Installation

### Ubuntu Server / Debian

1. Clone or download the project to your server
2. Navigate to the project directory
3. Run the installer:

```bash
chmod +x install.sh
sudo ./install.sh
```

The installer will:
- Check and install system dependencies
- Create a virtual environment
- Install Python packages
- Prompt for admin password and configuration
- Initialize the database
- Optionally set up systemd service for auto-start

**During installation, you will be asked:**
- Admin username (default: `admin`)
- Admin password (with confirmation)
- Server port (default: `5000`)
- Server host (default: `0.0.0.0`)
- Whether to set up systemd service for auto-start

### Manual Installation

If the installer doesn't work, install manually:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 -c "from database import init_db; init_db()"

# Create .env file (copy from .env.example and fill in values)
```

## Configuration

Configuration is stored in `.env` file (created automatically during installation):

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
FLASK_SECRET_KEY=your_secret_key
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False
```

## Running the Application

### Using the Run Script

```bash
./run.sh
```

### Manual Start

```bash
source .venv/bin/activate
python3 app.py
```

### Using Systemd Service (Production)

If systemd service was set up during installation:

```bash
# Start service
sudo systemctl start zcs-rp-010

# Stop service
sudo systemctl stop zcs-rp-010

# Check status
sudo systemctl status zcs-rp-010

# View logs
sudo journalctl -u zcs-rp-010 -f

# Enable auto-start on boot
sudo systemctl enable zcs-rp-010
```

The application will be available at: **http://your-server-ip:5000**

## Access

### Admin Panel

- **URL**: http://your-server-ip:5000/admin/login
- **Username**: Set during installation (default: `admin`)
- **Password**: Set during installation

> ⚠️ **Important**: Change the default admin password in production!

### Public View

- **URL**: http://your-server-ip:5000

## Usage

### Creating a Student Card

1. Log in to the admin panel
2. Click "Новая карточка" (New Card)
3. Fill in required fields:
   - Full Name
   - Class
   - Class Teacher
4. Add achievements:
   - Click "Добавить достижение" (Add Achievement)
   - Fill in: Competition name, Level, Result, Academic year, Date
   - Add multiple achievements as needed
5. Click "Сохранить" (Save)

### Exporting Data

In the admin panel, you can export data in three ways:

1. **Export All** - Exports all students to Excel
2. **Export by Class** - Select a class from dropdown to export
3. Each achievement is exported as a separate row with full details

Exported Excel files include:
- Student ID, Full Name, Class, Class Teacher
- Achievement Name, Level, Result, Year, Date
- Creation date

## Project Structure

```
project/
├── app.py                 # Main Flask application
├── database.py            # Database models and functions
├── config.py              # Configuration module
├── requirements.txt       # Python dependencies
├── install.sh             # Installation script (Ubuntu/Debian)
├── run.sh                 # Run script
├── .env                   # Environment variables (created during install)
├── app.db                 # SQLite database (created automatically)
├── templates/             # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── admin_dashboard.html
│   ├── admin_student_form.html
│   └── admin_login.html
└── static/                # Static files (CSS)
    └── style.css
```

## Production Deployment

For production deployment, it's recommended to:

1. **Use systemd service** (already included in installer)
2. **Set up Nginx as reverse proxy**:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
3. **Set up SSL certificate** (Let's Encrypt):
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```
4. **Configure firewall**:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

## Development

### Running in Debug Mode

Edit `.env` file:
```env
FLASK_DEBUG=True
```

Or set environment variable:
```bash
export FLASK_DEBUG=True
python3 app.py
```

## Troubleshooting

### Service won't start

Check logs:
```bash
sudo journalctl -u zcs-rp-010 -n 50
```

### Database errors

Reinitialize database:
```bash
python3 -c "from database import init_db; init_db()"
```

### Permission errors

Ensure correct permissions:
```bash
chmod +x install.sh run.sh
chmod 600 .env
```

## License

This work is licensed under a [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg

## Support

For issues and questions, please check the project documentation or contact the maintainer.

---

**ZCS-RP-010** - Student Achievement Management Panel
