from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy,pagination
from sqlalchemy import or_,func
from faker import Faker
import random
from flask_session import Session
from flask_paginate import Pagination
#func för varje konto att se deras saldo
from sqlalchemy.sql import func
from datetime import datetime
from sqlalchemy import asc
from sqlalchemy.orm import joinedload
app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.secret_key = "Tornsvalegatan1"

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:golestan5@localhost:3307/torresbank"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    namn = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    personnummer = db.Column(db.String(10), unique=True)
    address = db.Column(db.String(255))
    city = db.Column(db.String(255))

    accounts = db.relationship('Account', back_populates='customer')

    def __repr__(self):
        return f"<Customer {self.namn} - Email: {self.email}>"

    @property
    def total_balance(self):
        total_balance = 0
        for account in self.accounts:
            total_balance += account.calculate_balance()
        return round(total_balance, 2)

    @total_balance.setter
    def total_balance(self, value):
        pass

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    namn = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)

    @classmethod
    def authenticate(cls, username, password):
        return cls.query.filter_by(username=username, password=password).first()

class Account(db.Model):
    __tablename__ = 'account'
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(15), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship('Customer', back_populates='accounts')
    transactions = db.relationship('Transaction', back_populates='account')

    def calculate_balance(self):
        balance = 0
        for transaction in self.transactions:
            balance += transaction.amount
        return balance

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    transaction_type = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    account = db.relationship('Account', back_populates='transactions')

def create_tables():
    with app.app_context():
        db.create_all()

def seed_data(total: int) -> None:
    with app.app_context():
        f = Faker('sv_SE')

        admin_details = [
            {"namn": "Stefan Holmberg", "email": "stefan.holmberg@systementor.se", "username": "Admin",
             "password": "Hejsan123#"},
            {"namn": "Sebastian Mentor", "email": "stefan.holmberg@nackademin.se", "username": "Cashier",
             "password": "Hejsan123#"},
            {"namn": "Mohammad Rahimi", "email": "m.rahimi.vasteras@gmail.com", "username": "Boss",
             "password": "Hejsan123#"},
        ]

        for admin_detail in admin_details:
            existing_admin = Admin.query.filter(Admin.email.ilike(admin_detail["email"])).first()

            if existing_admin:
                existing_admin.namn = admin_detail["namn"]
                existing_admin.username = admin_detail["username"]
                existing_admin.password = admin_detail["password"]
            else:
                admin = Admin(**admin_detail)
                db.session.add(admin)

            db.session.commit()

        total_person = Customer.query.count()

        while total_person < total:
            namn = f.name()
            email = f.email()

            existing_customer = Customer.query.filter_by(email=email).first()
            if existing_customer:
                continue

            personnummer = f.random_number(digits=10)
            address = f.address()
            city = f.city()

            person = Customer(namn=namn, email=email, personnummer=personnummer, address=address, city=city)

            for _ in range(random.randint(1, 3)):
                account_number = f.random_number(digits=15)
                account = Account(account_number=account_number)
                person.accounts.append(account)

                initial_deposit = 5000.0
                initial_deposit_transaction = Transaction(
                    amount=initial_deposit,
                    transaction_type='Insättning',
                    timestamp=datetime(2017, 12, 15),
                    account=account
                )
                account.transactions.append(initial_deposit_transaction)

                for _ in range(random.randint(5, 20)):
                    amount = round(random.uniform(-500, 500), 2)
                    transaction_type = 'Insättning' if amount > 0 else random.choice(['Uttag', 'Överföring'])
                    timestamp = f.date_time_this_decade()

                    transaction = Transaction(
                        amount=amount,
                        transaction_type=transaction_type,
                        timestamp=timestamp,
                        account=account
                    )

                    account.transactions.append(transaction)

                db.session.add(account)

            db.session.add(person)
            db.session.commit()

            total_person += 1

@app.route("/login")
def index():
    total_customers = Customer.query.count()
    total_accounts = Account.query.count()
    total_balance = db.session.query(func.round(func.sum(Transaction.amount), 2)).scalar() or 0

    return render_template('index.html', total_customers=total_customers, total_accounts=total_accounts, total_balance=total_balance)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = Admin.authenticate(username, password)
        if user:
            session["user_id"] = user.id
            return redirect(url_for("index"))
        else:
            error_message = "DU har anget fel Username eller Password. Försök igen"
            return render_template("login.html", error_message=error_message)
    return render_template("login.html")

@app.route("/customers", strict_slashes=False)
def customers():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    customers_paginated = Customer.query.order_by(Customer.id.asc()).paginate(page=page, per_page=per_page)
    return render_template("customers.html", customers_paginated=customers_paginated)

@app.route("/template")
def template():
    return render_template("template.html")

from sqlalchemy import or_

@app.route("/search", methods=["GET"])
def search():
    search_query = request.args.get("search_query")
    page = request.args.get('page', 1, type=int)
    per_page = 7 
    search_option = request.args.get('search_option', 'id') 

    try:
        if search_query is not None:
            search_query_int = int(search_query)
        else:
            search_query_int = None
    except ValueError:
        search_query_int = None

    search_option_filters = {
        'id': Customer.id == search_query_int,
        'personnummer': Customer.personnummer.like(f"%{search_query}%"),
        'city': Customer.city.like(f"%{search_query}%"),
        'name': Customer.namn.like(f"%{search_query}%"),
    }

    query = Customer.query.filter(search_option_filters.get(search_option, False))

    results = query.paginate(page=page, per_page=per_page, error_out=False)
    for customer in results.items:
        total_balance = 0
        for account in customer.accounts:
            total_balance += account.calculate_balance()
        customer.total_balance = total_balance

    return render_template("search.html", results=results, search_query=search_query, search_option=search_option)

