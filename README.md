## Overview
Recos AI is an advanced AI-powered recruitment assistant designed to streamline the hiring process through integration with the Odoo HR system. Built with a Django REST Framework backend, Recos provides a robust API for managing recruiters, job postings, candidates, interviews, and AI-driven analytics. The system features secure authentication via Odoo credentials, automated workflows for interview scheduling, AI-assisted question generation, and comprehensive candidate evaluation reports. Interactive API documentation is available via Swagger and Redoc.

## Features
- Recruiter registration, login, and authentication with Odoo credentials
- CRUD operations for recruiters, companies, jobs, candidates, interviews, interview conversations, and AI reports
- Secure integration with Odoo HR system for synchronized data management
- AI-driven analytics, including skill match scores, candidate strengths/weaknesses, and hiring recommendations
- Automated interview scheduling and AI-generated question/answer analysis
- API documentation with Swagger UI and Redoc
- Modular PostgreSQL database schema for efficient data management
- Secure endpoints with configurable authentication and permissions
## Technology Stack
- Python 3.13+
- Django 4.2+
- Django REST Framework
- drf-yasg (Swagger / Redoc API docs)
- PostgreSQL
- Token authentication

## Getting Started
### Prerequisites
- Python 3.13 or higher
- pip package manager
- Virtual environment tool
- Database
### Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/akirachix/recos-backend.git
   cd recos-backend
   ```
2. Create and activate a virtual environment:
   **Linux/macOS:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
   **Windows:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```
4. Set environment variables and update `settings.py`
   - Configure your database, Odoo API credentials, secret keys, and static/media paths
5. Run database migrations:
   ```bash
   python manage.py migrate
   ```
6. Create a superuser for admin access:
   ```bash
   python manage.py createsuperuser
   ```
7. Collect static files:
   ```bash
   python manage.py collectstatic
   ```
8. Start the development server:
   ```bash
   python manage.py runserver
   ```
   
## API Documentation
- [Swagger UI](https://recos-662b3d74caf2.herokuapp.com/swagger/)
- [Redoc](https://recos-662b3d74caf2.herokuapp.com/redoc/)








