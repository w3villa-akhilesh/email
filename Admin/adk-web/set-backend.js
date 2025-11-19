/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const fs = require('fs');
const path = require('path');

// Load environment variables from .env file if it exists
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf8');
    envContent.split('\n').forEach(line => {
        line = line.trim();
        // Skip comments and empty lines
        if (line && !line.startsWith('#')) {
            const [key, ...valueParts] = line.split('=');
            if (key && valueParts.length > 0) {
                const value = valueParts.join('=').trim();
                // Only set if not already set
                if (!process.env[key]) {
                    process.env[key] = value;
                }
            }
        }
    });
}

const configPath = './src/assets/config/runtime-config.json';

// Read backend URL from environment variable only (simple, env-driven config)
const backendUrl = process.env.BACKEND_URL;

if (!backendUrl) {
    console.error('Missing backend URL configuration');
    console.error('');
    console.error('Please set the BACKEND_URL environment variable.');
    console.error('You can do this by creating a .env file next to set-backend.js containing:');
    console.error('');
    console.error('  BACKEND_URL=https://admin-agents.kivo.ai/adk_web_info');
    console.error('');
    console.error('Or by exporting it in your shell before running the app:');
    console.error('  export BACKEND_URL=https://admin-agents.kivo.ai/adk_web_info');
    process.exit(1);
}

const config = {
    backendUrl
};

fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

console.log(`✓ Backend URL injected from env: ${backendUrl}`);
