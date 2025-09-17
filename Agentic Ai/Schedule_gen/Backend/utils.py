def validate_username(username):
    
    if not username:
        return False,"Username is required"
    if len(username)<5 or len(username)>20:
        return False,"Username must be between 5 and 20 characters"
    if not username.isidentifier():
        return False,"Username must contain only letters,numbers and underscores"
    return True,"valid username"

def validate_password(password):
    
    if not password:
        return False,"Password is required"
    if len(password)<8:
        return False,"Password should be atleast 8 characters"
    if not any(c.islower() for c in password):
        return False,"Password must contain atleast 1 lowercase character"
    if not any(c.isupper() for c in password):
        return False,"Password must contain atleast 1 uppercase character"
    if not any(c.isdigit() for c in password):
        return False,"Password must contain atleast 1 digit"
    
    special_chars=r"!@#$%^&*()-_+=<>?/{}~|"
    if not any(c in special_chars for c in password):
        return False,"Password must contain atleast 1 special character"
    return True,"Password accepted"