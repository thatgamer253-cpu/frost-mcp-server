.
├── .dockerignore
├── .env.example             # Example environment variables
├── .gitignore
├── Dockerfile               # Docker build instructions
├── README.md                # This file
├── alembic.ini              # Alembic configuration
├── alembic/                 # Database migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── backend/                 # FastAPI backend application
│   ├── api/
│   │   └── v1/              # API version 1
│   │       ├── api.py       # Main API router
│   │       └── endpoints/   # API endpoints
│   │           ├── auth.py
│   │           ├── dashboard.py
│   │           ├── health.py
│   │           ├── market.py
│   │           ├── portfolio.py
│   │           ├── transactions.py
│   │           ├── users.py
│   │           └── watchlist.py
│   ├── config.py            # Application settings
│   ├── core/                # Core utilities and services
│   │   ├── exceptions.py
│   │   ├── logging_config.py
│   │   └── middleware.py
│   ├── crud.py              # CRUD operations for database models
│   ├── database.py          # Database session and engine setup
│   ├── dependencies.py      # Dependency injection for FastAPI
│   ├── models.py            # SQLAlchemy database models
│   ├── schemas.py           # Pydantic schemas for request/response validation
│   ├── security.py          # Authentication and authorization logic
│   └── services/            # Background services and external integrations
│       ├── backup_restore.py
│       ├── health_monitor.py
│       ├── market_data.py
│       ├── retry_logic.py
│       └── watchdog.py
├── frontend/                # Frontend assets and templates
│   ├── static/
│   │   ├── css/
│   │   │   └── tailwind.css
│   │   └── js/
│   │       ├── alpine.min.js
│   │       ├── auth.js
│   │       ├── chart.min.js
│   │       ├── dashboard.js
│   │       ├── main.js
│   │       ├── portfolio.js
│   │       ├── transactions.js
│   │       ├── user.js
│   │       └── watchlist.js
│   └── templates/
│       ├── auth/
│       │   ├── login.html
│       │   └── register.html
│       ├── base.html
│       ├── dashboard/
│       │   └── index.html
│       ├── index.html
│       ├── portfolio/
│       │   ├── add_asset.html
│       │   ├── edit_asset.html
│       │   └── index.html
│       ├── transactions/
│       │   └── index.html
│       ├── user/
│       │   ├── profile.html
│       │   └── settings.html
│       └── watchlist/
│           └── index.html
├── main.py                  # Main FastAPI application entry point
└── requirements.txt         # Python dependencies