from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'toza-gilam-pro-maxfiy-kalit-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm_v2.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --- BAZA MODELLARI ---
class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(50), unique=True, nullable=False)
  password = db.Column(db.String(200), nullable=False)
  full_name = db.Column(db.String(100), nullable=False)
  role = db.Column(db.String(20), nullable=False)  # 'admin', 'driver', 'worker'


class Order(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  client_name = db.Column(db.String(100), nullable=False)
  client_phone = db.Column(db.String(20), nullable=False)
  address = db.Column(db.String(200), nullable=False)

  carpet_sqm = db.Column(db.Float, default=0.0)
  korpacha_count = db.Column(db.Integer, default=0)
  adyol_count = db.Column(db.Integer, default=0)

  total_price = db.Column(db.Float, nullable=False)
  status = db.Column(db.String(30), default='Yangi zakaz')

  location_link = db.Column(db.String(300), nullable=True)

  driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

  driver = db.relationship('User', backref='orders', lazy=True)


@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))


# --- ROUTELAR (SAHIFALAR VA AMALLAR) ---


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
      login_user(user)
      return redirect(url_for('dashboard'))
    flash('Login yoki parol xato!', 'danger')
  return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
  search_query = request.args.get('q', '')
  if search_query:
    orders = Order.query.filter(
        (Order.client_name.contains(search_query))
        | (Order.client_phone.contains(search_query))
    ).all()
  else:
    orders = Order.query.all()

  drivers = User.query.filter_by(role='driver').all()
  return render_template(
      'dashboard.html', orders=orders, drivers=drivers, search_query=search_query
  )


@app.route('/add_order', methods=['POST'])
@login_required
def add_order():
  if current_user.role not in ['admin', 'driver']:
    flash("Buyurtma qo'shish huquqingiz yo'q!", 'danger')
    return redirect(url_for('dashboard'))

  new_order = Order(
      client_name=request.form.get('client_name'),
      client_phone=request.form.get('client_phone'),
      address=request.form.get('address'),
      carpet_sqm=float(request.form.get('carpet_sqm') or 0),
      korpacha_count=int(request.form.get('korpacha_count') or 0),
      adyol_count=int(request.form.get('adyol_count') or 0),
      total_price=float(request.form.get('total_price') or 0),
      location_link=request.form.get('location_link'),  # Formadan saqlash
      driver_id=(
          int(request.form.get('driver_id'))
          if request.form.get('driver_id')
          else (current_user.id if current_user.role == 'driver' else None)
      ),
  )
  db.session.add(new_order)
  db.session.commit()
  flash('Buyurtma muvaffaqiyatli qoʻshildi!', 'success')
  return redirect(url_for('dashboard'))


@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
  order = Order.query.get_or_404(order_id)
  new_status = request.form.get('status')
  if new_status:
    order.status = new_status
    db.session.commit()
    flash('Buyurtma holati yangilandi!', 'success')
  return redirect(url_for('dashboard'))


@app.route('/update_location/<int:order_id>', methods=['POST'])
@login_required
def update_location(order_id):
  order = Order.query.get_or_404(order_id)
  link = request.form.get('location_link')
  if link:
    order.location_link = link
    db.session.commit()
    flash('Lokatsiya havolasi saqlandi!', 'success')
  return redirect(url_for('dashboard'))


@app.route('/delete_order/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
  if current_user.role != 'admin':
    flash("Faqat admin buyurtmani o'chira oladi!", 'danger')
    return redirect(url_for('dashboard'))

  order = Order.query.get_or_404(order_id)
  db.session.delete(order)
  db.session.commit()
  flash("Buyurtma o'chirib yuborildi!", 'success')
  return redirect(url_for('dashboard'))


@app.route('/users', methods=['GET', 'POST'])
@login_required
def manage_users():
  if current_user.role != 'admin':
    flash('Bu sahifaga faqat admin kira oladi!', 'danger')
    return redirect(url_for('dashboard'))

  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    role = request.form.get('role')

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
      flash(
          'Bu login bilan xodim allaqachon mavjud! Boshqa login tanlang.',
          'warning',
      )
      return redirect(url_for('manage_users'))

    if username and password and full_name:
      hashed_pw = generate_password_hash(password)
      new_user = User(
          full_name=full_name, username=username, password=hashed_pw, role=role
      )
      db.session.add(new_user)
      db.session.commit()
      flash('Yangi xodim muvaffaqiyatli qoʻshildi!', 'success')
      return redirect(url_for('manage_users'))
    else:
      flash('Barcha maydonlarni toʻldiring!', 'danger')

  users = User.query.all()
  return render_template('users.html', users=users)


# --- DASTURNI ISHGA TUSHIRISH ---
with app.app_context():
  db.create_all()
  if not User.query.filter_by(username='admin').first():
    admin_user = User(
        username='admin',
        password=generate_password_hash('admin123'),
        full_name='Korxona Rahbari',
        role='admin',
    )
    db.session.add(admin_user)
    db.session.commit()

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)