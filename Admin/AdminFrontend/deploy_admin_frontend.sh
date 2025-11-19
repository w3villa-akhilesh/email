#!/bin/bash
set -e

echo "Cleaning local changes (including build)..."
git reset --hard

echo "Pulling latest code..."
git checkout development
git pull origin development

echo "Building Admin Frontend (React)..."
# cd Admin/AdminFrontend
npm ci
npm run build

echo "Deployment successful!" 