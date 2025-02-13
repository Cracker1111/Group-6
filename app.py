import os
from flask import Flask, render_template, request, redirect, url_for, flash, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from flask_wtf.file import FileField
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, current_user, UserMixin

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Folder where images will be saved
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rice_shop.db'  # SQLite database for simplicity
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Define the login route for redirects

# Define database models
class Farmer(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    rice_products = db.relationship('RiceProduct', backref='farmer', lazy=True)
    qr_code = db.Column(db.String(100), nullable=True) 

class RiceProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(100), nullable=True)  # Add image column to store filename
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmer.id'), nullable=False)

# Forms for handling user input
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('farmer', 'Farmer'), ('buyer', 'Buyer')], validators=[DataRequired()])
    submit = SubmitField('Register')

class SellRiceForm(FlaskForm):
    name = StringField('Rice Name', validators=[DataRequired()])
    description = StringField('Description')
    price = StringField('Price', validators=[DataRequired()])
    quantity = StringField('Quantity', validators=[DataRequired()])
    image = FileField('Upload Rice Image')  # Add file upload field
    submit = SubmitField('Sell Rice')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Flask-Login requires a user loader to load the user from the database
@login_manager.user_loader
def load_user(user_id):
    return Farmer.query.get(int(user_id))


# Routes for pages
@app.route('/')
def index():
    products = RiceProduct.query.all()
    return render_template('index.html', products=products)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        farmer = Farmer.query.filter_by(username=form.username.data).first()
        if farmer and check_password_hash(farmer.password, form.password.data):  # Note: use proper password hashing
            login_user(farmer)  # Log the user in
            flash('Logged in successfully!')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)


# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     form = RegisterForm()
#     if form.validate_on_submit():
#         farmer = Farmer(
#             username=form.username.data, 
#             password=form.password.data, 
#             role=form.role.data  # Save the selected role
#         )
#         db.session.add(farmer)
#         db.session.commit()
#         flash('Registered successfully!')
#         return redirect(url_for('login'))  # Redirect to login page
#     return render_template('register.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if username is already taken
        user_exists = Farmer.query.filter_by(username=form.username.data).first()
        if user_exists:
            flash('Username already exists. Please choose another.', 'error')
            return redirect(url_for('register'))
        
        # Create a new farmer user
        hashed_password = generate_password_hash(form.password.data)  # Hash password before saving
        farmer = Farmer(
            username=form.username.data, 
            password=hashed_password, 
            role=form.role.data  # Save the selected role
        )
        db.session.add(farmer)
        db.session.commit()
        flash('Registered successfully!')
        return redirect(url_for('login'))  # Redirect to login page
    return render_template('register.html', form=form)


@app.route('/sell_rice', methods=['GET', 'POST'])
@login_required  # Ensure only logged-in users can access this page
def sell_rice():
    if current_user.role != 'farmer':  # Check if the logged-in user is a farmer
        flash('You must be a farmer to sell rice.')
        return redirect(url_for('index'))
    
    form = SellRiceForm()
    if form.validate_on_submit():
        # Handle image upload
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.image.data.save(filepath)
        else:
            filename = None
        
        rice = RiceProduct(
            name=form.name.data, 
            description=form.description.data, 
            price=form.price.data, 
            quantity=form.quantity.data, 
            image=filename,  # Save the image filename
            farmer_id=current_user.id  # Use the logged-in farmer's ID
        )
        db.session.add(rice)
        db.session.commit()
        flash('Rice product added!')
        return redirect(url_for('index'))
    return render_template('sell_rice.html', form=form)


@app.route('/product/<int:id>')
def product_details(id):
    product = RiceProduct.query.get_or_404(id)
    return render_template('product_details.html', product=product)

# @app.route('/profile')
# @login_required
# def profile():
#     # Display only rice products added by the logged-in farmer
#     if current_user.role == 'farmer':
#         products = RiceProduct.query.filter_by(farmer_id=current_user.id).all()
#         return render_template('profile.html', products=products)
#     else:
#         flash('Only farmers can view this page.')
#         return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    if current_user.role != 'farmer':
        flash('You must be a farmer to view this page.')
        return redirect(url_for('index'))
    products = RiceProduct.query.filter_by(farmer_id=current_user.id).all()
    return render_template('profile.html', products=products)



# @app.route('/buy_now/<int:id>')
# @login_required
# def buy_now(id):
#     if current_user.role != 'buyer':
#         flash('Only buyers can make purchases.')
#         return redirect(url_for('index'))
    
#     # Redirect to payment page (for now, it's just a placeholder)
#     return render_template('payment_page.html', product_id=id)

@app.route('/buy_now/<int:id>')
@login_required
def buy_now(id):
    if current_user.role != 'buyer':
        flash('Only buyers can make purchases.')
        return redirect(url_for('index'))

    # Get the product from the database
    product = RiceProduct.query.get_or_404(id)

    # Get the farmer who is selling this product
    farmer = Farmer.query.get_or_404(product.farmer_id)

    # Fetch the farmer's QR code (assume the QR code filename is stored in the Farmer table)
    farmer_qr_code = farmer.qr_code  # Assuming this field is present in the Farmer model

    # Render the payment page, passing the product and farmer's QR code
    return render_template('payment_page.html', product=product, farmer_qr_code=farmer_qr_code)

def generate_qr_code(farmer_id):
    qr = qrcode.make(f"payment_info_for_farmer_{farmer_id}")  # Some unique information for the farmer
    qr_filename = f"farmer_{farmer_id}_qr.png"
    qr_path = os.path.join(current_app.config['UPLOAD_FOLDER'], qr_filename)
    qr.save(qr_path)
    return qr_filename

# Main block
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This will create the database tables
    app.run(debug=True, port=5001)

