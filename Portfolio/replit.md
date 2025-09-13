# Portfolio Website Project

## Overview
A stylish portfolio website built with Python Flask backend, modern HTML/CSS frontend, and interactive JavaScript features. The website showcases personal projects, skills, and provides a contact form for potential clients or employers.

## Project Structure
```
.
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css     # Modern CSS with animations
│   ├── js/
│   │   └── script.js     # Interactive JavaScript
│   └── images/           # Image assets (placeholder)
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
└── replit.md            # Project documentation
```

## Features
- **Responsive Design**: Mobile-first approach with modern CSS Grid and Flexbox
- **Interactive Navigation**: Smooth scrolling, mobile hamburger menu, active link highlighting
- **Hero Section**: Animated hero with gradient backgrounds and floating effects
- **About Section**: Skills showcase with interactive hover effects
- **Projects Gallery**: Filterable project cards with categories
- **Contact Form**: Working contact form with Flask backend (requires email configuration)
- **Modern Animations**: CSS animations and JavaScript interactions throughout

## Technologies Used
- **Backend**: Python 3.11, Flask 3.1.2, Flask-Mail 0.10.0
- **Frontend**: HTML5, CSS3 (with custom properties), Vanilla JavaScript
- **Styling**: Modern CSS with gradients, shadows, and animations
- **Icons**: Font Awesome 6.0
- **Fonts**: Google Fonts (Inter)

## Recent Changes
- September 13, 2025: Initial project setup with complete portfolio structure
- Created responsive design with modern styling
- Implemented interactive JavaScript features
- Set up Flask backend with contact form functionality
- Configured for GitHub deployment readiness

## User Preferences
- Requested stylish design with modern aesthetics
- Wanted exportable structure for GitHub management
- Preferred Python, HTML/CSS, and JavaScript stack

## Development Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run the application: `python app.py`
3. Visit: http://localhost:5000

## Deployment Notes
- The project is structured for easy GitHub deployment
- Contact form requires email configuration (MAIL_USERNAME, MAIL_PASSWORD environment variables)
- Flask app is configured to run on 0.0.0.0:5000 for deployment compatibility
- Includes proper .gitignore for Python projects

## Configuration
- **Session Secret**: Uses SESSION_SECRET environment variable
- **Email**: Requires MAIL_USERNAME and MAIL_PASSWORD for contact form functionality
- **Debug Mode**: Enabled for development, should be disabled for production