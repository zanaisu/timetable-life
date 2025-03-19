# Technical Context

## Technology Stack

### Backend
- **Python**: Primary language for backend development
- **Flask**: Web framework for API development and rendering templates
- **SQLAlchemy**: ORM for database operations
- **Flask-Migrate**: Database migration management
- **SQLite**: Local development database (PostgreSQL for production)
- **Flask-Login**: User authentication and session management
- **Flask-WTF**: Form handling and validation
- **Flask-Bcrypt**: Password hashing

### Frontend
- **HTML/JavaScript**: Frontend rendering and interactivity
- **CSS with Custom Variables**: Styling with dark/light theme support
- **Vanilla JavaScript**: No frontend frameworks, pure JavaScript
- **Fetch API**: AJAX requests to backend endpoints
- **CSS Grid/Flexbox**: Responsive layout system
- **CSS Glass Morphism**: Modern UI styling with transparency effects

### Project Structure
```
timetable/
├── app/                      # Main application package
│   ├── __init__.py           # Application factory
│   ├── models/               # SQLAlchemy models
│   ├── routes/               # Route definitions
│   │   ├── api/              # API endpoints
│   │   └── ...               # Other route modules
│   ├── static/               # Static assets
│   │   ├── css/              # CSS stylesheets
│   │   └── js/               # JavaScript files
│   ├── templates/            # Jinja2 templates
│   └── utils/                # Utility functions
├── config/                   # Configuration files
├── data/                     # Data import files
├── instance/                 # Instance-specific files
│   └── app.db                # SQLite database
├── memory-bank/              # Documentation
│   └── ...                   # Memory bank files
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
└── start_app.bat             # Windows batch starter
```

## Development Environment Setup

### Windows Setup
1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment: `.\.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables in `.env`
6. Initialize the database: `flask --app run.py init-db`
7. Run the application: `flask --app run.py run --debug`

### Alternative Startup Method
You can also use the provided batch files:
- `run_app.bat`: Runs the application with the Flask development server
- `start_app.bat`: Starts the application in a new command window

### Dependencies
The application depends on the following major packages:
- Flask 2.3.3
- Flask-SQLAlchemy 3.1.1
- Flask-Migrate 4.0.5
- Flask-Login 0.6.3
- Python-dotenv 1.0.0
- Werkzeug 2.3.7
- Flask-Bcrypt 1.0.1

### Dependency Management
The project uses a virtual environment to manage dependencies. Key points:
- Dependencies are listed in `requirements.txt`
- The application expects dependencies to be installed in the virtual environment
- The path to the virtual environment is configured in `run_app.py`
- If running into module import errors, check that the virtual environment path in `run_app.py` is correct

### Known Dependency Issues
- When running the app, you might encounter "No module named 'flask_sqlalchemy'" or similar errors
- This typically happens because the Python interpreter isn't finding packages in the virtual environment
- Solution: Update the virtual environment path in `run_app.py` to point to the correct location
- Current path convention: `../Cline rendtition/.venv/Lib/site-packages`
- Verify this path exists on your system and adjust if necessary

## Database Architecture

### Core Models
- **User**: User account information and authentication
- **Task**: Generated study tasks for users
- **Subject**: High-level curriculum categories
- **Topic**: Subject subdivisions
- **Subtopic**: Detailed topic components
- **TopicConfidence/SubtopicConfidence**: Track user confidence levels
- **TaskDistribution**: Configure task generation preferences

### Database Relationships
Key relationships in the database:
1. **User** to **Task**: One-to-many
2. **Subject** to **Topic**: One-to-many
3. **Topic** to **Subtopic**: One-to-many
4. **User** to **TopicConfidence**: One-to-many
5. **User** to **SubtopicConfidence**: One-to-many
6. **User** to **TaskDistribution**: One-to-many

### Database Operations
- Database initialization: `flask init-db` CLI command
- Data import: `flask import-data` CLI command
- Curriculum import: `flask import-curriculum` CLI command

## Frontend Architecture

### Styling Approach
The application uses a modular CSS approach:
- `style.css`: Core styling and variables
- `animations.css`: Animation definitions
- `curriculum.css`: Curriculum browser specific styles
- `pomodoro.css`: Pomodoro timer styles
- `progress.css`: Progress tracking styles

### JavaScript Module Pattern
Frontend code follows a consistent module pattern:
```javascript
const ModuleName = (function() {
  // Private variables and functions
  
  // Public API
  return {
    init: function() {
      // Initialize module
    },
    // Other public methods
  };
})();
```

### CSS Variables for Theming
The application uses CSS variables for consistent styling:
```css
:root {
  /* Light mode variables */
  --bg-primary: #f0f4f8;
  --bg-secondary: rgba(200, 210, 220, 0.35);
  --text-primary: #333333;
  --text-secondary: #666666;
  --accent-color: #ff8c29;
  --accent-light: #ffad63;
  /* Other variables */
}