@app.route('/accounttransactions/<account_id>', methods=['GET'])
def accounttransactions(account_id):
    account = Account.query.get(account_id)
    if account:
        total_balance = account.calculate_balance()
        order = request.args.get('order', 'desc')
        sort_column = Transaction.timestamp
        if order == 'asc':
            sort_column = sort_column.asc()
        else:
            sort_column = sort_column.desc()
        page = request.args.get('page', 1, type=int)
        per_page = 10
        transactions_paginated = Transaction.query.filter_by(account_id=account.id).order_by(sort_column).paginate(page=page, per_page=per_page, error_out=False)
        return render_template('account_transactions.html', account=account, transactions_paginated=transactions_paginated, order=order, total_balance=total_balance)
    return redirect(url_for('search'))

@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if request.method == "POST":
        account_number = request.form.get("account_number")
        deposit_amount = float(request.form.get("deposit_amount"))

        account = Account.query.filter_by(account_number=account_number).first()

        if not account:
            error_message = "Account not found. Please enter a valid account number."
            return render_template("deposit.html", error_message=error_message)

        if deposit_amount <= 0:
            error_message = "Invalid deposit amount. Please enter a positive number."
            return render_template("deposit.html", error_message=error_message)

        #räkna saldo efter VARJE transaction
        account_balance = sum(transaction.amount for transaction in account.transactions)

        account_balance += deposit_amount

        deposit_transaction = Transaction(
            amount=deposit_amount,
            transaction_type='Insättning',
            timestamp=datetime.now(),
            account=account
        )
        db.session.add(deposit_transaction)
        db.session.commit()

        return render_template("deposit_success.html", account=account, deposit_amount=deposit_amount, deposit_transaction=deposit_transaction, account_balance=account_balance)

    return render_template("deposit.html")

@app.route("/withdrawal", methods=["GET", "POST"])
def withdrawal():
    if request.method == "POST":
        account_number = request.form.get("account_number")
        withdrawal_amount = float(request.form.get("withdrawal_amount"))

        account = Account.query.filter_by(account_number=account_number).first()

        if not account:
            error_message = "Kontot hittades inte. Vänligen försök igen"
            return render_template("uttag.html", error_message=error_message)

        if withdrawal_amount <= 0:
            error_message = "Ogiltigt belopp. Försök igen"
            return render_template("uttag.html", error_message=error_message)

        #räknar RIKTIGA saldo
        current_balance = sum(transaction.amount for transaction in account.transactions)

        if withdrawal_amount > current_balance:
            error_message = "Det finns inte tillräckligt pengar på kontot."
            return render_template("uttag.html", error_message=error_message)

        withdrawal_transaction = Transaction(
            amount=-withdrawal_amount,  #GLÖM ej att ha minus värde
            transaction_type='Uttag',
            timestamp=datetime.now(),
            account=account
        )
        db.session.add(withdrawal_transaction)
        db.session.commit()

        new_balance = current_balance - withdrawal_amount

        return render_template("uttag_success.html", account=account, withdrawal_amount=withdrawal_amount, withdrawal_transaction=withdrawal_transaction, account_balance=new_balance)

    return render_template("uttag.html")

@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    if request.method == "POST":
        from_account_number = request.form.get("from_account_number")
        to_account_number = request.form.get("to_account_number")
        transfer_amount = float(request.form.get("transfer_amount"))

        from_account = Account.query.filter_by(account_number=from_account_number).first()
        to_account = Account.query.filter_by(account_number=to_account_number).first()

        if not from_account or not to_account:
            error_message = "Ett av kontona hittades inte. Vänligen försök igen"
            return render_template("transfer.html", error_message=error_message)

        if transfer_amount <= 0:
            error_message = "Ogiltigt överföringsbelopp. Vänligen försök igen"
            return render_template("transfer.html", error_message=error_message)

        from_account_balance = sum(transaction.amount for transaction in from_account.transactions)

        if transfer_amount > from_account_balance:
            error_message = "Det finns inte tillräckligt pengar på avsändarkontot."
            return render_template("transfer.html", error_message=error_message)

        from_transfer_transaction = Transaction(
            amount=-transfer_amount,  # Negativs värde
            transaction_type='Överföring',
            timestamp=datetime.now(),
            account=from_account
        )

        to_transfer_transaction = Transaction(
            amount=transfer_amount, 
            transaction_type='Överföring',
            timestamp=datetime.now(),
            account=to_account
        )

        db.session.add(from_transfer_transaction)
        db.session.add(to_transfer_transaction)
        db.session.commit()

        new_from_account_balance = from_account_balance - transfer_amount

        return render_template("transfer_success.html", from_account=from_account, to_account=to_account, transfer_amount=transfer_amount, from_transfer_transaction=from_transfer_transaction, to_transfer_transaction=to_transfer_transaction, from_account_balance=new_from_account_balance)

    return render_template("transfer.html")

if __name__ == "__main__":
    create_tables()
    seed_data(500)
    app.run(debug=True)
