# Frost Marketplace - Quick Start Guide

## Installation

```bash
pip install fastapi uvicorn stripe requests
```

## Starting the Marketplace

```bash
cd c:\Users\thatg\Desktop\Frost
python marketplace_api.py
```

The marketplace will be available at: `http://localhost:8000`

## API Documentation

Once running, visit: `http://localhost:8000/docs` for interactive API documentation.

## Testing with Demo Client

In a new terminal:

```bash
python agent_client_example.py
```

This will:

1. Discover available services
2. Purchase the Job Scanner API
3. Use the API to scan for jobs
4. Display results

## Available Services

- **Job Scanner API**: $5/month - Scan Upwork & LinkedIn
- **Cover Letter Generator**: $0.50/use - GPT-4 powered letters
- **Automation Toolkit**: $20 one-time - Full source code
- **Profile Optimizer**: $10 one-time - AI profile enhancement

## For Other AI Agents

Your marketplace is now discoverable at `http://localhost:8000/services`

Agents can:

1. GET `/services` - Discover offerings
2. POST `/purchase` - Buy a service
3. Use service endpoints with their API key

## Revenue Tracking

All sales are automatically tracked in `revenue_data.json` and can be withdrawn via:

```bash
python trigger_transfer.py
```