[data-theme="dark"] {
  /* Dark mode variables */
  --bg-primary: #121212;
  --bg-secondary: rgba(20, 20, 25, 0.35);
  --text-primary: #f0f0f0;
  --text-secondary: #aaaaaa;
  /* Other variables */
}
```

### Glass Morphism Design
The UI uses modern glass morphism styling:
- Transparent backgrounds (35% opacity)
- Strong blur effects (16px)
- Subtle border highlights
- Inner shadow highlights
- Background visibility through elements
- Consistent styling across dark and light modes with different background colors

## API Structure

### Main Endpoints
- `/api/tasks`: Task management endpoints
- `/api/curriculum`: Curriculum data access
- `/api/progress`: Progress tracking and reporting
- `/api/confidence`: Confidence level management
- `/api/distribution`: Task distribution preferences

### Authentication Endpoints
- `/auth/login`: User login
- `/auth/register`: User registration
- `/auth/logout`: User logout

### Response Format
All API endpoints return JSON with a consistent format:
```json
{
  "status": "success|error",
  "data": { /* response data */ },
  "message": "Optional status message"
}
```

## Task Generation System

The application uses a sophisticated task generation system:
- Based on curriculum structure
- Influenced by user confidence levels
- Respects task distribution preferences
- Generates appropriate difficulty levels
- Creates varied question types
- Includes time estimation

## UI Design Principles

1. **Glass Morphism Design**
   - Transparent card backgrounds (35% opacity)
   - Strong blur effects (16px)
   - Subtle border highlights
   - Drop shadows for elevation
   - Background visibility through elements

2. **Color Theme**
   - Orange accent colors (#ff8c29 and #ffad63)
   - Color-coded confidence levels
   - Distinct light and dark modes
   - Consistent accent color usage across the application
   - Subtle gradient backgrounds

3. **Responsive Design**
   - Mobile-first approach
   - Flexible layouts with CSS Grid and Flexbox
   - Appropriate spacing for all screen sizes
   - Touch-friendly interactive elements
   - Optimized content flow for small screens

4. **Interactive Elements**
   - Subtle hover effects
   - Smooth transitions and animations
   - Clear focus states
   - Consistent styling across all interactive elements
   - Feedback for user actions

## Testing Strategy

The application employs several testing approaches:
- Unit testing for utility functions
- Integration testing for API endpoints
- Template validation for frontend
- Manual testing for UI components

Key testing tools:
- Python's unittest framework
- Custom template validator
- Flask test client for API testing

## Deployment Strategy

The application supports multiple deployment targets:
- Local development with SQLite
- Testing environment with SQLite
- Production with PostgreSQL on Railway

### Environment Configuration
The application uses environment variables for configuration:
- `.env` file for local development
- Environment variables for production
- Config classes for different environments

### Database Migration
Database schema changes are managed through Flask-Migrate:
- Initialize: `flask db init`
- Create migration: `flask db migrate -m "Migration message"`
- Apply migration: `flask db upgrade`
