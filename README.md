# FADDSS System - Barangay Management System

Two-portal system for barangay resident management and profiling.

##  Architecture

- **Backend**: Django REST Framework (Pseudo-Microservices)
- **Admin Portal**: React + Vite + Tailwind CSS
- **Resident Portal**: React + Vite + Tailwind CSS

##  Project Structure
```
FADDSS-System/
├── backend/              # Django API
├── frontend/
│   ├── admin-portal/     # Staff/Admin interface
│   └── resident-portal/  # Resident interface
```

##  Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (for production)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Backend runs at: http://localhost:8000

### Admin Portal Setup
```bash
cd frontend/admin-portal
npm install
npm run dev
```

Admin Portal runs at: http://localhost:5173

### Resident Portal Setup
```bash
cd frontend/resident-portal
npm install
npm run dev
```

Resident Portal runs at: http://localhost:5174

##  Environment Variables

### Backend (.env)
```
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://localhost/faddss_db
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
```

##  Modules

- **accounts** - User management, roles, permissions
- **authentication** - JWT authentication
- **residents** - Basic resident records
- **profiling** - Household, family, and personal profiling

##  Testing
```bash
# Backend tests
cd backend
python manage.py test

# Frontend tests
cd frontend/admin-portal
npm test
```

##  API Documentation

API docs available at: http://localhost:8000/api/docs/

##  Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

##  License

This project is licensed under the MIT License.