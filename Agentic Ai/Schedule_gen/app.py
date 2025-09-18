from flask import Flask, render_template, session, redirect, url_for, flash
from Backend.auth import auth_bp
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__, template_folder='Frontend/Templates', static_folder='Frontend/scripts')
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))


app.register_blueprint(auth_bp, url_prefix='/')

@app.route('/')
def index():
    """Renders the landing page."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    else:
        flash("You need to be logged in to see this page.", "warning")
        return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True)
