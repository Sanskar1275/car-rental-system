from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas
from flask import send_file
import io
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST")
app.config['MYSQL_USER'] = os.getenv("MYSQL_USER")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB")

app.config['MYSQL_PORT'] = int(os.getenv("MYSQL_PORT"))

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['MYSQL_SSL'] = {
    "ca": os.path.join(BASE_DIR, "ca.pem")
}

mysql = MySQL(app)

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Upload Configuration

UPLOAD_FOLDER = 'static/uploads/vehicles'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def send_invoice_email(receiver_email, pdf_data, invoice_no):

    msg = EmailMessage()

    msg['Subject'] = f'Car Rental Invoice #{invoice_no}'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = receiver_email

    msg.set_content(
        """
Hello Customer,

Thank you for choosing our Car Rental System.

Your invoice PDF is attached.

Regards,
Car Rental System
        """
    )

    msg.add_attachment(
        pdf_data,
        maintype='application',
        subtype='pdf',
        filename=f'Invoice_{invoice_no}.pdf'
    )

    with smtplib.SMTP_SSL(
        'smtp.gmail.com',
        465
    ) as smtp:
    
        smtp.login(
            EMAIL_ADDRESS,
            EMAIL_PASSWORD
        )

        smtp.send_message(msg)
# ------------------------
# HOME
# ------------------------

@app.route('/')
def home():
    return redirect('/login')

# ------------------------
# LOGIN
# ------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cur.fetchone()

        cur.close()

        if user:

            stored_password = user[4]

            if check_password_hash(
                stored_password,
                password
            ):

                session['user_id'] = user[0]
                session['fullname'] = user[1]
                session['role'] = user[5]

                return redirect('/dashboard')

        flash("Invalid Email or Password")

    return render_template('login.html')

# ------------------------
# SIGNUP
# ------------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )
        
        existing = cur.fetchone()
        
        if existing:
            cur.close()
            flash("Email already registered")
            return redirect('/signup')

        mysql.connection.commit()
        cur.close()

        flash("Registration Successful")
        return redirect('/login')

    return render_template('signup.html')


# ------------------------


@app.route('/vehicles')
def vehicles():

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    search = request.args.get('search', '')

    status = request.args.get('status', '')

    cur.execute("""
    SELECT *
    FROM vehicles
    WHERE brand LIKE %s
    OR model LIKE %s
    OR vehicle_number LIKE %s
    """,
    (
    f"%{search}%",
    f"%{search}%",
    f"%{search}%"
    ))

    vehicles = cur.fetchall()

    cur.close()

    return render_template(
        'vehicles.html',
        vehicles=vehicles
    )

@app.route('/add_vehicle', methods=['GET', 'POST'])
def add_vehicle():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        brand = request.form['brand']
        model = request.form['model']
        vehicle_number = request.form['vehicle_number']
        year = request.form['year']
        fuel_type = request.form['fuel_type']
        transmission = request.form['transmission']
        seats = request.form['seats']
        price_per_day = request.form['price_per_day']
        status = request.form['status']

        image = request.files['image']

        filename = ''

        if image and image.filename != '':
            filename = secure_filename(image.filename)

            image.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO vehicles
            (
                brand,
                model,
                vehicle_number,
                year,
                fuel_type,
                transmission,
                seats,
                price_per_day,
                status,
                image
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            brand,
            model,
            vehicle_number,
            year,
            fuel_type,
            transmission,
            seats,
            price_per_day,
            status,
            filename
        ))

        mysql.connection.commit()

        cur.close()

        flash("Vehicle Added Successfully")

        return redirect('/vehicles')

    return render_template('add_vehicle.html')

@app.route('/delete_vehicle/<int:id>')
def delete_vehicle(id):

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute(
        "DELETE FROM vehicles WHERE vehicle_id=%s",
        (id,)
    )

    mysql.connection.commit()

    cur.close()

    flash("Vehicle Deleted Successfully")

    return redirect('/vehicles')

@app.route('/edit_vehicle/<int:id>',
           methods=['GET', 'POST'])
