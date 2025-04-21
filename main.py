from flask import Flask, render_template, redirect, url_for, request, jsonify, g
import mysql.connector
import hashlib
import jwt
import datetime
import logging  # new import
from auth import auth_required
from db_connection import get_db_connection
from AddUser import add_user_bp
from flask_cors import CORS
from StudentSignup import student_signup_bp
from VisitorSignup import visitor_signup_bp
from WardenAPI import warden_bp
from AddStudent import add_student_bp
from datetime import datetime, timedelta, timezone



# Configure logging: prints to console and writes to server.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log")
    ]
)

app = Flask(_name_)
CORS(app)
app.config['SECRET_KEY'] = 'CS432_SECRET'  # Replace with an environment variable in production

app.register_blueprint(add_user_bp)
app.register_blueprint(student_signup_bp)
app.register_blueprint(visitor_signup_bp)
app.register_blueprint(warden_bp)
app.register_blueprint(add_student_bp)

# ------------------ Authentication Routes ------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_admin', methods=['POST'])
def add_admin():
    data = request.get_json()

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    username = email.split("@")[0]
    hashed_pw = hashlib.md5(password.encode()).hexdigest()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into members table
        cursor.execute("INSERT INTO cs432cims.members (userName, emailID, DoB) VALUES (%s, %s, NULL)", (username, email))
        member_id = cursor.lastrowid

        # Insert into login table
        cursor.execute("INSERT INTO cs432cims.Login (MemberID, Password, Role) VALUES (%s, %s, 'admin')", (member_id, hashed_pw))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Admin added successfully!", "member_id": member_id}), 200

    except mysql.connector.IntegrityError:
        return jsonify({"error": f"Username '{username}' already exists."}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/select_role')
def select_role():
    return render_template('select_role.html')

@app.route('/student_login')
def student_login():
    return render_template('student_login.html')

@app.route('/warden_login')
def warden_login():
    return render_template('warden_login.html')

@app.route('/visitor_login')
def visitor_login():
    return render_template('visitor_login.html')

@app.route('/student_signup')
def student_signup():
    return render_template('student_signup.html')

@app.route('/visitor_signup')
def visitor_signup():
    return render_template('visitor_signup.html')


@app.route('/student_dashboard')
@auth_required(app)
def student_dashboard():
    # Fetch the student ID from g (which should now have member_id)
    student_id = g.member_id  # This should work after the successful login

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Query to fetch student details
    cursor.execute("""
        SELECT student_id, name, age, email, contact_no, Room_ID, Hostel_ID
        FROM cs432g4.student
        WHERE student_id = %s
    """, (student_id,))

    student_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if student_data:
        return render_template("student_dashboard.html", student=student_data)
    else:
        return jsonify({"error": "Student not found"}), 404


# ------------------ Visitor Dashboard ------------------
@app.route('/visitor_dashboard')
@auth_required(app)
def visitor_dashboard():
    """
    Visitor landing page.
    Expects:
        - g.member_id populated by auth_required
    Renders:
        - dashboardVisitor.html  (template expects a `visitor` dictionary)
    """
    member_id = g.member_id                           # From validated JWT
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Pull visitor record + name of the student they’re visiting (if any)
    cursor.execute("""
        SELECT  v.visitor_id,
                v.name,
                v.contact,
                v.in_time,
                v.out_time,
                s.name AS student_name
        FROM    cs432g4.visitors v
        LEFT JOIN cs432g4.student s
               ON v.student_id = s.student_id
        WHERE   v.visitor_id = %s
    """, (member_id,))
    visitor_data = cursor.fetchone()

    cursor.close()
    conn.close()

    if visitor_data:
        return render_template("dashboardVisitor.html", visitor=visitor_data)
    else:
        # Record not found → clean JSON error
        return jsonify({"error": "Visitor not found"}), 404

@app.route('/register_complaint')
@auth_required(app)
def register_complaint():
    # Code for the complaint registration page
    return render_template("complaint.html")

@app.route('/make_payment')
@auth_required(app)
def make_payment():
    # Code for the payment page
    return render_template("payment.html")

@app.route('/submit_payment', methods=['POST'])
@auth_required(app)  # Ensure that the user is logged in
def submit_payment():
    payment_id = request.form.get('payment_id')
    sender = request.form.get('sender')
    receiver = request.form.get('receiver')
    date = request.form.get('date')

    if not all([payment_id, sender, receiver, date]):
        return jsonify({"error": "All fields are required."}), 400

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insert data into Payments table
        insert_sql = """
            INSERT INTO cs432cims.Payments (TransactionID, Sender, Receiver, Date)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_sql, (payment_id, sender, receiver, date))
        conn.commit()

        return jsonify({"message": "Payment submitted successfully!"}), 200

    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": str(err)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/student_logout')
def student_logout():
    # Code for logging out the student
    resp = redirect(url_for('student_login'))
    resp.delete_cookie('token')  # deletes JWT token
    return resp


@app.route('/warden-dashboard')
@auth_required(app)
def warden_dashboard():
    member_id = g.member_id

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cs432g4.warden WHERE warden_id = %s", (member_id,))
    warden_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not warden_data:
        return render_template("warden_dashboard.html", warden={ "warden_id": member_id, "name": "N/A", "contact": "-", "email": "-", "hostel_name": "-" })

    # add placeholder if hostel_name isn't in table
    warden_data.setdefault("hostel_name", "Not Assigned")
    return render_template("warden_dashboard.html", warden=warden_data)

@app.route('/add_room', methods=['GET', 'POST'])
@auth_required(app)
def add_room():
    if request.method == 'GET':
        # Extract warden's hostel ID
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT hostel_id FROM cs432g4.hostel WHERE Warden_ID = %s", (g.member_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "No hostel assigned to this warden"}), 404

        hostel_id = result['hostel_id']

        cursor.close()
        conn.close()

        hostel_id = result['hostel_id'] if result else ""
        return render_template("add_room.html", hostel_id=hostel_id)

    elif request.method == 'POST':
        data = request.get_json()
        room_id = data.get("room_id")
        room_type = data.get("room_type")
        status = data.get("status")
        hostel_id = data.get("hostel_id")

        # Validate inputs
        if not room_id or not hostel_id or not room_type or not status:
            return jsonify({"error": "Missing required fields"}), 400
        if not (room_id.isdigit() and len(room_id) == 3):
            return jsonify({"error": "Room ID must be a 3-digit number"}), 400
        if not (str(hostel_id).isdigit() and 1 <= int(hostel_id) <= 12):
            return jsonify({"error": "Hostel ID must be between 1 and 12"}), 400

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Check for existing room (room_id + hostel_id composite key)
            cursor.execute("SELECT * FROM cs432g4.room WHERE room_id = %s AND Hostel_ID = %s", (room_id, hostel_id))
            existing = cursor.fetchone()
            if existing:
                return jsonify({"error": "Room already exists for this hostel"}), 409

            # Insert into table
            insert_sql = """
                INSERT INTO cs432g4.room (room_id, room_type, status, Hostel_ID)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (room_id, room_type.lower(), status.lower(), hostel_id))
            conn.commit()

        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 500
        finally:
            cursor.close()
            conn.close()

        return jsonify({"message": "Room added successfully!"}), 200

