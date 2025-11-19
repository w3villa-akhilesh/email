# Admin Backend

FastAPI-based backend service for the Kivo Admin Panel.

## Prerequisites

- Python 3.8+
- PostgreSQL database

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   
   Update `config.py` with your database credentials and environment settings:
   - Database connection details
   - Kivo OAuth credentials
   - CORS allowed origins

3. **Run the Application**
   ```bash
   python main.py
   ```

   The API server will start at `http://localhost:8000` (or configured port).

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
AdminBackend/
├── routers/          # API route handlers
├── services/         # Business logic
├── database/         # Database models and connection
├── schemas.py        # Pydantic models
├── main.py          # Application entry point
└── config.py        # Configuration settings
```

## Key Features

- **Authentication**: Kivo OAuth integration
- **Companies Management**: CRUD operations for companies
- **LLM Credentials**: Manage API keys for LLM providers
- **Agent Keys**: Generate and manage agent API keys
- **Agent Mappings**: Configure agent-company-credential associations

## API Endpoints

### Main Routes
- `/companies` - Company management
- `/llm-credential` - LLM credentials management
- `/agent-keys` - Agent API keys management
- `/agents` - Agent configuration
- `/agent-mappings` - Agent mapping configuration

## Development

The application uses SQLAlchemy ORM for database operations and includes automatic table creation on startup.

## Security

All protected endpoints require a valid Kivo access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

