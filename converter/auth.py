import traceback
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Users
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
        user = Users.query.filter_by(first_name=first_name).first()
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
                newUser = Users(first_name=first_name, password=generate_password_hash(password1))
                db.session.add(newUser)
                db.session.commit()
                user = Users.query.filter_by(first_name=first_name).first()
                login_user(user, remember=True)
                flash('Аккаунт успешно создан', category='success')
                return redirect(url_for('views.home_redirector'))
            except:
                traceback.print_exc()
                flash('Ошибка при регистрации', category='error')

    return render_template('registration.html', title='Регистрация', user=current_user)


# Страница входа
@auth.route('/login', methods=['GET', 'POST'])
def login():
    data = request.form
    first_name = data.get('first_name')
    password = data.get('password')
    lite = data.get('lite', False)  # Флаг для толстого клиента, чтобы не генерировать страницы.
    user = Users.query.filter_by(first_name=first_name).first()
    if user:
        if check_password_hash(user.password, password):
            login_user(user, remember=True)
            if lite:
                return {}, 200
            flash('Успешная авторизация', category='success')
            return redirect(url_for('views.home_redirector')), 200
        else:
            if lite:
                return {}, 400
            flash('Неверный пароль', category='error')
    else:
        flash('Пользователь с таким именем отсутствует', category='error')
    return render_template('login.html', title='Вход', user=current_user), 400


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.home_redirector'))


@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    try:
        data = request.json
        user_id = data.get('userId')
        new_password = data.get('newPassword')
        confirm_password = data.get('confirmPassword')

        # Проверка на существование данных
        if not all([user_id, new_password, confirm_password]):
            return jsonify({'success': False, 'message': 'Не все поля заполнены.'})

        # Проверка совпадения паролей
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'Пароли не совпадают.'})

        # Найти пользователя по ID
        user = Users.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Пользователь не найден.'})

        # Обновление пароля
        user.password = generate_password_hash(new_password)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Пароль успешно изменен.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': e})


@auth.route('/block-user', methods=['POST'])
@login_required
def block_user():
    try:
        data = request.json
        user_id = data.get('userId')
        # Найти пользователя по ID
        user = Users.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Пользователь не найден.'})
        if user.first_name == 'admin':
            return jsonify({'success': False, 'message': 'Нельзя заблокировать учетную запись администратора.'})
        # Обновление пароля
        user.password = ' '
        db.session.commit()

        return jsonify({'success': True, 'message': 'Пользователь заблокирован, для разблокировки воспользуйтесь сменой пароля'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': e})


@auth.route('/add-user', methods=['POST'])
@login_required
def add_user():
    try:
        data = request.json
        login = data.get('firstName')
        pw = data.get('password')
        pwc = data.get('confirmPassword')
        if not all((login, pw, pwc)):
            return {'success': False, 'message': 'Не все обязательные (*) поля заполнены'}
        if pw != pwc:
            return {'success': False, 'message': 'Введенные пароли не совпадают'}
        new_user = Users(
            fio=data.get('fio', None),
            first_name=login,
            password=generate_password_hash(pw),
            is_judge=data['isJudge']
        )
        db.session.add(new_user)
        db.session.commit()
        return {'success': True, 'message': 'Пользователь успешно добавлен'}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': 'Ошибка при добавлении пользователя: ' + str(e)}