@app.route('/add_item', methods=['GET', 'POST'])
@auth_required(app)
def add_item():
    if request.method == 'GET':
        # Get the hostel_id of this logged-in warden
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT hostel_id FROM cs432g4.hostel WHERE Warden_ID = %s", (g.member_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            return render_template("add_item.html", error="No hostel assigned to this warden.")

        hostel_id = result['hostel_id']
        return render_template("add_item.html", hostel_id=hostel_id)

    elif request.method == 'POST':
        item_name = request.form.get('item_name')
        quantity = request.form.get('quantity')
        i_condition = request.form.get('i_condition')

        # Fetch hostel ID again for POST
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT hostel_id FROM cs432g4.hostel WHERE Warden_ID = %s", (g.member_id,))
        result = cursor.fetchone()

        if not result:
            return render_template("add_item.html", error="Hostel not found for warden.")

        hostel_id = result['hostel_id']

        # Validate fields
        if not all([item_name, quantity, i_condition]):
            return render_template("add_item.html", error="All fields are required.", hostel_id=hostel_id)

        if not quantity.isdigit() or not (1 <= int(quantity) <= 500):
            return render_template("add_item.html", error="Quantity must be between 1 and 500.", hostel_id=hostel_id)

        try:
            cursor.execute("""
                INSERT INTO cs432g4.inventory (item_name, quantity, i_condition, Hostel_ID)
                VALUES (%s, %s, %s, %s)
            """, (item_name.strip(), int(quantity), i_condition, hostel_id))
            conn.commit()
            return render_template("add_item.html", success="Item added successfully!", hostel_id=hostel_id)

        except mysql.connector.Error as err:
            conn.rollback()
            return render_template("add_item.html", error=str(err), hostel_id=hostel_id)
        finally:
            cursor.close()
            conn.close()



