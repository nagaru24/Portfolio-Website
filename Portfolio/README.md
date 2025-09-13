# Portfolio Website

A modern, responsive portfolio website built with Python Flask, featuring interactive JavaScript elements and stylish CSS animations.

## 🌟 Features

- **Responsive Design**: Mobile-first approach with modern CSS Grid and Flexbox
- **Interactive Navigation**: Smooth scrolling, mobile hamburger menu, active link highlighting
- **Hero Section**: Animated hero with gradient backgrounds and floating effects
- **About Section**: Skills showcase with interactive hover effects
- **Projects Gallery**: Filterable project cards with categories (Web, Mobile, Desktop)
- **Contact Form**: Working contact form with Flask backend and email integration
- **Modern Animations**: CSS animations and JavaScript interactions throughout
- **Back-to-Top Button**: Smooth scroll to top functionality

## 🛠️ Technologies Used

- **Backend**: Python 3.11, Flask 3.1.2, Flask-Mail 0.10.0
- **Frontend**: HTML5, CSS3 (with custom properties), Vanilla JavaScript
- **Styling**: Modern CSS with gradients, shadows, and animations
- **Icons**: Font Awesome 6.0
- **Fonts**: Google Fonts (Inter)

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/portfolio-website.git
   cd portfolio-website
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (for contact form)
   ```bash
   export SESSION_SECRET="your-secret-key-here"
   export MAIL_USERNAME="your-email@gmail.com"
   export MAIL_PASSWORD="your-app-password"
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Visit the website**
   Open your browser and go to `http://localhost:5000`

## 📁 Project Structure

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
│   └── images/           # Image assets
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
└── README.md            # Project documentation
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SESSION_SECRET` | Secret key for Flask sessions | Yes |
| `MAIL_USERNAME` | Email username for contact form | Optional* |
| `MAIL_PASSWORD` | Email password/app password | Optional* |

*Required only if you want the contact form to send emails

### Email Setup (Gmail Example)

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
3. Use your Gmail address as `MAIL_USERNAME`
4. Use the generated app password as `MAIL_PASSWORD`

## 🎨 Customization

### Personal Information
Edit the following in `templates/index.html`:
- Replace "Your Name" with your actual name
- Update contact information (email, LinkedIn, GitHub)
- Modify the about section with your bio
- Update projects with your actual projects

### Styling
- Colors and themes: Edit CSS custom properties in `static/css/style.css`
- Fonts: Change the Google Fonts import in the HTML template
- Animations: Modify CSS animations and JavaScript interactions

### Adding Projects
Add new project cards in the projects section of `templates/index.html`:
```html
<div class="project-card" data-category="web">
    <div class="project-image">
        <i class="fas fa-your-icon"></i>
    </div>
    <div class="project-content">
        <h3>Your Project Name</h3>
        <p>Project description...</p>
        <div class="project-tech">
            <span class="tech-tag">Technology</span>
        </div>
        <div class="project-links">
            <a href="#" class="project-link"><i class="fab fa-github"></i></a>
            <a href="#" class="project-link"><i class="fas fa-external-link-alt"></i></a>
        </div>
    </div>
</div>
```

## 🚀 Deployment

### GitHub Pages (Static Version)
To deploy as a static site, you'll need to convert the Flask app to static HTML.

### Heroku
1. Create a `Procfile`:
   ```
   web: python app.py
   ```
2. Set environment variables in Heroku dashboard
3. Deploy from GitHub integration

### Other Platforms
The app is compatible with any platform that supports Python/Flask:
- PythonAnywhere
- DigitalOcean App Platform
- Railway
- Vercel (with serverless functions)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 📞 Support

If you have any questions or need help with customization, feel free to:
- Open an issue on GitHub
- Contact me through the portfolio contact form
- Connect with me on [LinkedIn](https://linkedin.com/in/yourprofile)

---

⭐ Star this repository if you found it helpful!