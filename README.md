# ninefruits-django
Student Information System running on django framework

## Requirements Management

This project uses `pip-tools` for dependency management to ensure reproducible builds and better dependency resolution.

### Project Structure
- `requirements/base.in` - High-level dependencies (what you want)
- `requirements/base.txt` - Compiled dependencies with exact versions (what you get)

### Installation

#### 1. Install pip-tools (if not already installed)
```bash
pip install pip-tools
```

#### 2. Install project dependencies
```bash
pip install -r requirements/base.txt
```

### Managing Dependencies

#### Adding new dependencies
1. Add the package to `requirements/base.in`
2. Compile the requirements:
   ```bash
   pip-compile requirements/base.in
   ```
3. Install the updated requirements:
   ```bash
   pip install -r requirements/base.txt
   ```

#### Updating dependencies
To update all dependencies to their latest compatible versions:
```bash
pip-compile --upgrade requirements/base.in
pip install -r requirements/base.txt
```

To update a specific package:
```bash
pip-compile --upgrade-package django requirements/base.in
pip install -r requirements/base.txt
```

#### Using Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements/base.txt
```

### Environment Variables

This project uses `django-environ` for environment variable management. You need to set up environment variables before running the application.

#### Option 1: Using .env file (Recommended)
1. Create a `.env` file in the `ninefruits` directory:
   ```bash
   cd ninefruits
   touch .env  # On Windows: echo. > .env
   ```

2. Add the following content to `.env`:
   ```
   DJANGO_SECRET_KEY=your-secret-key-here
   DEBUG=True
   ```

3. Generate a secure secret key:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

#### Option 2: Set environment variables directly
```bash
# On Windows PowerShell:
$env:DJANGO_SECRET_KEY="your-secret-key-here"
$env:DEBUG="True"

# On Windows Command Prompt:
set DJANGO_SECRET_KEY=your-secret-key-here
set DEBUG=True

# On macOS/Linux:
export DJANGO_SECRET_KEY="your-secret-key-here"
export DEBUG="True"
```

### Frontend Setup (Svelte)

This project uses Django with Svelte frontend. The Svelte app is located in the `django_svelte` directory.

#### Build Svelte App
1. Navigate to the Svelte app directory:
   ```bash
   cd django_svelte
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Build the Svelte app for production:
   ```bash
   npm run build
   ```

4. For development with hot reload (optional - for standalone Svelte development):
   ```bash
   npm run dev
   ```
   
   **Note**: In this Django-Svelte setup, you typically only need `npm run build`. 
   The Django server serves the built Svelte components.

#### Project Structure
```
ninefruits-django/
├── ninefruits/              # Django project
│   ├── manage.py
│   └── ninefruits/
│       └── settings.py
├── django_svelte/           # Svelte frontend
│   ├── src/
│   ├── public/
│   │   └── build/          # Built files (generated)
│   └── package.json
└── requirements/            # Python dependencies
```

### Development Setup
1. Clone the repository
2. Create and activate virtual environment
3. Install dependencies: `pip install -r requirements/base.txt`
4. **Build Svelte frontend** (see above)
5. Navigate to Django project: `cd ninefruits`
6. **Set up environment variables** (see above)
7. Run migrations: `python manage.py migrate`
8. **Create superuser** (optional):
   ```bash
   # Interactive creation (recommended):
   python manage.py createsuperuser
   
   # Non-interactive creation (for scripts):
   python manage.py createsuperuser --username admin --email admin@example.com --noinput
   python manage.py changepassword admin

   # Linux Command Prompt:
   DJANGO_SUPERUSER_PASSWORD=your_password python manage.py createsuperuser --username admin --email admin@example.com --noinput

   # Windows Command Prompt:
   set DJANGO_SUPERUSER_PASSWORD=your_password && python manage.py createsuperuser --username admin --email admin@example.com --noinput

   # Windows Power Shell:
   $env:DJANGO_SUPERUSER_PASSWORD="your_password"; python manage.py createsuperuser --username admin --email admin@example.com --noinput
   ```
9. Start development server: `python manage.py runserver`