@app.route('/delete_item', methods=['GET', 'POST'])
@auth_required(app)
def delete_item():
    if request.method == 'GET':
        return render_template("delete_item.html")

    elif request.method == 'POST':
        item_id = request.form.get("item_id")

        if not item_id or not item_id.isdigit():
            return render_template("delete_item.html", error="Invalid item ID")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if item exists
            cursor.execute("SELECT * FROM cs432g4.inventory WHERE item_id = %s", (item_id,))
            item = cursor.fetchone()

            if not item:
                return render_template("delete_item.html", error="Item ID does not exist.")

            # Delete item
            cursor.execute("DELETE FROM cs432g4.inventory WHERE item_id = %s", (item_id,))
            conn.commit()

        except mysql.connector.Error as err:
            return render_template("delete_item.html", error=f"Database error: {err}")
        finally:
            cursor.close()
            conn.close()

        return render_template("delete_item.html", success="Item deleted successfully!")

@app.route('/view_all_rooms')
@auth_required(app)
def view_all_rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # If you want to filter by hostel of the logged-in warden:
    cursor.execute("""
        SELECT r.room_id, r.room_type, r.status, r.Hostel_ID
        FROM cs432g4.room r
        JOIN cs432g4.hostel h ON r.Hostel_ID = h.hostel_id
        WHERE h.Warden_ID = %s
    """, (g.member_id,))
    
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template("view_all_rooms.html", rooms=rooms)


@app.route('/manage_inventory')
@auth_required(app)
def manage_inventory():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT item_id, item_name, quantity, i_condition FROM cs432g4.inventory ORDER BY item_id ASC")
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("manage_inventory.html", items=items)

@app.route('/view_complaints')
@auth_required(app)
def view_complaints():
    # Get the logged-in warden's ID from the auth decorator (g.member_id)
    warden_id = g.member_id

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # First, retrieve the hostel_id for the warden
    cursor.execute("SELECT hostel_id FROM cs432g4.hostel WHERE Warden_ID = %s", (warden_id,))
    result = cursor.fetchone()
    if result:
        hostel_id = result['hostel_id']
    else:
        # If no hostel is assigned, return an appropriate message or empty list
        hostel_id = None

    complaints = []
    if hostel_id:
        # Use a join between complaints and student table to filter by hostel.
        query = """
            SELECT c.complaint_no, c.Student_ID, c.category, c.status, c.complaint_date
            FROM cs432g4.complaints c
            JOIN cs432g4.student s ON c.Student_ID = s.student_id
            WHERE s.Hostel_ID = %s
            ORDER BY c.complaint_date DESC
        """
        cursor.execute(query, (hostel_id,))
        complaints = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template("view_complaints.html", complaints=complaints)





@app.route('/logout')
def logout():
    resp = redirect(url_for('warden_login'))
    resp.delete_cookie('token')  # deletes JWT token
    return resp

#warden
@app.route('/view_students')
@auth_required(app)
def view_students_page():  # Renamed to avoid conflict
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cs432g4.student")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("view_students.html", students=students)


# -------- Admin Dashboard and Pages --------
@app.route('/dashboardAdmin')
@auth_required(app)
def dashboard_admin():
    return render_template('dashboardAdmin.html')


@app.route('/add_item_admin')
@auth_required(app)
def add_item_admin():
    return render_template('add_item_admin.html')

@app.route('/view_room_admin')
@auth_required(app)
def view_room_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cs432g4.room ORDER BY Hostel_ID, room_id")
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("view_room_admin.html", rooms=rooms)




@app.route('/add_warden')
@auth_required(app)
def add_warden():
    return render_template('add_warden.html')

@app.route('/delete_item_admin')
@auth_required(app)
def delete_item_admin():
    return render_template('delete_item_admin.html')

@app.route('/delete_student')
@auth_required(app)
def delete_student():
    return render_template('delete_student.html')

@app.route('/delete_warden')
@auth_required(app)
def delete_warden():
    return render_template('delete_warden.html')

@app.route('/manage_inventory_admin')
@auth_required(app)
def manage_inventory_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Fetch all inventory items; this query does not filter by warden so it returns data for all hostels.
    cursor.execute("SELECT item_id, item_name, quantity, i_condition, Hostel_ID FROM cs432g4.inventory ORDER BY item_id ASC")

    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("manage_inventory_admin.html", items=items)


@app.route('/view_complaints_admin')
@auth_required(app)
def view_complaints_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Fetch all complaints irrespective of hostel, ordering by date (latest first)
    cursor.execute("""
        SELECT complaint_no, Student_ID, category, status, complaint_date 
        FROM cs432g4.complaints 
        ORDER BY complaint_date DESC
    """)
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("view_complaints_admin.html", complaints=complaints)


@app.route('/view_students')
@auth_required(app)
def view_students():
    return render_template('view_students.html')


@app.route('/view_wardens')
@auth_required(app)
def view_wardens():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Join warden table with hostel to fetch hostel_id
    cursor.execute("""
        SELECT w.warden_id, w.name, w.contact, w.email, h.hostel_id
        FROM cs432g4.warden w
        LEFT JOIN cs432g4.hostel h ON w.warden_id = h.Warden_ID
    """)
    
    wardens = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("view_wardens.html", wardens=wardens)

