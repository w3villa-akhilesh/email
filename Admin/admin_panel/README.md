# Kivo Admin Panel

A beautiful admin interface for managing Kivo Agent data using FastAPI, MySQL, and SQLAdmin.

## Features

✨ **Beautiful Admin UI** - Modern, responsive interface powered by SQLAdmin  
🔐 **Secure Authentication** - Session-based authentication with configurable credentials  
🗄️ **Database Management** - Full CRUD operations for all models  
📊 **Data Visualization** - Rich data tables with search, sort, and pagination  
🔍 **Advanced Search** - Search across multiple fields in each model  
🎨 **Customizable Views** - Tailored admin views for each data model  

## Prerequisites

- Python 3.8+
- MySQL Server
- Required packages (see requirements.txt)

## Quick Setup

### 1. Install Dependencies

```bash
cd /path/to/kivo_agent/Admin/admin_panel
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the admin_panel directory:

```bash
# Database Configuration
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_database_name

# Admin Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your-super-secret-key-for-sessions

# Application Settings
DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8001
```

### 3. Run the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Access Admin Panel

Open your browser and navigate to:
- **Admin Panel**: http://localhost:8001/admin
- **API Health Check**: http://localhost:8001/health

## Admin Models

The admin panel provides management interfaces for:

### 👥 Users
- **Fields**: ID, Kivo ID, First Name, Email, Timezone
- **Features**: Search by name/email, OAuth token management
- **Security**: Sensitive tokens hidden from display

### 📅 Events
- **Fields**: ID, App Name, User ID, Session ID, Author, Timestamp, Content
- **Features**: Real-time event tracking, JSON content viewer
- **Sorting**: Latest events first by default

### 🔑 LLM Credentials
- **Fields**: Company ID, App Name, Model, API Keys, Status
- **Features**: Secure key management, status toggling
- **Security**: API keys displayed as password fields

### ⚙️ Session Modes
- **Fields**: ID, Session ID, Mode
- **Features**: Session configuration management

## Configuration

### Database Settings

The application uses SQLAlchemy with MySQL connector. Ensure your MySQL server is running and accessible with the provided credentials.

### Authentication

Default admin credentials:
- **Username**: `admin` (configurable via ADMIN_USERNAME)
- **Password**: `admin123` (configurable via ADMIN_PASSWORD)

**⚠️ Important**: Change the default password in production!

### Security

- Session-based authentication
- Configurable secret key for session encryption
- API keys hidden in admin interface
- CORS protection available

## Development

### Project Structure

```
admin_panel/
├── main.py              # FastAPI application entry point
├── database.py          # Database connection and configuration
├── models.py            # SQLAlchemy models
├── admin_views.py       # SQLAdmin view configurations
├── config.py            # Application configuration
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Adding New Models

1. Define the SQLAlchemy model in `models.py`
2. Create an admin view in `admin_views.py`
3. Add the view to the `admin_views` list
4. The view will be automatically registered

### Customizing Views

Admin views can be customized by modifying the classes in `admin_views.py`:

```python
class YourModelAdmin(ModelView, model=YourModel):
    # Display configuration
    column_list = [YourModel.field1, YourModel.field2]
    column_searchable_list = [YourModel.field1]
    column_sortable_list = [YourModel.field1, YourModel.field2]
    
    # Form configuration
    form_excluded_columns = [YourModel.sensitive_field]
    
    # UI configuration
    name = "Your Model"
    icon = "fa-solid fa-your-icon"
```

## Production Deployment

### Environment Variables

Ensure all required environment variables are set:

```bash
export DB_USER="production_user"
export DB_PASSWORD="secure_password"
export DB_NAME="production_db"
export ADMIN_PASSWORD="very_secure_admin_password"
export SECRET_KEY="random-secret-key-for-production"
export DEBUG="False"
```

### Running with Gunicorn

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

## Troubleshooting

### Database Connection Issues

1. Verify MySQL server is running
2. Check database credentials in `.env`
3. Ensure database exists
4. Check firewall/network connectivity

### Import Errors

If you see import errors, ensure you're running from the admin_panel directory:

```bash
cd /path/to/kivo_agent/Admin/admin_panel
python main.py
```

### Permission Issues

Ensure the database user has appropriate permissions:

```sql
GRANT ALL PRIVILEGES ON your_database.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

## API Endpoints

- `GET /` - Application info and status
- `GET /health` - Health check with database status
- `GET /admin` - Admin panel interface (requires authentication)

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify environment configuration
3. Ensure database connectivity
4. Review the troubleshooting section above
