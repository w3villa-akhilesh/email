# Kivo Agent

An intelligent agent that filters and summarizes data using a custom toolchain.  
It uses FastAPI and an MCP Server (SSE) to interact with live APIs and run AI-driven analysis every hour.

**Port Required:** 8080

## Features

- Tool-powered reasoning with ADK's agents framework
- SSE-based MCPServer for streaming communication
- FastAPI for API interaction
- Exception-handling using Email Notifications
- Periodic execution using cron

## Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone https://github.com/w3villa/kivo_agent.git
   cd kivo_agent
   ```

2. **Install uv (Recommended)**

   uv is a fast package manager and virtual environment tool.

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Create and Activate Virtual Environment**

   ```bash
   uv venv
   .venv\Scripts\activate  # Windows
   # OR
   source .venv/bin/activate  # macOS/Linux
   ```

4. **Install Dependencies**

   ```bash
   uv add -r requirements.txt
   ```

   If you're not using uv, use:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables**

   Create a `.env` file in the root directory with the following content:

   ```env
   LLM_API_KEY=""
   LLM_API_BASE=""
   KIVO_AGENT_MODEL=""
   EXCEPTION_NOTIFIER_API_KEY=""
   EXCEPTION_NOTIFIER_SENDER=""
   EXCEPTION_NOTIFIER_RECIPIENT=""
   KIVO_API_BASE_URL=""
   KIVO_AUTH_TOKEN=""  
   DATA_BATCH_SIZE=""
   DB_HOST=""
   DB_NAME=""
   DB_USER=""
   DB_PASSWORD=""
   DB_HOST=localhost
   REDIS_HOST=localhost
   REDIS_PORT=""  // 6379
   REDIS_DB=""    // 0
   LINK_GENERATING_AGENT_KEY=""
   TRIAGE_AGENT_MODEL=""
   KIVO_HRMS_AGENT_MODEL=""
   LINK_GENERATING_AGENT_MODEL=""
   PMS_AGENT_MODEL=""
   PMS_AGENT_KEY=""
   AWS_ACCESS_KEY_ID=""              # Your AWS Access Key ID
   AWS_SECRET_ACCESS_KEY=""          # Your AWS Secret Access Key  
   AWS_REGION="us-west-2"           # AWS region where your S3 bucket is located
   AWS_S3_BUCKET_NAME="simmpli-staging"  # Name of your S3 bucket for storing images
   KNOWLEDGE_BASE_API_KEY=""
   ELASTIC_HOST =""
   ELASTIC_USERNAME =""
   ELASTIC_PASSWORD =""
  
   ```

6. **Database Migration (Required)**

   Before running the application, you need to add the missing `app_name` column to the `iats_user_sessions` table. This fixes the error: "Unknown column 'iats_user_sessions.app_name' in 'field list'".

   **Option 1: Run the Python migration script (Recommended)**
   ```bash
   cd database_migrations
   python migrate_app_name_column.py
   ```

   **Option 2: Run SQL manually**
   ```sql
   ALTER TABLE iats_user_sessions ADD COLUMN app_name VARCHAR(255) NULL;
   CREATE INDEX idx_iats_user_sessions_app_name ON iats_user_sessions(app_name);
   ```

8. **Setup LocalStack for Local S3 (Optional)**

   If you want to use a local S3 service for development instead of AWS, you can use LocalStack:

   ```bash
   docker run -d \
     --name localstack \
     -p 4566:4566 \
     -e SERVICES=s3 \
     -e DEFAULT_REGION=us-west-2 \
     -v /Users/priyank/localstack:/var/lib/localstack \
     -v /var/run/docker.sock:/var/run/docker.sock \
     localstack/localstack:latest
   ```

   **Note:** Update your `.env` file with LocalStack configuration:
   ```env
   AWS_ENDPOINT_URL="http://localhost:4566"
   AWS_ACCESS_KEY_ID="test"
   AWS_SECRET_ACCESS_KEY="test"
   AWS_REGION="us-west-2"
   ```

9. **Run FastAPI Server**

   ```bash
   python main.py
   ```

   Then, test the endpoint:

   ```
   POST http://127.0.0.1:8080/invoke-pmboard-agent
   ```

10. Ensuring **'credentials'** folder existance in case of unauth error from mcp tools.

## Project Structure

```
## Project Structure

- app/
  - core/
    - constants.py
    - helpers/
      - pm_board_agent.py
  - models/
    - schema.py
  - prompts/
    - kivo_agent_prompts.json
  - services/
    - authenticate_agent.py
    - batchify_data.py
    - decrypt_api_key.py
    - email_notifier.py
    - llm_engine.py
    - mcp_connection.py
    - my_sql_client.py
    - redis_common_state.py
- pm_board_data/
- api_kivo/
  - core/
- .env
- .gitignore
- main.py
- pyproject.toml
- README.md
- requirements.txt


**11. Generating Encrypted Key and Entering into Database**

This section guides you through encrypting your LLM API key and inserting it into the database for production use.

### Step 1: Choose Environment Mode

Set the environment mode in your `.env` file:

- For **development** mode:
  ```env
  PRODUCTION_MODE="false"
  ```
  Provide credentials (model, key, base URL) directly in the `.env` for each agent.

- For **production** mode:
  ```env
  PRODUCTION_MODE="true"
  ```
  Follow the instructions below to store credentials securely in the database.

---

### Step 2: Generate Encryption Key & Encrypt API Key

1. Open `app/services/fernet.py`.
2. Modify the line `raw_key = "..."` to contain your actual API key.
3. Run the script:

   ```bash
   cd app/services
   python fernet.py
   ```

4. The output will display:
   ```
   Generated LLM_ENCRYPTION_KEY:
   your-encryption-key

   Encrypted API Key:
   gAAAAAB...

   Decrypted Back:
   sk-xxx...
   ```

---

### Step 3: Set `LLM_ENCRYPTION_KEY` in .env

Copy the generated `LLM_ENCRYPTION_KEY` from Step 2 and add it to your `.env` file:

```env
LLM_ENCRYPTION_KEY=your-encryption-key
```

This key will be used at runtime to decrypt credentials.

---

### Step 4: Insert Encrypted Key into the Database

Use the following SQL query to insert the encrypted key:

```sql
INSERT INTO iats_llm_credentials (
  company_id,
  llm_model,
  llm_key,
  llm_base_url,
  app_name,
  created_at,
  updated_at
) VALUES (
  '1',
  'openai/gpt-4o',
  'your-encrypted-key-here',
  'https://llm.kivo.ai/v1',
  'iats_sequential_flow',
  NOW(),
  NOW()
);
```

Replace placeholders as follows:
- `'1'`: your company ID
- `'openai/gpt-4o'`: the model name
- `'your-encrypted-key-here'`: the encrypted API key from Step 2
- `'iats_sequential_flow'`: the app name

---

Once this is set up, the application will automatically decrypt the key using the `LLM_ENCRYPTION_KEY` at runtime.
```