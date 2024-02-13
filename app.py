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
from sqlalchemy.orm import joinedload  # Import joinedload to load related accounts


app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.secret_key = "Tornsvalegatan1"
#det här är min master lösenord

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:golestan5@localhost:3307/torresbank"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


#skapa en instans av sqlalchemy som heter db
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
    
    # För att kunna visa varje kunds saldo
    @property
    def total_balance(self):
        total_balance = 0
        for account in self.accounts:
            # Calculate the balance based on transactions
            balance = account.balance
            for transaction in account.transactions:
                if transaction.transaction_type == 'Insättning':
                    balance += transaction.amount
                elif transaction.transaction_type == 'Uttag':
                    balance -= transaction.amount
            total_balance += balance
        return round(total_balance, 2)

    @total_balance.setter
    def total_balance(self, value):
        # This setter is needed to make the property writable
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
    balance = db.Column(db.Float)

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship('Customer', back_populates='accounts')

    transactions = db.relationship('Transaction', back_populates='account')


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
                continue  # Skip this iteration and generate a new customer

            personnummer = f.random_number(digits=10)
            address = f.address()
            city = f.city()

            person = Customer(namn=namn, email=email, personnummer=personnummer, address=address, city=city)

            # Add accounts to the customer
            for _ in range(random.randint(1, 3)):
                account_number = f.random_number(digits=15)

                account = Account(account_number=account_number)
                person.accounts.append(account)

                # Add initial deposit transaction with a fixed date
                initial_deposit = 5000.0
                initial_deposit_transaction = Transaction(
                    amount=initial_deposit,
                    transaction_type='Insättning',
                    timestamp=datetime(2017, 12, 15),
                    account=account  # Associate the transaction with the account
                )
                account.transactions.append(initial_deposit_transaction)

                # Set the initial balance based on the initial deposit
                account.balance = initial_deposit

                # Add random transactions to the account
                for _ in range(random.randint(5, 20)):
                    amount = round(random.uniform(-500, 500), 2)
                    transaction_type = 'Insättning' if amount > 0 else random.choice(['Uttag', 'Överföring'])
                    timestamp = f.date_time_this_decade()

                    transaction = Transaction(
                        amount=amount,
                        transaction_type=transaction_type,
                        timestamp=timestamp,
                        account=account  # Associate the transaction with the account
                    )

                    account.transactions.append(transaction)

                    # Update the account balance based on the transaction type
                    if transaction_type == 'Insättning':
                        account.balance += amount
                    elif transaction_type == 'Uttag':
                        account.balance -= amount

                db.session.add(account)

            db.session.add(person)
            db.session.commit()

            total_person += 1





@app.route("/login")
def index():
    total_customers = Customer.query.count()
    total_balance = db.session.query(db.func.round(db.func.sum(Account.balance), 2)).scalar() or 0
    total_accounts = Account.query.count()

    return render_template('index.html', total_customers=total_customers, total_balance=total_balance, total_accounts=total_accounts)


@app.route("/", methods=["GET", "POST"]) #första sidan när personalen kommer
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Admin.authenticate(username, password)

        if user:
            session["user_id"] = user.id  # Store user id in session for authentication
            return redirect(url_for("index"))  # Redirect to index page on successful login
        else:
            error_message = "DU har anget fel Username eller Password. Försök igen"
            return render_template("login.html", error_message=error_message)

    return render_template("login.html")

@app.route("/customers", strict_slashes=False)
def customers():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Order the customers by their ID in descending order
    customers_paginated = Customer.query.order_by(asc(Customer.id)).paginate(page=page, per_page=per_page)

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

    # Fetch the results along with the total balance for each customer
    results = query.paginate(page=page, per_page=per_page, error_out=False)
    for customer in results.items:
        total_balance = 0
        for account in customer.accounts:
            total_balance += account.balance
        customer.total_balance = total_balance

    return render_template("search.html", results=results, search_query=search_query, search_option=search_option)


@app.route('/accounttransactions/<account_id>', methods=['GET'])
def accounttransactions(account_id):
    account = Account.query.get(account_id)

    if account:
        # Calculate the total balance of the account
        total_balance = sum(transaction.amount for transaction in account.transactions)

        # Get the sorting order from the request
        order = request.args.get('order', 'desc')  # Set the default order to 'desc'

        # Determine the column to sort by and the order
        sort_column = Transaction.timestamp
        if order == 'asc':
            sort_column = sort_column.asc()
        else:
            sort_column = sort_column.desc()

        # Get the page from the request
        page = request.args.get('page', 1, type=int)

        # Set the number of transactions per page
        per_page = 10

        # Fetch the transactions, sorted accordingly and paginated
        transactions_paginated = Transaction.query \
            .filter_by(account_id=account.id) \
            .order_by(sort_column) \
            .paginate(page=page, per_page=per_page, error_out=False)

        return render_template('account_transactions.html', account=account, transactions_paginated=transactions_paginated, order=order, total_balance=total_balance)

    # If the account is not found, handle the error appropriately
    return redirect(url_for('search'))



if __name__ == "__main__":
    create_tables()
    seed_data(500)
    #500 kunder
    app.run(debug=True)