@app.route('/view_visitors')
@auth_required(app)
def view_visitors():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT visitor_id, name, contact, in_time, out_time, student_id
        FROM cs432g4.visitors
    """)
    visitors = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("view_visitors.html", visitors=visitors)










from flask import g, jsonify, redirect, url_for
import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from db_connection import get_db_connection

@app.route('/authUser', methods=['POST'])
def auth_user():
    # Accept either JSON or form data.
    data = request.get_json() if request.is_json else request.form

    member_id = data.get('MemberID')
    password = data.get('Password')
    role_sent = data.get('Role')  # Make sure the login form sends a hidden field Role = "student"
    
    if not member_id or not password:
        return jsonify({"error": "Missing MemberID or Password"}), 400

    hashed_pw = hashlib.md5(password.encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Login WHERE MemberID = %s", (member_id,))
    user = cursor.fetchone()

    if user and user['Password'] == hashed_pw:
        # Role validation: ensure that the role coming in matches the user role in the database
        if user['Role'] != role_sent:
            cursor.close()
            conn.close()
            return jsonify({"error": "Unauthorized role login"}), 403

        # Set member_id in g to make it accessible in other routes
        g.member_id = member_id  # Store member_id in g

        # Generate token
        token = jwt.encode({
            "MemberID": member_id,
            "Role": user["Role"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        expiry_time = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())

        cursor.execute("UPDATE Login SET Session = %s, Expiry = %s WHERE MemberID = %s",
                       (token, expiry_time, member_id))
        conn.commit()
        cursor.close()
        conn.close()

        # Instead of returning JSON, redirect to the appropriate dashboard
        if user['Role'] == 'student':
            response = redirect(url_for("student_dashboard"))
        elif user['Role'] == 'visitor':
            response = redirect(url_for("visitor_dashboard"))
        elif user['Role'] == 'warden':
            response = redirect(url_for("warden_dashboard"))
        elif user['Role'] == 'admin':
            response = redirect(url_for("dashboard_admin"))
        else:
            return jsonify({"error": "Unknown role"}), 403

        response.set_cookie("token", token)  # Set the token in the cookie
        return response

    else:
        cursor.close()
        conn.close()
        return jsonify({"error": "Invalid credentials"}), 401






# ------------------ Example Route (Token Check) ------------------
@app.route('/example', methods=['GET'])
@auth_required(app)
def example():
    return jsonify({"message": f"Hello {g.member_id}, your role is {g.role}."})

@app.route('/assignGroup', methods=['POST'])
@auth_required(app)
def assign_group():
    data = request.json
    member_id = data.get('MemberID')
    group_id = data.get('GroupID')

    if not member_id or not group_id:
        return jsonify({"error": "MemberID and GroupID required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if MemberID exists
    cursor.execute("SELECT 1 FROM members WHERE ID = %s", (member_id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        return jsonify({"error": f"Member {member_id} does not exist"}), 404

    # Proceed to insert into mapping
    cursor.execute("INSERT INTO MemberGroupMapping (MemberID, GroupID) VALUES (%s, %s)",
                   (member_id, group_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": f"Member {member_id} assigned to group {group_id}."}), 200

# ------------------ Member Deletion Routes ------------------
@app.route('/member/<int:member_id>', methods=['GET'])
@auth_required(app)
def check_member(member_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM members WHERE ID = %s", (member_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        return jsonify({"member": result}), 200
    else:
        return jsonify({"message": f"Member {member_id} not found."}), 404






@app.route('/deleteMember/<member_id>', methods=['DELETE'])
@auth_required(app)
def delete_member(member_id):
    group_name = 'cs432g4'  # your group name
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check how many groups this member is in
    cursor.execute("SELECT COUNT(*) FROM MemberGroupMapping WHERE MemberID = %s", (member_id,))
    count = cursor.fetchone()[0]

    if count > 1:
        # Just remove the mapping for cs432g4
        cursor.execute("DELETE FROM MemberGroupMapping WHERE MemberID = %s AND GroupName = %s", (member_id, group_name))
        msg = f"Removed group mapping for {group_name}, member still exists in other groups."
    else:
        # Fully delete member from all relevant tables
        cursor.execute("DELETE FROM MemberGroupMapping WHERE MemberID = %s", (member_id,))
        cursor.execute("DELETE FROM Login WHERE MemberID = %s", (member_id,))
        cursor.execute("DELETE FROM members WHERE ID = %s", (member_id,))
        msg = f"Member {member_id} fully deleted."

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": msg}), 200

# ------------------ Run App ------------------
if _name_ == '_main_':
    app.run(debug=True)
