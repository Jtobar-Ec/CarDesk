from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ...forms import LoginForm, RegisterForm, EditProfileForm
from ...database.models import Usuario
from ...database import db

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(u_username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            flash('Inicio de sesión exitoso', 'success')
            return redirect(next_page)
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    # Mostrar enlace de registro solo si no hay usuarios
    show_register_link = Usuario.query.count() == 0
    return render_template('auth/login.html', form=form, show_register_link=show_register_link)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Verificar si ya existe al menos un usuario
    existing_users = Usuario.query.count()
    if existing_users > 0:
        flash('El registro está deshabilitado. Ya existe una cuenta de administrador.', 'error')
        return redirect(url_for('auth.login'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = Usuario(u_username=form.username.data)
        user.set_password(form.password.data)
        user.save()
        flash('Registro exitoso. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.u_username)
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.u_username = form.username.data
            if form.new_password.data:
                current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Tu perfil ha sido actualizado correctamente', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Contraseña actual incorrecta', 'error')
    elif request.method == 'GET':
        form.username.data = current_user.u_username
    
    return render_template('auth/profile.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('auth.login'))