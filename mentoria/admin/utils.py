from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

# Função decoradora para proteger rotas de admin
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("Acesso não autorizado.", "danger")
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function