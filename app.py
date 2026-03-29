from pvc1 import get_ieema_df, calculate_single_record_from_dict
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# -------------------------
# 1. CREATE APP
# -------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'pvc-webapp-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pvc.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# -------------------------
# 2. INIT EXTENSIONS
# -------------------------
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -------------------------
# 3. MODELS
# -------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class PVCResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(80))
    item = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    basicrate = db.Column(db.Float)
    quantity = db.Column(db.Float)
    freight = db.Column(db.Float)
    pvcbasedate = db.Column(db.String(10))
    origdp = db.Column(db.String(10))
    refixeddp = db.Column(db.String(10))
    extendeddp = db.Column(db.String(10))
    caldate = db.Column(db.String(10))
    supdate = db.Column(db.String(10))
    rateapplied = db.Column(db.String(50))

    pvcactual = db.Column(db.Float)
    ldamtactual = db.Column(db.Float)
    fairprice = db.Column(db.Float)
    selectedscenario = db.Column(db.String(10))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------
# 4. LOAD DATA
# -------------------------
with app.app_context():
    ieema_df = get_ieema_df()

# -------------------------
# 5. ROUTES
# -------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password_hash, p):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    items = ['Transformer', 'IGBT Pulsation', 'Traction Motor', 'Shell']
    return render_template('index.html', items=items)

@app.route('/calculate', methods=['POST'])
@login_required
def calculate():
    data = {
        'user_id': current_user.id,
        'username': current_user.username,
        'item': request.form['item'],
        'basicrate': float(request.form.get('basicrate', 0) or 0),
        'quantity': float(request.form.get('quantity', 0) or 0),
        'freight': float(request.form.get('freight', 0) or 0),

        'pvcbasedate': request.form.get('pvcbasedate') or '',
        'origdp': request.form.get('origdp') or '',
        'refixeddp': request.form.get('refixeddp') or '',
        'extendeddp': request.form.get('extendeddp') or '',
        'caldate': request.form.get('caldate') or '',
        'supdate': request.form.get('supdate') or '',
        'rateapplied': request.form.get('rateapplied') or '',

        'lowerrate': float(request.form.get('lowerrate', 0) or 0),
        'lowerfreight': float(request.form.get('lowerfreight', 0) or 0),
        'lowerbasicdate': request.form.get('lowerbasicdate') or '',
    }

    one = {
        "acc_qty": data['quantity'],
        "basic_rate": data['basicrate'],
        "freight_rate_per_unit": data['freight'],
        "pvc_base_date": data['pvcbasedate'],
        "call_date": data['caldate'],
        "orig_dp": data['origdp'],
        "refixeddp": data['refixeddp'],
        "extendeddp": data['extendeddp'],
        "sup_date": data['supdate'],
        "lower_rate": data['lowerrate'],
        "lower_freight": data['lowerfreight'],
        "lower_basic_date": data['lowerbasicdate'],
    }

    result_row = calculate_single_record_from_dict(one, ieema_df)

    result = {
        "data": {
            "pvcactual": result_row["pvc_actual"],
            "ldamtactual": result_row["ld_amt_actual"],
            "fairprice": result_row["fair_price_new"],
            "selectedscenario": result_row["selected_scenario_new"],
        }
    }

    calc = PVCResult(
        user_id=data['user_id'],
        username=data['username'],
        item=data['item'],
        basicrate=data['basicrate'],
        quantity=data['quantity'],
        freight=data['freight'],
        pvcbasedate=data['pvcbasedate'],
        origdp=data['origdp'],
        refixeddp=data['refixeddp'],
        extendeddp=data['extendeddp'],
        caldate=data['caldate'],
        supdate=data['supdate'],
        rateapplied=data['rateapplied'],
        pvcactual=result["data"]["pvcactual"],
        ldamtactual=result["data"]["ldamtactual"],
        fairprice=result["data"]["fairprice"],
        selectedscenario=result["data"]["selectedscenario"],
    )

    db.session.add(calc)
    db.session.commit()

    return render_template(
        'result.html',
        item=data['item'],
        data=data,
        result=result,
        calc_id=calc.id
    )

# -------------------------
# 6. INIT DB (IMPORTANT FIX)
# -------------------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
