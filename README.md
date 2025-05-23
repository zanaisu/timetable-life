# Timetable - A-Level Revision Platform

A web-based timetable application designed to help students manage their A-Level revision efficiently. The system uses a confidence-based algorithm to prioritize topics and subtopics that need more attention.

## Features

- **Confidence-Based Task Generation**: Tasks are generated based on confidence levels to focus on weaker areas
- **Subtopic Prioritization**: Mark specific subtopics as priorities to ensure they appear more frequently
- **Curriculum Browser**: View and manage your curriculum structure with confidence tracking
- **Progress Tracking**: Monitor your study progress over time
- **Calendar View**: Visualize your study schedule and completed tasks
- **Dark Mode Support**: Choose between light and dark themes
- **Dual Database Support**: Local database for development and Railway database for production
- **Database Management Interface**: Web-based interface for managing database files

## Project Structure

```
timetable/
├── app/                    # Main application package
│   ├── models/            # Database models
│   ├── routes/            # Route definitions
│   ├── static/            # Static files (CSS, JS)
│   ├── templates/         # HTML templates
│   ├── utils/             # Utility functions
│   └── __init__.py        # App initialization
├── config/                # Configuration files
├── data/                  # Data files (curriculum.jsonc)
├── migrations/            # Database migrations
├── tests/                 # Test files
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
└── run.py                 # Application entry point
```

## Technologies Used

- **Backend**: Python with Flask
- **Database**: PostgreSQL
- **Frontend**: HTML, JavaScript, CSS
- **CSS Framework**: Custom CSS with glassmorphism design
- **Charts**: Chart.js for visualizations
- **Icons**: Font Awesome

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/timetable.git
   cd timetable
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env` file:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   
   # Local Database
   LOCAL_DATABASE_URI=postgresql://user:password@localhost:5432/timetable
   
   # Railway Database
   DATABASE_URL=postgresql://postgres:ZhhasIZcLyTEmRVyFigfPkgXhiNqRnCH@postgres.railway.internal:5432/railway
   ```

4. Initialize and manage the database:
   ```
   flask db-manage
   ```
   This will open a browser-based interface for database management.

5. Run the application:
   ```
   flask run
   ```

## Database Configuration

The application is configured to support two database connections:

1. **Local Database**: Used for development and testing
2. **Railway Database**: Used for production deployment

The database connection is determined by the `FLASK_ENV` environment variable. The application uses the local database in development mode and the Railway database in production mode.

## Confidence System

The confidence system is based on a 1-5 scale:

- **1**: Not confident at all
- **2**: Slightly confident
- **3**: Moderately confident
- **4**: Confident
- **5**: Very confident

The weighting system gives higher priority to topics with lower confidence levels using the formula: (7 - confidence_level)²

## Task Generation

Tasks are generated based on:

1. The user's study hours per day
2. A balanced distribution across subjects
3. Confidence levels for topics and subtopics
4. Prioritized subtopics
5. Task types enabled by the user

## API Routes

The application provides the following API endpoints:

### Authentication
- `POST /api/auth/login`: User login
- `POST /api/auth/register`: User registration
- `POST /api/auth/logout`: User logout
- `GET /api/auth/status`: Get current user authentication status

### Curriculum
- `GET /api/curriculum/subjects`: Get all subjects
- `GET /api/curriculum/subjects/<subject_id>`: Get a specific subject
- `GET /api/curriculum/topics`: Get all topics
- `GET /api/curriculum/topics/<topic_id>`: Get a specific topic
- `GET /api/curriculum/subtopics`: Get all subtopics
- `GET /api/curriculum/subtopics/<subtopic_id>`: Get a specific subtopic

### Confidence Management
- `POST /api/confidence/topic`: Update topic confidence level
- `POST /api/confidence/subtopic`: Update subtopic confidence level
- `GET /api/confidence/stats`: Get confidence statistics

### Tasks
- `GET /api/tasks`: Get all tasks
- `GET /api/tasks/<task_id>`: Get a specific task
- `POST /api/tasks`: Create a new task
- `PUT /api/tasks/<task_id>`: Update a task
- `DELETE /api/tasks/<task_id>`: Delete a task
- `POST /api/tasks/generate`: Generate tasks based on confidence levels
- `POST /api/tasks/complete/<task_id>`: Mark a task as complete

### Progress
- `GET /api/progress/daily`: Get daily progress stats
- `GET /api/progress/weekly`: Get weekly progress stats
- `GET /api/progress/monthly`: Get monthly progress stats
- `GET /api/progress/subjects`: Get progress by subject

## Flask CLI Commands

The application provides the following Flask CLI commands:

### Database Management
- `flask db-manage`: Open the database management interface in a browser. Allows importing, exporting, and managing database files via a web interface.
- `flask db migrate`: Generate a database migration (after model changes).
- `flask db upgrade`: Apply database migrations.

### Data Management
- `flask verify-data`: Verify the integrity of imported curriculum data.

### Server Management
- `flask run`: Run the development server.
- `flask routes`: Display all registered routes.
- `flask shell`: Run a Python shell with the Flask app context.

## Development

To run the application in development mode:

```
export FLASK_ENV=development
flask run
```

For database migrations:

```
flask db migrate -m "Migration message"
flask db upgrade
```

## Database Management Interface

The application includes a web-based database management interface that can be accessed by running:

```
flask db-manage
```

This interface provides the following functionality:
- View current database information
- Export the current database to a file
- Import database files
- Cache and manage multiple database versions
- Apply a cached database file
- Import curriculum data

The interface is password-protected for security.
