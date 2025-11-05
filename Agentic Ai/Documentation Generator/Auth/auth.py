from flask import Blueprint,flash,redirect,render_template,session,url_for
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv
from functools import wraps
from auth_utils import validate_username,validate_password,secure_token,save_user,load_user


load_dotenv()

auth_bp=Blueprint("auth",__name__)


"""Register Blueprint"""




