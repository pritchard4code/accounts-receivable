import os
from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from flask_mail import Mail
from models import db, User
from config import config

mail = Mail()
login_manager = LoginManager()


def create_app(env=None):
    app = Flask(__name__)

    env = env or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config[env])

    db.init_app(app)
    mail.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # Register blueprints
    from ar.auth import auth_bp
    from ar.invoices import invoices_bp
    from ar.payments import payments_bp
    from ar.collections import collections_bp
    from ar.cash_app import cash_bp
    from ar.credit import credit_bp
    from ar.disputes import disputes_bp
    from ar.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(invoices_bp, url_prefix="/invoices")
    app.register_blueprint(payments_bp, url_prefix="/payments")
    app.register_blueprint(collections_bp, url_prefix="/collections")
    app.register_blueprint(cash_bp, url_prefix="/cash")
    app.register_blueprint(credit_bp, url_prefix="/credit")
    app.register_blueprint(disputes_bp, url_prefix="/disputes")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    @app.route("/")
    def index():
        return redirect(url_for("reports.dashboard"))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def _seed_default_data(app):
    from werkzeug.security import generate_password_hash
    from models import User, DunningRule, Customer
    from decimal import Decimal

    # Create admin user if none exist
    if User.query.count() == 0:
        admin = User(
            email="admin@company.com",
            password_hash=generate_password_hash("admin123"),
            full_name="System Administrator",
            role="admin",
        )
        db.session.add(admin)
        print("Created default admin user: admin@company.com / admin123")

    # Seed default dunning rules
    if DunningRule.query.count() == 0:
        rules = [
            DunningRule(name="Friendly Reminder", days_past_due=3,
                        template_name="dunning_reminder", sort_order=1),
            DunningRule(name="First Notice", days_past_due=10,
                        template_name="dunning_first_notice", sort_order=2),
            DunningRule(name="Second Notice + Late Fee", days_past_due=20,
                        template_name="dunning_second_notice", apply_late_fee=True, sort_order=3),
            DunningRule(name="Final Demand", days_past_due=45,
                        template_name="dunning_final_demand", sort_order=4),
        ]
        db.session.add_all(rules)
        print("Seeded default dunning rules.")

    # Seed sample customers
    if Customer.query.count() == 0:
        customers = [
            Customer(customer_number="CUST-001", company_name="Acme Corp",
                     contact_name="John Smith", email="john@acme.com",
                     credit_limit=Decimal("25000.00"), payment_terms_days=30),
            Customer(customer_number="CUST-002", company_name="Globex Industries",
                     contact_name="Jane Doe", email="jane@globex.com",
                     credit_limit=Decimal("50000.00"), payment_terms_days=45),
            Customer(customer_number="CUST-003", company_name="Initech LLC",
                     contact_name="Bob Johnson", email="bob@initech.com",
                     credit_limit=Decimal("10000.00"), payment_terms_days=30),
        ]
        db.session.add_all(customers)
        print("Seeded 3 sample customers.")

    db.session.commit()


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        _seed_default_data(app)
    app.run(debug=True, host="0.0.0.0", port=5000)
