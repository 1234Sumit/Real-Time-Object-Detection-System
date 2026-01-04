from flask import Flask, render_template, flash, redirect, url_for, session, request,Response,jsonify # type: ignore
from flask_sqlalchemy import SQLAlchemy # type: ignore

from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
# from index import d_dtcn
import cv2 # type: ignore

from ultralytics import YOLO # type: ignore

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

model=YOLO("model/yolov8m.pt")
camera=None


## 

detection_active = False
# Constants for distance estimation
KNOWN_WIDTH = 0.5  # meters (approximate width of known object)
FOCAL_LENGTH = 600  # depends on your camera, can be calibrated

# For storing object data
detected_objects = []

def estimate_distance(pixel_width):
    if pixel_width == 0:
        return 0
    return (KNOWN_WIDTH * FOCAL_LENGTH) / pixel_width

def generate_frames():
    global detected_objects, camera, detection_active

    camera = cv2.VideoCapture(0)
    while detection_active:
        success, frame = camera.read()
        if not success:
            break

        results = model(frame)[0]
        detected = []

        for box in results.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = box
            if score < 0.3:
                continue

            label_name = model.names[int(class_id)]
            pixel_width = x2 - x1
            distance = estimate_distance(pixel_width)
            confidence = float(score)

            label = f"{label_name} {confidence:.2f} {distance:.2f}m"

            detected.append({
                "label": label_name,
                "confidence": round(confidence, 2),
                "distance_m": round(distance, 2)
            })

            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0,255,0), 2)
            cv2.putText(frame, label, (int(x1), int(y1)-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

        detected_objects = detected
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    if camera:
        camera.release()


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    uname = db.Column(db.String(20), unique=True, nullable=False)
    lname = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    date = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(20), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
   
    pass1 = db.Column(db.String(60), nullable=False)

# admin database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)



# models.py
class Medical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uname = db.Column(db.String(255))  # Add this line
    address = db.Column(db.String(255))
    allergies = db.Column(db.String(255))
    visionstatus = db.Column(db.String(255))
    medications = db.Column(db.String(255))
    surgeries = db.Column(db.String(255))
    bloodgroup = db.Column(db.String(255))
    age = db.Column(db.String(255))
    chronic_conditions = db.Column(db.String(255))
    emergency_contact = db.Column(db.String(20))
    blood_pressure = db.Column(db.String(15))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        pass1 = request.form['pass1']
        user = Users.query.filter_by(phone=phone).first()
        if user and check_password_hash(user.pass1, pass1):
            flash('Login successful!', 'success')
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            flash('Login failed. Check your email and password.', 'danger')
    return render_template('login.html')

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        uname = request.form['uname']
        lname = request.form['lname']
        email = request.form['email']
        date = request.form['date']
        address = request.form['address']
        phone = request.form['phone']
        pass1 = request.form['pass1']
        pass2 = request.form['pass2']

        if pass1 == pass2:
            hashed_password = generate_password_hash(pass1)
            new_user = Users(username=username,uname=uname,lname=lname, email=email,date=date,address=address,phone=phone, pass1=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match.', 'danger')

    return render_template('user_registration.html')

@app.route('/logout/')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('base'))




@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    user = Users.query.get_or_404(id)
    if request.method == 'POST':
        # Update user
        user.username = request.form['username']
        user.uname = request.form['uname']
        user.lname = request.form['lname']
        user.email = request.form['email']
        user.date = request.form['date']
        user.address = request.form['address']
        user.phone = request.form['phone']
        user.pass1 = request.form['pass1']

        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('users'))
    else:
        return render_template('edit_user.html', user=user)
    

# @app.route("/doctorinfo")
# def doctor():
#     return render_template("doctorinfo.html")
@app.route('/users/delete/<int:id>', methods=['POST'])
def delete_user(id):
    user = Users.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('users'))


@app.route("/home",methods=['GET', 'POST'])
def home():
    print(request.method)
    if request.method == 'POST':
        if request.form.get('Continue') == 'Continue':
           return render_template("test1.html")
    else:
        # pass # unknown
        return render_template("index.html")



@app.route("/")
def base():
    return render_template("base.html")


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            flash('Login successful!', 'success')
            session['user_id'] = user.id
            return redirect(url_for('admin_home'))
        else:
            flash('Login failed. Check your email and password.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin_register/', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password == confirm_password:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('admin_login'))
        else:
            flash('Passwords do not match.', 'danger')

    return render_template('admin_register.html')

@app.route('/admin_logout/')
def admin_logout():
    session.pop('user_id', None)
    return redirect(url_for('base'))


@app.route("/admin_home")
def admin_home():
    return render_template("admin_home.html")



@app.route("/view_user")
def view_user():
    users = Users.query.all()
    return render_template('view_user.html', users=users)


@app.route('/medical_info/', methods=['GET', 'POST'])
def medical_info():
    if request.method == 'POST':
        uname = request.form['uname']
        address = request.form['address']
        allergies = request.form['allergies']
        visionstatus = request.form['visionstatus']
        medications = request.form['medications']
        surgeries = request.form['surgeries']
        bloodgroup = request.form['bloodgroup']
        age = request.form['age']
        chronic_conditions = request.form['chronic_conditions']
        emergency_contact = request.form['emergency_contact']
        blood_pressure = request.form['blood_pressure']

        # Get the user ID from the session
        user_id = session.get('user_id')

        # Check if the user is logged in
        if user_id:
            # Create a UserMedical instance
            medical_info = Medical(
                user_id=user_id,  # Assuming you have a 'user_id' column in UserMedical
                uname=uname,
                address=address,
                allergies=allergies,
                visionstatus=visionstatus,
                medications=medications,
                surgeries=surgeries,
                bloodgroup=bloodgroup,
                age=age,
                chronic_conditions=chronic_conditions,
                emergency_contact=emergency_contact,
                blood_pressure=blood_pressure
            )

            # Add and commit the medical_info to the database
            db.session.add(medical_info)
            db.session.commit()

            return redirect(url_for('home'))  # Redirect to home page after submission

    return render_template("add_medical.html")


@app.route("/view_medical")
def view_medical():
    user_medical_info = Medical.query.all()
    return render_template('view_medical.html', user_medical_info=user_medical_info)

@app.route('/update_medical/<int:id>', methods=['GET', 'POST'])
def update_medical(id):
    medical_info = Medical.query.get(id)

    if request.method == 'POST':
        # Update medical_info attributes based on the form data
        medical_info.allergies = request.form['allergies']
        medical_info.medications = request.form['medications']
        # Update other attributes as needed

        # Commit the changes to the database
        db.session.commit()

        return redirect(url_for('view_medical'))

    return render_template('update_medical.html', medical_info=medical_info)



# Route for deleting medical information
@app.route('/delete_medical/<int:id>')
def delete_medical(id):
    medical_info = Medical.query.get(id)

    # Check if the medical_info exists
    if medical_info:
        # Delete the medical_info from the database
        db.session.delete(medical_info)
        db.session.commit()

    return redirect(url_for('view_medical'))



@app.route('/start_detection')
def start_detection():
    global detection_active
    if not detection_active:
        detection_active = True
    return 'Detection started'

@app.route('/stop_detection')
def stop_detection():
    global detection_active
    detection_active = False
    return 'Detection stopped'

@app.route("/start")
def start_video_feed():
    return render_template('outputview.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/objects')
def get_objects():
    return jsonify(detected_objects)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

