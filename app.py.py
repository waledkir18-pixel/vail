from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'njom_secret_key_2026'

# إعداد مسار حفظ الصور المرفوعة
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'store.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# الامتدادات المسموحة للصور
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# جدول المستخدمين
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='customer')

# جدول العبايات المعروضة (مع خانة الصورة)
class Abaya(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    catalog = db.Column(db.String(50), nullable=False, default='عام')
    discount = db.Column(db.Integer, default=0)
    image_file = db.Column(db.String(200), default='default.jpg') # اسم ملف الصورة

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('shop'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        
        if phone == '0500000000' and password == 'admin123':
            session['user_id'] = 999
            session['user_name'] = 'المسؤول'
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
            
        user = User.query.filter_by(phone=phone, password=password).first()
        if user:
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['role'] = 'customer'
            return redirect(url_for('shop'))
        else:
            flash('عذراً، رقم الجوال أو كلمة السر غير صحيحة.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        phone = request.form['phone']
        age = request.form['age']
        email = request.form['email']
        password = request.form['password']
        
        existing_user = User.query.filter((User.phone == phone) | (User.email == email)).first()
        if existing_user:
            flash('رقم الجوال أو البريد الإلكتروني مسجل مسبقاً!', 'error')
            return redirect(url_for('register'))
            
        new_user = User(full_name=full_name, phone=phone, age=age, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('تم إنشاء حسابكِ بنجاح! يمكنكِ الآن تسجيل الدخول.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/shop')
def shop():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    abayas = Abaya.query.all()
    catalogs = db.session.query(Abaya.catalog).distinct().all()
    catalogs_list = [c[0] for c in catalogs] if catalogs else ['عام']
    
    selected_catalog = request.args.get('catalog', 'الكل')
    if selected_catalog != 'الكل':
        abayas = Abaya.query.filter_by(catalog=selected_catalog).all()
        
    return render_template('shop.html', user_name=session.get('user_name'), abayas=abayas, catalogs=catalogs_list, selected_catalog=selected_catalog)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form['title']
        details = request.form['details']
        price = request.form['price']
        catalog = request.form['catalog']
        discount = request.form.get('discount', 0)
        
        # معالجة رفع الصورة
        filename = 'default.jpg'
        if 'abaya_image' in request.files:
            file = request.files['abaya_image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_abaya = Abaya(
            title=title, 
            details=details, 
            price=float(price), 
            catalog=catalog, 
            discount=int(discount) if discount else 0,
            image_file=filename
        )
        db.session.add(new_abaya)
        db.session.commit()
        flash('تم إضافة العباية بالصورة وتحديث الكتالوج بنجاح!')
        return redirect(url_for('admin_dashboard'))
        
    abayas = Abaya.query.all()
    customers = User.query.filter_by(role='customer').all()
    return render_template('admin.html', abayas=abayas, customers=customers)

@app.route('/admin/delete/<int:id>')
def delete_abaya(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    abaya = Abaya.query.get(id)
    if abaya:
        # حذف ملف الصورة من المجلد إذا لم تكن الصورة الافتراضية
        if abaya.image_file != 'default.jpg':
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], abaya.image_file))
            except:
                pass
        db.session.delete(abaya)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # إنشاء مجلدات قاعدة البيانات والصور تلقائياً لو مو موجودة
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)