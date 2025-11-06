from flask import Flask
from flask_jwt_extended import JWTManager
from Auth.auth import auth_bp
import os 

app = Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY") 
JWTManager(app)
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    app.run(debug=True) 