def edit_vehicle(id):

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        brand = request.form['brand']
        model = request.form['model']
        price_per_day = request.form['price_per_day']
        status = request.form['status']

        cur.execute("""
            UPDATE vehicles
            SET
                brand=%s,
                model=%s,
                price_per_day=%s,
                status=%s
            WHERE vehicle_id=%s
        """,
        (
            brand,
            model,
            price_per_day,
            status,
            id
        ))

        mysql.connection.commit()

        flash("Vehicle Updated Successfully")

        return redirect('/vehicles')

    cur.execute(
        "SELECT * FROM vehicles WHERE vehicle_id=%s",
        (id,)
    )

    vehicle = cur.fetchone()

    cur.close()

    return render_template(
        'edit_vehicle.html',
        vehicle=vehicle
    )

@app.route('/customers')
def customers():

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    search = request.args.get('search', '')

    cur.execute("""
    SELECT *
    FROM customers
    WHERE full_name LIKE %s
    OR phone LIKE %s
    OR license_number LIKE %s
    """,
    (
    f"%{search}%",
    f"%{search}%",
    f"%{search}%"
    ))

    customers = cur.fetchall()

    cur.close()

    return render_template(
        'customers.html',
        customers=customers
    )

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        license_number = request.form['license_number']
        address = request.form['address']

        cur = mysql.connection.cursor()

        cur.execute("""
        INSERT INTO customers
        (
            full_name,
            email,
            phone,
            license_number,
            address
        )
        VALUES(%s,%s,%s,%s,%s)
        """,
        (
            full_name,
            email,
            phone,
            license_number,
            address
        ))

        mysql.connection.commit()
        cur.close()

        flash("Customer Added Successfully")

        return redirect('/customers')

    return render_template('add_customer.html')

@app.route('/edit_customer/<int:id>',
methods=['GET', 'POST'])
def edit_customer(id):

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        license_number = request.form['license_number']
        address = request.form['address']

        cur.execute("""
        UPDATE customers
        SET
        full_name=%s,
        email=%s,
        phone=%s,
        license_number=%s,
        address=%s
        WHERE customer_id=%s
        """,
        (
        full_name,
        email,
        phone,
        license_number,
        address,
        id
        ))

        mysql.connection.commit()

        return redirect('/customers')

    cur.execute(
    "SELECT * FROM customers WHERE customer_id=%s",
    (id,)
    )

    customer = cur.fetchone()

    cur.close()

    return render_template(
    'edit_customer.html',
    customer=customer
    )

@app.route('/delete_customer/<int:id>')
def delete_customer(id):

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute(
    "DELETE FROM customers WHERE customer_id=%s",
    (id,)
    )

    mysql.connection.commit()

    cur.close()

    flash("Customer Deleted")

    return redirect('/customers')

@app.route('/rentals')
def rentals():

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    status = request.args.get('status', '')

    query = """
    SELECT
        rentals.rental_id,
        customers.full_name,
        vehicles.brand,
        vehicles.model,
        rentals.pickup_date,
        rentals.return_date,
        rentals.total_days,
        rentals.total_amount,
        rentals.rental_status
    FROM rentals
    JOIN customers
    ON rentals.customer_id = customers.customer_id
    JOIN vehicles
    ON rentals.vehicle_id = vehicles.vehicle_id
    """

    if status:
        query += " WHERE rentals.rental_status=%s"
        cur.execute(query,(status,))
    else:
        cur.execute(query)

    rentals_data = cur.fetchall()

    cur.close()

    return render_template(
        'rentals.html',
        rentals=rentals_data
    )

