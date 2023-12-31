from flask import Flask, render_template, url_for, request, redirect, flash, session, jsonify
from flask_login import UserMixin, login_user, login_required, logout_user, current_user, LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.secret_key = "5473895728547392"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return UserCredentials.query.get(int(id))
 
class UserCredentials(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

    client = db.relationship('ClientInformation')
    quotes = db.relationship('FuelQuote')

class ClientInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullName = db.Column(db.String(50))
    addressOne = db.Column(db.String(100))
    addressTwo = db.Column(db.String(100))
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    zipcode = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey(UserCredentials.id))

class FuelQuote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gallons = db.Column(db.Float)
    addressOne = db.Column(db.String(100))
    addressTwo = db.Column(db.String(100))
    deliveryDate = db.Column(db.String(10))
    pricePerGallon = db.Column(db.Float)
    totalAmountDue = db.Column(db.Float)

    user = db.relationship('UserCredentials', back_populates='quotes')

    user_id = db.Column(db.Integer, db.ForeignKey(UserCredentials.id))

class PricingModule:
    def __init__(self):
        self.refinery_price = 1.5
        self.quote_id = 1
        self.quote_history = []
    
    def get_margin(self, gallons, state, has_history):
        location_factor = 0.02 if state == 'TX' else 0.04
        history_factor = 0.01 if has_history else 0.00
        gallons_factor = 0.02 if gallons > 1000 else 0.03
        profit_factor = 0.1

        margin = self.refinery_price * (location_factor - history_factor + gallons_factor + profit_factor)

        return margin
    
    def get_price_per_gallon(self, gallons, state, has_history):
        margin = self.get_margin(gallons, state, has_history)
        price_per_gallon = self.refinery_price + margin

        return price_per_gallon
    
    def update_quote_history(self, quote_details):
        quote_details['quote_id'] = self.quote_id
        self.quote_id += 1
        self.quote_history.append(quote_details)

pricing_module = PricingModule()

@app.route('/')
def index():
    return render_template('index.html', user=current_user)

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = UserCredentials.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            flash('Login successful.', category='success')
            login_user(user)
            
            return redirect(url_for('index'))
        elif user and not check_password_hash(user.password, password):
            flash('Incorrect password.', category='error')
        else:
            flash('Username does not exist.', category="error")
    
    return render_template('login.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully signed out!', category='success')
    
    return redirect(url_for('index'))

@app.route('/profile', methods = ['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        fullName = request.form.get('fullName')
        addressOne = request.form.get('addressOne')
        addressTwo = request.form.get('addressTwo')
        city = request.form.get('city')
        state = request.form.get('state')
        zipcode = request.form.get('zipcode')

        if len(fullName) <= 0:
            flash('Full Name must be at least 1 character long.', category='error')
        elif len(fullName) > 50:
            flash('Full Name can be at most 50 characters long.', category='error')
        elif len(addressOne) <= 0:
            flash('Address 1 must be at least 1 character long.', category='error')
        elif len(addressOne) > 100:
            flash('Address 1 can be at most 100 characters long.', category='error')
        elif len(addressTwo) > 100:
            flash('Address 2 can be at most 100 characters long.', category='error')
        elif len(city) > 100:
            flash('City can be at most 100 characters long.', category='error')
        elif len(zipcode) < 5:
            flash('Zipcode must be at least 5 digits long.', category='error')
        elif len(zipcode) > 9:
            flash('Zipcode can be at most 9 digits long.', category='error')
        else:
            client = ClientInformation.query.filter_by(user_id=current_user.id).first()
            if client:
                client.fullName = fullName
                client.addressOne = addressOne
                client.addressTwo = addressTwo
                client.city = city
                client.state = state
                client.zipcode = zipcode
            else:
                new_clientInfo = ClientInformation(fullName=fullName,
                                                   addressOne=addressOne,
                                                   addressTwo=addressTwo,
                                                   city=city,
                                                   state=state,
                                                   zipcode=zipcode,
                                                   user_id=current_user.id)
                db.session.add(new_clientInfo)
                
            db.session.commit()
            flash('Updated profile.', category='success')
    
    return render_template('profile.html', user=current_user)

@app.route('/sign_up', methods = ['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = UserCredentials.query.filter_by(username = username).first()
        if user:
            flash("Username already exists.", category='error')
        elif len(username) < 1:
            flash('Please enter a username.', category='error')
        elif len(password) < 1:
                flash('Please enter a password.', category='error')
        else:
            new_user = UserCredentials(username=username,
                                       password = generate_password_hash(password, method ='scrypt'))
            
            db.session.add(new_user)
            db.session.commit()
            flash('Registration complete.', category='success')
            
            return redirect(url_for('login'))
        
    return render_template('sign_up.html', user=current_user)

@app.route('/quote', methods = ['GET', 'POST'])
@login_required
def quote():
    client = ClientInformation.query.filter_by(user_id=current_user.id).first()
    if not client:
        flash('Please complete profile before getting a quote.', category='error')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        gallons = float(request.form.get('gallons'))
        delivery_date = request.form.get('deliveryDate')

        has_history = bool(current_user.quotes)
        margin = pricing_module.get_margin(gallons, client.state, has_history)
        price_per_gallon = pricing_module.get_price_per_gallon(gallons, client.state, has_history)

        total_amount_due = gallons * price_per_gallon

        if gallons <= 0:
            flash('Please enter a valid number of gallons.', category='error')
        if delivery_date == '':
            flash('Please enter a delivery date.', category='error')
        else:
            new_quote = FuelQuote(gallons=gallons,
                                  addressOne=client.addressOne,
                                  addressTwo=client.addressTwo,
                                  deliveryDate=delivery_date,
                                  pricePerGallon=price_per_gallon,
                                  totalAmountDue=total_amount_due,
                                  user_id=current_user.id)
            
            db.session.add(new_quote)
            db.session.commit()

            flash('Form complete.', category='success')

    return render_template('quote.html',
                           addressOne=client.addressOne,
                           addressTwo=client.addressTwo,
                           user=current_user)

@app.route('/history')
@login_required
def history():
    quote_history = FuelQuote.query.filter_by(user_id=current_user.id).order_by(FuelQuote.deliveryDate).all()
    return render_template('history.html',
                           user=current_user,
                           quote_history=quote_history)

@app.route('/get_quote', methods=['POST'])
@login_required
def get_quote():
    gallons = float(request.form.get('gallons'))

    client = ClientInformation.query.filter_by(user_id=current_user.id).first()
    if client:
        has_history = bool(current_user.quotes)
        price_per_gallon = pricing_module.get_price_per_gallon(gallons, client.state, has_history)
        total_amount_due = gallons * price_per_gallon
        return jsonify({'pricePerGallon': price_per_gallon, 'totalAmountDue': total_amount_due})
    else:
        return jsonify({'error': 'Client information not found'}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 