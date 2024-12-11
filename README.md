# 🐰 Rabbit Route - AI Travel Itinerary Planner

Rabbit Route is a modern, AI-powered travel itinerary planner that helps users create personalized travel experiences. The application combines the power of OpenAI's GPT models with a user-friendly interface to generate detailed, customized travel plans. Let AI plan your next adventure!

## 🌟 Features

### Core Functionality
- **AI-Powered Itinerary Generation**: Creates detailed day-by-day travel plans including:
  - Accommodation recommendations
  - Restaurant suggestions with ratings
  - Daily activities and attractions
  - Local travel tips
  - Cultural insights
  - Weather information

### User Experience
- **Interactive Trip Planning**: 
  - Destination search
  - Date range selection
  - Travel preferences customization
  - Budget consideration
  - Activity level preferences
  - Dietary requirements

### Profile Management
- **User Profiles**:
  - Customizable profile information
  - Travel preferences
  - Accessibility requirements
  - Language preferences
  - Profile picture management

### Trip Management
- **Trip Organization**:
  - View all planned trips
  - Favorite trips
  - Delete/recover trips
  - Track travel statistics
  - Set and manage travel goals

## 🛠 Technology Stack

### Frontend
- React 18.3
- Vite
- TailwindCSS
- Framer Motion
- Headless UI
- React Router DOM
- Lucide Icons
- React Easy Crop
- ESLint

### Backend
- FastAPI
- SQLModel
- Alembic (Database migrations)
- OpenAI API
- Supabase (Authentication)
- JWT Authentication
- PostgreSQL

## 🚀 Getting Started

### Prerequisites
- Node.js (v16 or higher)
- Python (3.8 or higher)
- PostgreSQL database
- Supabase account
- OpenAI API key

### Environment Variables
Create a `.env` file in both frontend and backend directories:

#### Frontend (.env)
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_API_KEY=your_supabase_api_key
```

#### Backend (.env)
```
DATABASE_URL=your_postgresql_url
SUPABASE_SECRET_KEY=your_supabase_secret_key
JWT_ALGORITHM=HS256
OPENAI_API_KEY=your_openai_api_key
```

### Installation

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn main:app --reload
```

## 🎯 API Endpoints

### Authentication
- `POST /login`: User login
- `POST /registration`: User registration

### Trip Management
- `POST /trips/create`: Create new trip
- `GET /trips`: Get all user trips
- `GET /trips/{trip_id}/details`: Get specific trip details
- `DELETE /trips/{trip_id}`: Delete a trip

### Itinerary
- `GET /itineraries/{trip_id}`: Get detailed itinerary

### User Profile
- `GET /users/profile`: Get user profile
- `POST /users/profile`: Create/update user profile

## 🔒 Security Features
- JWT-based authentication
- Supabase integration for secure user management
- Protected routes
- Input validation and sanitization
- CORS configuration
- Environment variable protection

## 🎨 Design Features
- Responsive design
- Animated transitions
- Modern UI components
- Interactive elements
- Loading states
- Error handling states
- Dark/light mode support

## 🤝 Contributing
We welcome contributions to Rabbit Route! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments
- OpenAI for providing the GPT API
- Supabase for authentication services
- All contributors and supporters of the project

## 📧 Contact
For any queries or support, please reach out to me at jordanchurch95@gmail.com

---
Built with ❤️ by the Rabbit Route Team