@app.route('/add_rental', methods=['GET', 'POST'])
def add_rental():

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        customer_id = request.form['customer_id']
        vehicle_id = request.form['vehicle_id']

        pickup_date = request.form['pickup_date']
        return_date = request.form['return_date']

        from datetime import datetime

        start = datetime.strptime(
            pickup_date,
            "%Y-%m-%d"
        )

        end = datetime.strptime(
            return_date,
            "%Y-%m-%d"
        )
        if end < start:
            flash("Return date cannot be before pickup date")
            return redirect('/add_rental')
        
        total_days = max(1, (end - start).days)
    
        cur.execute(
            "SELECT price_per_day FROM vehicles WHERE vehicle_id=%s",
            (vehicle_id,)
        )

        vehicle = cur.fetchone()

        rent_per_day = vehicle[0]

        total_amount = total_days * float(rent_per_day)

        cur.execute("""
        INSERT INTO rentals
        (
            customer_id,
            vehicle_id,
            pickup_date,
            return_date,
            total_days,
            rent_per_day,
            total_amount
        )
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            customer_id,
            vehicle_id,
            pickup_date,
            return_date,
            total_days,
            rent_per_day,
            total_amount
        ))

        cur.execute("""
            UPDATE vehicles
            SET status='Booked'
            WHERE vehicle_id=%s
        """, (vehicle_id,))

        mysql.connection.commit()

        flash("Rental Created Successfully")

        return redirect('/rentals')

    cur.execute(
        "SELECT customer_id, full_name FROM customers"
    )

    customers = cur.fetchall()

    cur.execute("""
    SELECT vehicle_id, brand, model
    FROM vehicles
    WHERE status='Available'
    """)

    vehicles = cur.fetchall()

    cur.close()

    return render_template(
        'add_rental.html',
        customers=customers,
        vehicles=vehicles
    )

@app.route('/bills')
def bills():

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    search = request.args.get('search','')

    cur.execute("""
    SELECT
        bills.bill_id,
        customers.full_name,
        vehicles.brand,
        vehicles.model,
        rentals.total_amount,
        bills.gst_amount,
        bills.final_amount,
        bills.payment_status
    
    FROM bills
    
    JOIN rentals
    ON bills.rental_id = rentals.rental_id
    
    JOIN customers
    ON rentals.customer_id = customers.customer_id
    
    JOIN vehicles
    ON rentals.vehicle_id = vehicles.vehicle_id
    
    WHERE customers.full_name LIKE %s
    """,
    (
    f"%{search}%",
    ))

    bills_data = cur.fetchall()

    print(bills_data)

    cur.close()

    return render_template(
        'bills.html',
        bills=bills_data
    )

@app.route('/generate_bill/<int:rental_id>')
def generate_bill(rental_id):

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()
 
    cur.execute(
        "SELECT bill_id FROM bills WHERE rental_id=%s",
        (rental_id,)
    )

    existing_bill = cur.fetchone()

    if existing_bill:
        flash("Bill already exists")
        cur.close()
        return redirect('/bills')

    cur.execute("""
    SELECT total_amount,rental_status
    FROM rentals
    WHERE rental_id=%s
    """,(rental_id,))

    rental = cur.fetchone()

    if not rental:
        flash("Rental not found")
        cur.close()
        return redirect('/rentals')

    subtotal = float(rental[0])

    rental_status = rental[1]

    if rental_status == "Completed":
        payment_status = "Paid"
    else:
        payment_status = "Pending"
        
    gst = subtotal * 0.18

    final_amount = subtotal + gst

    cur.execute("""
    INSERT INTO bills
    (
        rental_id,
        gst_amount,
        final_amount,
        payment_method,
        payment_status
    )
    VALUES(%s,%s,%s,%s,%s)
    """,
    (
        rental_id,
        gst,
        final_amount,
        'Cash',
        payment_status
    ))

    mysql.connection.commit()
    cur.close()

    flash("Bill Generated")

    return redirect('/bills')

@app.route('/invoice/<int:bill_id>')
def invoice(bill_id):

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT
        bills.bill_id,
        customers.full_name,
        customers.phone,
        customers.email,
        vehicles.brand,
        vehicles.model,
        vehicles.vehicle_number,
        rentals.total_amount,
        bills.gst_amount,
        bills.final_amount,
        bills.payment_status,
        bills.bill_date

    FROM bills

    JOIN rentals
        ON bills.rental_id = rentals.rental_id

    JOIN customers
        ON rentals.customer_id = customers.customer_id

    JOIN vehicles
        ON rentals.vehicle_id = vehicles.vehicle_id

    WHERE bills.bill_id=%s
    """, (bill_id,))

    bill = cur.fetchone()
    cur.close()

    if not bill:
        flash("Invoice not found")
        return redirect('/bills')

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setTitle("Rental Invoice")

    # =====================
    # OUTER BORDER
    # =====================

    pdf.rect(20, 20, 555, 800)

    # =====================
    # HEADER
    # =====================

    pdf.setFillColorRGB(0.18, 0.37, 0.78)
    pdf.rect(20, 770, 555, 50, fill=1)

    pdf.setFillColorRGB(1,1,1)
    pdf.setFont("Helvetica-Bold",22)
    pdf.drawCentredString(297,790,"CAR RENTAL SYSTEM")

    pdf.setFont("Helvetica",10)
    pdf.drawCentredString(
        297,
        775,
        "Vehicle Rental & Billing Management"
    )

    # =====================
    # INVOICE INFO
    # =====================

    pdf.setFillColorRGB(0.95,0.95,0.95)
    pdf.rect(40,700,500,40,fill=1)

    pdf.setFillColorRGB(0,0,0)
    pdf.setFont("Helvetica-Bold",11)

    pdf.drawString(
        60,
        715,
        f"Invoice No : INV-{bill[0]}"
    )

    pdf.drawRightString(
        520,
        715,
        f"Date : {bill[11]}"
    )

    # =====================
    # CUSTOMER DETAILS
    # =====================

    pdf.setFont("Helvetica-Bold",14)
    pdf.drawString(40,670,"CUSTOMER DETAILS")

    pdf.rect(40,560,500,95)

    pdf.setFont("Helvetica",11)

    pdf.drawString(60, 630, f"Customer  : {bill[1]}")
    pdf.drawString(60, 610, f"Mobile No : {bill[2]}")
    pdf.drawString(60, 590, f"Vehicle   : {bill[4]} {bill[5]}")
    pdf.drawString(60, 570, f"Vehicle No: {bill[6]}")

    # =====================
    # BILLING DETAILS
    # =====================

    pdf.setFont("Helvetica-Bold",14)
    pdf.drawString(40,530,"BILLING DETAILS")

    # Table Header

    pdf.setFillColorRGB(0.18,0.37,0.78)
    pdf.rect(40,490,500,30,fill=1)

    pdf.setFillColorRGB(1,1,1)

    pdf.drawString(80,500,"Description")
    pdf.drawString(400,500,"Amount")

    # Table Body

    pdf.setFillColorRGB(1,1,1)

    pdf.rect(40,410,500,80)

    pdf.line(360,410,360,520)
    pdf.line(40,450,540,450)

    pdf.setFillColorRGB(0,0,0)

    pdf.setFont("Helvetica",11)

    pdf.drawString(
        80,
        465,
        "Rent Amount"
    )

    pdf.drawString(
        400,
        465,
        f"Rs. {bill[7]}"
    )

    pdf.drawString(
        80,
        425,
        "GST (18%)"
    )

    pdf.drawString(
        400,
        425,
        f"Rs. {bill[8]}"
    )

    # =====================
    # GRAND TOTAL
    # =====================

    pdf.setFillColorRGB(
        0.88,
        0.95,
        0.88
    )

    pdf.rect(
        40,
        340,
        500,
        45,
        fill=1
    )

    pdf.setFillColorRGB(
        0,
        0.55,
        0
    )

    pdf.setFont(
        "Helvetica-Bold",
        15
    )

    pdf.drawString(
        60,
        357,
        "Grand Total"
    )

    pdf.drawString(
        390,
        357,
        f"Rs. {bill[9]}"
    )

    # =====================
    # PAYMENT STATUS
    # =====================

    pdf.rect(
        40,
        280,
        500,
        40
    )

    if bill[10] == "Paid":
        pdf.setFillColorRGB(0,0.6,0)
    else:
        pdf.setFillColorRGB(0.8,0,0)

    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        60,
        295,
        f"Payment Status : {bill[10]}"
    )

    # =====================
    # NOTES
    # =====================

    pdf.setFillColorRGB(0,0,0)

    pdf.setFont(
        "Helvetica-Bold",
        11
    )

    pdf.drawString(
        40,
        240,
        "Notes"
    )

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawString(
        60,
        220,
        "• GST included as per government regulations."
    )

    pdf.drawString(
        60,
        200,
        "• Keep this invoice for future reference."
    )

    pdf.drawString(
        60,
        180,
        "• Contact support for any billing issues."
    )

    # =====================
    # SIGNATURE
    # =====================

    pdf.line(
        380,
        120,
        520,
        120
    )

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawString(
        405,
        105,
        "Authorized Signature"
    )

    # =====================
    # FOOTER
    # =====================

    pdf.setFont(
        "Helvetica-Oblique",
        9
    )

    pdf.drawCentredString(
        297,
        60,
        "Thank you for choosing Car Rental System"
    )

    pdf.drawCentredString(
        297,
        45,
        "This is a computer generated invoice"
    )

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"invoice_{bill_id}.pdf",
        mimetype='application/pdf'
    )

