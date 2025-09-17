from flask import Blueprint,request,flash,render_template,redirect,url_for,session
from flask_jwt_extended import create_access_token 
from werkzeug.security import generate_password_hash,check_password_hash
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import os 
from utils import validate_username, validate_password

load_dotenv()

# setting up mongo client
client=MongoClient(os.getenv("MONGODB_URI"))
db=client[os.getenv("DATABASE_NAME","Schedule_gen")]
user_col=db[os.getenv("COLLECTION_NAME","Users")]

# Setting up the blueprint
auth_bp=Blueprint("auth",__name__)

# Registration route with flash messages
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Username validation
        if not username:
            flash('Username is required', 'warning')
            return render_template('register.html')
        
        is_valid, error_msg = validate_username(username)
        if not is_valid:
            flash(error_msg, 'warning')
            return render_template('register.html')

        # Password validation
        if not password:
            flash('Password is required', 'warning')
            return render_template('register.html')
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            flash(error_msg, 'warning')
            return render_template('register.html')

        # Confirm password validation
        if password != confirm_password:
            flash('Passwords do not match', 'warning')
            return render_template('register.html')

        # Check if username already exists
        if user_col.find_one({'username': username}):
            flash('Username already exists', 'warning')
            return render_template('register.html')

        # Create new user
        try:
            hashed_password = generate_password_hash(password)
            user_data = {
                'username': username,
                'password': hashed_password,
                'created_at': datetime.utcnow(),
                'last_login': None,
                'is_active': True
            }
            
            result = user_col.insert_one(user_data)
            
            if result.inserted_id:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Registration failed. Please try again.', 'error')
                
        except Exception as e:
            flash('An error occurred during registration. Please try again.', 'error')
            print(f"Registration error: {e}")

    return render_template('register.html')

# Login route with flash messages
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Username and password are required', 'warning')
            return render_template('login.html')

        user = user_col.find_one({'username': username})
        if not user or not check_password_hash(user['password'], password):
            flash('Invalid username or password', 'warning')
            return render_template('login.html')

        # Successful login
        try:
            # Update last login
            user_col.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow()}}
            )
            
            # Create session
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            
            # Create JWT token for API access
            access_token = create_access_token(identity=str(user['_id']))
            session['access_token'] = access_token
            
            flash(f'Welcome back, {user["username"]}!', 'success')
            
            # Redirect directly to dashboard after successful login
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash('Login failed. Please try again.', 'error')
            print(f"Login error: {e}")

    return render_template('login.html')

# Logout route
@auth_bp.route('/logout')
def logout():
    if 'username' in session:
        username = session['username']
        session.clear()
        flash(f'You have been logged out successfully, {username}.', 'info')
    else:
        flash('You were not logged in.', 'info')
    
    return redirect(url_for('auth.login'))

# Profile route (requires login)
@auth_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    user = user_col.find_one({'_id': user_id})
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('profile.html', user=user)

# Change password route
@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        user_id = session.get('user_id')
        user = user_col.find_one({'_id': user_id})
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('auth.login'))
        
        # Verify current password
        if not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect', 'warning')
            return render_template('change_password.html')
        
        # Validate new password
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            flash(error_msg, 'warning')
            return render_template('change_password.html')
        
        # Check if new password matches confirmation
        if new_password != confirm_password:
            flash('New passwords do not match', 'warning')
            return render_template('change_password.html')
        
        # Update password
        try:
            hashed_password = generate_password_hash(new_password)
            user_col.update_one(
                {'_id': user['_id']},
                {'$set': {'password': hashed_password}}
            )
            flash('Password changed successfully', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            flash('Failed to change password. Please try again.', 'error')
            print(f"Password change error: {e}")
    
    return render_template('change_password.html')