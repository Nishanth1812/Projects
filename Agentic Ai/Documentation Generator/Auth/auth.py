from flask import Blueprint,flash,redirect,render_template,request,session,url_for
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash,check_password_hash
from functools import wraps
from Auth.auth_utils import validate_username,validate_password,secure_token,save_user,load_user,user_exists



auth_bp=Blueprint("auth",__name__)


"""Register Blueprint"""

@auth_bp.route('/register',methods=['GET','POST'])
def register():
    if request.method=='GET':
        # render_template('register.html')
        pass
        
        
    data=request.get_json(silent=True) or {}
    
    
    email=data.get('email','') 
    username=data.get('username','') 
    password=data.get('password','') 
    conf_password=data.get('confirm_password','') 
    pat=data.get('pat','') 
    
    """Form validation"""
    if not email:
        flash("Email is required.", 'error')
        return {'status': 'error', 'message': "Email is required."}, 400
    
    
    username_validation=validate_username(username=username)
    password_validation=validate_password(password=password)
    
    if not username_validation[1]:  
        flash(username_validation[0], 'error')
        return {'status': 'error', 'message': username_validation[0]}, 400


    if not password_validation[1]: 
        flash(password_validation[0], 'error')
        return {'status': 'error', 'message': password_validation[0]}, 400

    if password != conf_password:
        flash("Passwords do not match.", 'error')
        return {'status': 'error', 'message': "Passwords do not match."}, 400
    
    if user_exists(username):
        flash('User already registered.', 'error')
        return {'status': 'error', 'message': 'User already registered.'}, 409
    
    try:
        token=secure_token(pat)
        save_user(username, email, generate_password_hash(password),token) #type: ignore
        
        flash('User registered successfully.', 'success')
        return {'status': 'success', 'message': 'User registered successfully.'}
    except Exception as e:
        flash(f'Registration failed: {str(e)}', 'error')
        return {'status': 'error', 'message': f'Registration failed: {str(e)}'}, 500


@auth_bp.route('/login',methods=['GET','POST'])
def login():
    if request.method=='GET':
        # return render_template('login.html')
        pass
    
    data=request.get_json(silent=True) or {} 
    
    username=data.get('username','') or {}
    password=data.get('password','') or {} 
    
    
    """Form Validation"""
    
    if not username:
        flash("Username is required.", 'error')
        return {'status': 'error', 'message': "Username is required."}, 400
    if not password:
        flash("Password is required.", 'error')
        return {'status': 'error', 'message': "Password is required."}, 400
    
    user = load_user(username=username)
    if not user:
        flash('User not found.', 'error')
        return {'status': 'error', 'message': 'User not found.'}, 404

    if not user.get('password_hash') or not check_password_hash(user['password_hash'], password): #type: ignore
        flash('Incorrect username or password.', 'error')
        return {'status': 'error', 'message': 'Incorrect username or password.'}, 401

    session['username'] = username
    session['access token'] = create_access_token(identity=username)
    flash('Login successful.', 'success')
    return {'status': 'success', 'message': 'Login successful.'}