@app.route('/send_invoice/<int:bill_id>')
def send_invoice(bill_id):

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT
        bills.bill_id,
        customers.full_name,
        customers.phone,
        customers.email,
        vehicles.brand,
        vehicles.model,
        vehicles.vehicle_number,
        rentals.total_amount,
        bills.gst_amount,
        bills.final_amount,
        bills.payment_status,
        bills.bill_date

    FROM bills

    JOIN rentals
        ON bills.rental_id = rentals.rental_id

    JOIN customers
        ON rentals.customer_id = customers.customer_id

    JOIN vehicles
        ON rentals.vehicle_id = vehicles.vehicle_id

    WHERE bills.bill_id=%s
    """,(bill_id,))

    bill = cur.fetchone()

    cur.close()

    if not bill:

        flash("Bill not found")

        return redirect('/bills')
    
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setTitle("Rental Invoice")

    # =====================
    # OUTER BORDER
    # =====================

    pdf.rect(20, 20, 555, 800)

    # =====================
    # HEADER
    # =====================

    pdf.setFillColorRGB(0.18, 0.37, 0.78)
    pdf.rect(20, 770, 555, 50, fill=1)

    pdf.setFillColorRGB(1,1,1)
    pdf.setFont("Helvetica-Bold",22)
    pdf.drawCentredString(297,790,"CAR RENTAL SYSTEM")

    pdf.setFont("Helvetica",10)
    pdf.drawCentredString(
        297,
        775,
        "Vehicle Rental & Billing Management"
    )

    # =====================
    # INVOICE INFO
    # =====================

    pdf.setFillColorRGB(0.95,0.95,0.95)
    pdf.rect(40,700,500,40,fill=1)

    pdf.setFillColorRGB(0,0,0)
    pdf.setFont("Helvetica-Bold",11)

    pdf.drawString(
        60,
        715,
        f"Invoice No : INV-{bill[0]}"
    )

    pdf.drawRightString(
        520,
        715,
        f"Date : {bill[11]}"
    )

    # =====================
    # CUSTOMER DETAILS
    # =====================

    pdf.setFont("Helvetica-Bold",14)
    pdf.drawString(40,670,"CUSTOMER DETAILS")

    pdf.rect(40,560,500,95)

    pdf.setFont("Helvetica",11)

    pdf.drawString(60, 630, f"Customer  : {bill[1]}")
    pdf.drawString(60, 610, f"Mobile No : {bill[2]}")
    pdf.drawString(60, 590, f"Vehicle   : {bill[4]} {bill[5]}")
    pdf.drawString(60, 570, f"Vehicle No: {bill[6]}")

    # =====================
    # BILLING DETAILS
    # =====================

    pdf.setFont("Helvetica-Bold",14)
    pdf.drawString(40,530,"BILLING DETAILS")

    # Table Header

    pdf.setFillColorRGB(0.18,0.37,0.78)
    pdf.rect(40,490,500,30,fill=1)

    pdf.setFillColorRGB(1,1,1)

    pdf.drawString(80,500,"Description")
    pdf.drawString(400,500,"Amount")

    # Table Body

    pdf.setFillColorRGB(1,1,1)

    pdf.rect(40,410,500,80)

    pdf.line(360,410,360,520)
    pdf.line(40,450,540,450)

    pdf.setFillColorRGB(0,0,0)

    pdf.setFont("Helvetica",11)

    pdf.drawString(
        80,
        465,
        "Rent Amount"
    )

    pdf.drawString(
        400,
        465,
        f"Rs. {bill[7]}"
    )

    pdf.drawString(
        80,
        425,
        "GST (18%)"
    )

    pdf.drawString(
        400,
        425,
        f"Rs. {bill[8]}"
    )

    # =====================
    # GRAND TOTAL
    # =====================

    pdf.setFillColorRGB(
        0.88,
        0.95,
        0.88
    )

    pdf.rect(
        40,
        340,
        500,
        45,
        fill=1
    )

    pdf.setFillColorRGB(
        0,
        0.55,
        0
    )

    pdf.setFont(
        "Helvetica-Bold",
        15
    )

    pdf.drawString(
        60,
        357,
        "Grand Total"
    )

    pdf.drawString(
        390,
        357,
        f"Rs. {bill[9]}"
    )

    # =====================
    # PAYMENT STATUS
    # =====================

    pdf.rect(
        40,
        280,
        500,
        40
    )

    if bill[10] == "Paid":
        pdf.setFillColorRGB(0,0.6,0)
    else:
        pdf.setFillColorRGB(0.8,0,0)

    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        60,
        295,
        f"Payment Status : {bill[10]}"
    )

    # =====================
    # NOTES
    # =====================

    pdf.setFillColorRGB(0,0,0)

    pdf.setFont(
        "Helvetica-Bold",
        11
    )

    pdf.drawString(
        40,
        240,
        "Notes"
    )

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawString(
        60,
        220,
        "• GST included as per government regulations."
    )

    pdf.drawString(
        60,
        200,
        "• Keep this invoice for future reference."
    )

    pdf.drawString(
        60,
        180,
        "• Contact support for any billing issues."
    )

    # =====================
    # SIGNATURE
    # =====================

    pdf.line(
        380,
        120,
        520,
        120
    )

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawString(
        405,
        105,
        "Authorized Signature"
    )

    # =====================
    # FOOTER
    # =====================

    pdf.setFont(
        "Helvetica-Oblique",
        9
    )

    pdf.drawCentredString(
        297,
        60,
        "Thank you for choosing Car Rental System"
    )

    pdf.drawCentredString(
        297,
        45,
        "This is a computer generated invoice"
    )

    pdf.save()

    buffer.seek(0)

    pdf_data = buffer.getvalue()

    send_invoice_email(
        bill[3],      # customer email
        pdf_data,
        bill[0]
    )

    flash("Invoice emailed successfully")

    return redirect('/bills')


@app.route('/complete_rental/<int:id>')
def complete_rental(id):

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT vehicle_id
        FROM rentals
        WHERE rental_id=%s
    """, (id,))

    vehicle = cur.fetchone()

    if vehicle:

        vehicle_id = vehicle[0]

        cur.execute("""
            UPDATE rentals
            SET rental_status='Completed'
            WHERE rental_id=%s
        """, (id,))

        cur.execute("""
            UPDATE bills
            SET payment_status='Paid'
            WHERE rental_id=%s
        """, (id,))

        cur.execute("""
            UPDATE vehicles
            SET status='Available'
            WHERE vehicle_id=%s
        """, (vehicle_id,))

        mysql.connection.commit()

    cur.close()

    return redirect('/rentals')

@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM vehicles")
    total_vehicles = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM customers")
    total_customers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM rentals")
    total_rentals = cur.fetchone()[0]

    cur.execute("""
    SELECT IFNULL(SUM(final_amount),0)
    FROM bills
    WHERE payment_status='Paid'
    """)

    revenue = cur.fetchone()[0]

    cur.close()

    return render_template(
    'dashboard.html',
    name=session['fullname'],
    total_vehicles=total_vehicles,
    total_customers=total_customers,
    total_rentals=total_rentals,
    revenue=revenue
    )
    
@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('login'))

if __name__ == "__main__":
    import webbrowser

    # webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True)
