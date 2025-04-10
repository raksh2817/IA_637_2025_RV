from flask import Flask
from flask import render_template
from flask import request,session, redirect, url_for, send_from_directory,make_response 
from flask_session import Session
from datetime import timedelta
from user import user
from vehicle import vehicle
import time
import datetime

app = Flask(__name__,static_url_path='')

app.config['SECRET_KEY'] = '5sdghsgRTg'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
sess = Session()
sess.init_app(app)

@app.route('/')
def home():
    return redirect('/login')

@app.context_processor
def inject_user():
    return dict(me=session.get('user'))

def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    if value is None:
        return ''
    try:
        return value.strftime(format)
    except AttributeError:
        return 'NA'

app.jinja_env.filters['format_datetime'] = format_datetime

@app.route('/login',methods = ['GET','POST'])
def login():
    if request.form.get('email') is not None and request.form.get('password') is not None:
        print("FORM:", request.form.get('email'), request.form.get('password'))
        u = user()
        print("BEFORE TRYLOGIN")
        if u.tryLogin(request.form.get('email'),request.form.get('password')):
            print("Login ok",u.data)
            session['user'] = u.data[0]
            session['active'] = time.time()
            return redirect('main')
        else:
            print("Login Failed")
            return render_template('login.html', title='Login', msg='Incorrect username or password.')
    else:   
        if 'msg' not in session.keys() or session['msg'] is None:
            m = 'Type your email and password to continue.'
        else:
            m = session['msg']
            session['msg'] = None
        return render_template('login.html', title='Login', msg=m)    
    
@app.route('/logout',methods = ['GET','POST'])
def logout():
    if session.get('user') is not None:
        del session['user']
        del session['active']
    return render_template('login.html', title='Login', msg='You have logged out.')
@app.route('/main')
def main():
    if checkSession() == False: 
        return redirect('/login')
    
    if session['user']['role'] == 'admin':
        return render_template('main.html', title='Main menu') 
    elif session['user']['role'] == 'professor':
        return render_template('professor_main.html', title='Main menu')
    elif session['user']['role'] == 'student':
        return render_template('student_main.html', title='Main menu')
    else:
        return render_template('customer_main.html', title='Main menu') 
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    u = user()
    u.createBlank()  # Initializes u.data[0] with default fields
    msg = ''

    if request.method == 'POST':
        data = request.form.to_dict()
        print("Form Data Submitted:", data)
        # Set required system fields
        data['status'] = 'pending'
        data['date_of_creation'] = datetime.date.today()
        u.set(data)
        if u.data:
            print("u.data[0] after set:", u.data[0])
        else:
            print("u.data is empty after set.")
        print(" Data bound to user object:", u.data[0])
        if u.verify_new():
            u.insert()
            return render_template("ok_dialog.html", msg=" Registration successful! Await admin approval.")
        else:
            msg = "<br>".join(u.errors)
            print("Validation Errors:", u.errors)

    return render_template('register.html', u=u, msg=msg)



@app.route('/users/manage',methods=['GET','POST'])
def manage_user():
    if checkSession() == False or session['user']['role'] != 'admin': 
        return redirect('/login')
    o = user()
    action = request.args.get('action')
    pkval = request.args.get('pkval')
    if action is not None and action == 'delete': #action=delete&pkval=123
        o.deleteById(request.args.get('pkval'))
        return render_template('ok_dialog.html',msg= "Deleted.")
    if action is not None and action == 'insert':
        d = {}
        d['fname'] = request.form.get('fname')
        d['email'] = request.form.get('email')
        d['role'] = request.form.get('role')
        d['password'] = request.form.get('password')
        d['password2'] = request.form.get('password2')
        o.set(d)
        if o.verify_new():
            #print(o.data)
            o.insert()
            return render_template('ok_dialog.html',msg= "User added.")
        else:
            return render_template('users/add.html',obj = o)
    if action is not None and action == 'update':
        o.getById(pkval)
        o.data[0]['fname'] = request.form.get('fname')
        o.data[0]['email'] = request.form.get('email')
        o.data[0]['role'] = request.form.get('role')
        o.data[0]['password'] = request.form.get('password')
        o.data[0]['password2'] = request.form.get('password2')
        if o.verify_update():
            o.update()
            return render_template('ok_dialog.html',msg= "User updated. ")
        else:
            return render_template('users/manage.html',obj = o)
    if pkval is None:
        o.getAll()
        return render_template('users/manage_user.html',obj = o)
    if pkval == 'new':
        o.createBlank()
        return render_template('users/add.html',obj = o)
    else:
        print(pkval)
        o.getById(pkval)
        return render_template('users/manage.html',obj = o)
    

    
##############################################################################3
###################               vehicles:
############################################################################

@app.route('/vehicles/manage', methods=['GET', 'POST'])
def manage_vehicle():
    if checkSession() == False or session['user']['role'] != 'admin':
        return redirect('/login')
    o = vehicle()
    u = user()
    u.getAll()
    o.owners = u.data
    action = request.args.get('action')
    pkval = request.args.get('pkval')

    if action == 'delete' and pkval:
        o.deleteById(pkval)
        return render_template('ok_dialog.html', msg="Vehicle deleted.")

    if action == 'insert':
        d = {}
        d['make'] = request.form.get('make')
        d['model'] = request.form.get('model')
        d['owner_uid'] = request.form.get('owner_uid')
        d['created'] = datetime.datetime.now()
        d['year'] = request.form.get('year')
        o.set(d)
        if o.verify_new():  # You'll need to implement this in your vehicle class
            o.insert()
            return render_template('ok_dialog.html', msg="Vehicle added.")
        else:
            return render_template('vehicles/add.html', obj=o)

    if action == 'update' and pkval:
        o.getById(pkval)
        if o.data:
            o.data[0]['make'] = request.form.get('make')
            o.data[0]['model'] = request.form.get('model')
            o.data[0]['owner_uid'] = request.form.get('owner_uid')
            o.data[0]['year'] = request.form.get('year')
            if o.verify_update():  # Implement this in your vehicle class
                o.update()
                return render_template('ok_dialog.html', msg="Vehicle updated.")
            else:
                return render_template('vehicles/manage.html', obj=o)
        else:
            return render_template('error_dialog.html', msg=f"Vehicle with ID {pkval} not found.")

    if pkval is None:
        o.getWithOwner()
        return render_template('vehicles/list.html', obj=o)

    if pkval == 'new':
        o.createBlank()
        return render_template('vehicles/add.html', obj=o)

    else:
        o.getById(pkval)
        if o.data:
            return render_template('vehicles/manage.html', obj=o)
        else:
            return render_template('error_dialog.html', msg=f"Vehicle with ID {pkval} not found.")

# endpoint route for static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

#standalone function to be called when we need to check if a user is logged in.
def checkSession():
    if 'active' in session.keys():
        timeSinceAct = time.time() - session['active']
        #print(timeSinceAct)
        if timeSinceAct > 500:
            session['msg'] = 'Your session has timed out.'
            return False
        else:
            session['active'] = time.time()
            return True
    else:
        return False   


if __name__ == '__main__':
   app.run(host='127.0.0.1',debug=True)   