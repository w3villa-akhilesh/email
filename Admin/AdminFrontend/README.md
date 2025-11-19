# Admin Frontend

React-based frontend application for the Kivo Admin Panel built with CoreUI and Vite.

## Prerequisites

- Node.js 16+ and npm

## Setup

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Configure Environment**
   
   Create a `.env` file in the root directory:
   ```env
   VITE_BACKEND_URL=http://localhost:8000
   ```

3. **Run Development Server**
   ```bash
   npm run dev
   ```

   The application will start at `http://localhost:5173`.

4. **Build for Production**
   ```bash
   npm run build
   ```

## Project Structure

```
AdminFrontend/
├── src/
│   ├── views/           # Page components
│   ├── components/      # Reusable components
│   ├── Api/            # API client functions
│   ├── Constants/      # API endpoints configuration
│   ├── hooks/          # Custom React hooks
│   └── utils/          # Helper functions
├── public/             # Static assets
└── vite.config.mjs    # Vite configuration
```

## Key Features

- **Dashboard**: Session analytics and worklog visualization
- **Companies Management**: Create, edit, and manage companies
- **LLM Credentials**: Configure LLM provider credentials per company
- **Agent Configuration**: Set up agents and their mappings
- **Agent Keys**: Generate and manage agent API keys
- **Authentication**: Kivo OAuth login

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint

## Main Pages

- `/dashboard` - Dashboard with analytics
- `/companies` - Companies listing and management
- `/companies/:id` - Company details with credentials and agent mappings
- `/authenticate-agent` - Agent API keys management
- `/worklog` - Session logs and analytics

## Authentication

The application uses Kivo OAuth for authentication. Users must have admin access to log in.

## Styling

- Built with CoreUI React components
- Custom SCSS for additional styling
- Font Awesome icons for UI elements

## API Integration

API calls are handled through centralized functions in `src/Api/Auth.js` using the endpoints defined in `src/Constants/endpoints.js`.
