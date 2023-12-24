import traceback
from flask import Blueprint, render_template, request, flash, redirect, url_for
from email_validator import validate_email
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from . import db
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)


# Страница регистрации
@auth.route('/register', methods=['GET', 'POST'])
def registration():
    data = request.form
    if request.method == 'POST':
        first_name = data.get('first_name')
        password1 = data.get('password1')
        password2 = data.get('password2')
        user = User.query.filter_by(first_name=first_name).first()
        if user:
            flash('Пользователь с таким именем существует', category='error')
        if len(first_name) < 2:
            flash('Имя не может быть короче 2 символов', category='error')
        elif password1 != password2:
            flash('Пароли не совпадают', category='error')
        elif len(password1) < 4:
            flash('Пароль не может быть короче 4 символов', category='error')

        else:
            try:
                newUser = User(first_name=first_name, password=generate_password_hash(password1))
                db.session.add(newUser)
                db.session.commit()
                user = User.query.filter_by(first_name=first_name).first()
                login_user(user, remember=True)
                flash('Аккаунт успешно создан', category='success')
                return redirect(url_for('views.home'))
            except:
                traceback.print_exc()
                flash('Ошибка при регистрации', category='error')

    return render_template('registration.html', title='Регистрация', user=current_user)


# Страница входа
@auth.route('/login', methods=['GET', 'POST'])
def login():
    data = request.form
    if request.method == 'POST':
        first_name = data.get('first_name')
        password = data.get('password')
        user = User.query.filter_by(first_name=first_name).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember=True)
                flash('Успешная авторизация', category='success')
                return redirect(url_for('views.home'))
            else:
                flash('Неверный пароль', category='error')
        else:
            flash('Пользователь с таким именем отсутствует', category='error')
    return render_template('login.html', title='Вход', user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.home'))
