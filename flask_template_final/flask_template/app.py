from flask import Flask
from flask import render_template
from flask import request,session, redirect, url_for, send_from_directory,make_response 
from flask_session import Session
from project import project
from skill_model import skill
from application import application
from datetime import timedelta
from user import user
import os
from werkzeug.utils import secure_filename
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.form.get('email') is not None and request.form.get('password') is not None:
        email = request.form.get('email')
        password = request.form.get('password')
        print("FORM Submitted:", email, password)

        u = user()
        print("Running tryLogin()...")
        
        if u.tryLogin(email, password):
            print("Login successful. User data:", u.data)

            user_data = u.data[0]

            # Check user status
            if user_data['status'] == 'pending':
                print("Login denied. Account status is pending.")
                return render_template('login.html', title='Login', msg='Your account is pending admin approval. Please try again later.')

            # If approved, proceed to login
            session['user'] = user_data
            session['active'] = time.time()
            print("User logged in successfully. Redirecting to /main.")
            return redirect('/main')
        else:
            print("Login failed. Invalid credentials.")
            return render_template('login.html', title='Login', msg='Incorrect username or password.')

    else:
        print("No form submission. Showing login page.")
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
        uid = session['user']['user_id']
        u = user()
        u.getById(uid)
        resume_path = u.data[0].get('resume_path')
        return render_template('student_main.html', title='Main menu',me=u.data[0], resume_path=resume_path)
    else:
        return render_template('main.html', title='Main menu')
    

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
        o.getByRole(['student','professor'])
        return render_template('users/manage_user.html',obj = o)
    if pkval == 'new':
        o.createBlank()
        return render_template('users/add.html',obj = o)
    else:
        print(pkval)
        o.getById(pkval)
        return render_template('users/manage.html',obj = o)
    
@app.route('/users/update_status', methods=['POST'])
def update_status():
    if checkSession() == False or session['user']['role'] != 'admin':
        return redirect('/login')

    user_id = request.form.get('user_id')
    new_status = request.form.get('status')

    print("Updating user:", user_id, "→", new_status)

    if not user_id or new_status not in ['active', 'rejected']:
        return redirect('/users/manage')

    u = user()
    u.getById(user_id)

    if not u.data:
        print("User not found")
        return redirect('/users/manage')

    u.data[0]['status'] = new_status
    u.update()

    print("Status updated successfully.")
    return redirect('/users/manage')

    
##############################################################################3
###################              PROJECTS                #######################
############################################################################

@app.route('/projects/post', methods=['GET', 'POST'])
def post_project():
    if checkSession() == False or session['user']['role'] != 'professor':
        return redirect('/login')

    p = project()
    msg = ''

    if request.method == 'POST':
        data = request.form.to_dict()
        data['posted_by'] = session['user']['user_id']
        data['date_posted'] = datetime.date.today()

        p.set(data)

        if p.verify_new():
            p.insert()
            project_id = p.data[0]['project_id']  # Get inserted project ID

            skill_names = request.form.getlist("skills")
            for skill_name in skill_names:
                if skill_name.strip():
                    s = skill()
                    s.set({
                        'skill_name': skill_name.strip(),
                        'project_id': project_id,
                        'user_id': None
                    })
                    s.insert()



            return render_template("professor_main.html", msg="Project posted successfully.")
        else:
            msg = "<br>".join(p.errors)
    else:
        p.createBlank()  

    return render_template('projects/post_project.html', obj=p, msg=msg)



@app.route('/projects/myprojects')
def view_my_projects():
    if checkSession() == False or session['user']['role'] not in ['professor', 'admin']:
        return redirect('/login')

    p = project()
    if session['user']['role'] == 'admin':
        p.cur.execute("SELECT * FROM RV_Project ORDER BY date_posted DESC")
        p.data = p.cur.fetchall()
    else:
         p.getByField('posted_by', session['user']['user_id'])

    return render_template('projects/my_project.html', obj=p)


@app.route('/projects/manage', methods=['GET', 'POST'])
def manage_project():
    if checkSession() == False or session['user']['role'] not in ['professor', 'admin']:
        return redirect('/login')

    p = project()
    msg = ''
    pkval = request.args.get('pkval')

    # INITIAL LOAD
    if pkval == 'new':
        p.createBlank()
        skills = []
    else:
        p.getById(pkval)
        s = skill()
        s.cur.execute("SELECT skill_name FROM RV_Skill WHERE project_id = %s AND user_id IS NULL LIMIT 5", [pkval])
        skills = [row['skill_name'] for row in s.cur.fetchall()]

    # FORM SUBMISSION
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'Delete Project':
            a = application()
            a.cur.execute("DELETE FROM RV_Application WHERE project_id = %s", [pkval])
            p.deleteById(pkval)
            redirect_path = '/users/projects' if session['user']['role'] == 'admin' else '/projects/myprojects'
            return redirect(redirect_path)

        # Save Project
        data = request.form.to_dict()
        data['posted_by'] = session['user']['user_id']
        data['date_posted'] = datetime.date.today()

        if pkval != 'new':
            data['project_id'] = pkval

        p.set(data)

        if p.verify_new():
            if pkval == 'new':
                p.insert()
                project_id = p.data[0]['project_id']
            else:
                p.data[0]['project_id'] = pkval
                p.update()
                project_id = pkval

            # ✅ Update project skills
            s = skill()
            s.cur.execute("DELETE FROM RV_Skill WHERE project_id = %s AND user_id IS NULL", [project_id])
            skill_inputs = request.form.getlist("skills")
            count = 0
            for name in skill_inputs:
                name = name.strip()
                if name:
                    count += 1
                    if count > 5:
                        break
                    s.set({
                        'skill_name': name,
                        'project_id': project_id,
                        'user_id': None
                    })
                    s.insert()

            # ✅ Final redirect
            redirect_path = '/users/projects' if session['user']['role'] == 'admin' else '/projects/myprojects'
            return redirect(redirect_path)
        else:
            msg = "<br>".join(p.errors)

    return render_template('projects/manage_project.html', obj=p, msg=msg, skills=skills)



@app.route('/projects/browse')
def browse_projects():
    if checkSession() == False or session['user']['role'] != 'student':
        return redirect('/login')

    p = project()
    p.cur.execute("""
        SELECT p.*, u.user_name AS posted_by_name
        FROM RV_Project p
        JOIN RV_User u ON p.posted_by = u.user_id
        ORDER BY p.date_posted DESC
    """)
    p.data = p.cur.fetchall()

    # For each project, fetch its skills
    for row in p.data:
        s = skill()
        s.cur.execute("""
            SELECT skill_name FROM RV_Skill
            WHERE project_id = %s AND user_id IS NULL
            LIMIT 5
        """, [row['project_id']])
        skills = s.cur.fetchall()
        row['skills'] = [sk['skill_name'] for sk in skills]

    return render_template('projects/browse_projects.html', obj=p)


@app.route('/projects/apply')
def apply_to_project():
    if checkSession() == False or session['user']['role'] != 'student':
        return redirect('/login')

    pid = request.args.get('pid')
    uid = session['user']['user_id']

    # Check if already applied to this project
    a = application()
    a.cur.execute("""
        SELECT * FROM RV_Application
        WHERE project_id = %s AND applicant_id = %s
    """, [pid, uid])
    
    if a.cur.fetchone():
        return render_template("ok_dialog.html", msg="You have already applied to this project.")

    # Insert new application
    a.set({
        'project_id': pid,
        'applicant_id': uid,
        'app_date': datetime.date.today(),
        'status': 'pending'
    })
    a.insert()

    return render_template("ok_dialog.html", msg="Application submitted successfully.")




########################### UPLOAD RESUME ################################

ALLOWED_EXTENSIONS = {'pdf', 'docx'}
UPLOAD_FOLDER = os.path.join('static', 'resumes')

@app.route('/student/upload_resume', methods=['GET', 'POST'])
def upload_resume():
    if checkSession() == False or session['user']['role'] != 'student':
        return redirect('/login')

    msg = ''
    user_id = session['user']['user_id']
    user_dir = os.path.join(UPLOAD_FOLDER, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    if request.method == 'POST':
        file = request.files.get('resume')
        if not file:
            msg = "No file selected."
        else:
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                msg = "Only PDF or DOCX files are allowed."
            else:
                save_path = os.path.join(user_dir, filename)
                file.save(save_path)

                # Save path in DB (relative to static)
                rel_path = os.path.join('resumes', str(user_id), filename)

                u = user()
                u.getById(user_id)
                u.data[0]['resume_path'] = rel_path
                u.update()

                msg = "Resume uploaded successfully."

    return render_template("student/upload_resume.html", msg=msg)


############### VIEW APPLICATIONS ###########################
@app.route('/applications/mine')
def my_applications():
    if checkSession() == False or session['user']['role'] != 'student':
        return redirect('/login')

    uid = session['user']['user_id']
    a = application()

    a.cur.execute("""
        SELECT a.*, p.title, p.deadline, u.user_name AS professor
        FROM RV_Application a
        JOIN RV_Project p ON a.project_id = p.project_id
        JOIN RV_User u ON p.posted_by = u.user_id
        WHERE a.applicant_id = %s
        ORDER BY a.app_date DESC
    """, [uid])

    a.data = a.cur.fetchall()
    return render_template("applications/my_applications.html", obj=a)


@app.route('/applications/manage', methods=['GET', 'POST'])
def admin_applications():
    if checkSession() == False or session['user']['role'] != 'admin':
        return redirect('/login')

    a = application()

    # Fetch all applications with related project and student info
    a.cur.execute("""
        SELECT a.app_id, a.status, a.app_date,
               p.title AS project_title,
               u.user_name AS student_name
        FROM RV_Application a
        JOIN RV_Project p ON a.project_id = p.project_id
        JOIN RV_User u ON a.applicant_id = u.user_id
        ORDER BY a.app_date DESC
    """)
    a.data = a.cur.fetchall()

    return render_template("users/manage_applications.html", obj=a)


@app.route('/users/projects')
def admin_view_projects():
    if checkSession() == False or session['user']['role'] != 'admin':
        return redirect('/login')

    p = project()
    # Fetch all projects with professor info
    p.cur.execute("""
        SELECT p.*, u.user_name AS professor_name
        FROM RV_Project p
        JOIN RV_User u ON p.posted_by = u.user_id
        ORDER BY p.date_posted DESC
    """)
    p.data = p.cur.fetchall()

    return render_template("users/manage_projects.html", obj=p)

@app.route('/users/skills')
def admin_view_skills():
    if checkSession() == False or session['user']['role'] != 'admin':
        return redirect('/login')

    s = skill()
    s.cur.execute("""
        SELECT sk.skill_name, sk.project_id, sk.user_id,
               u.user_name AS user_name,
               p.title AS project_title
        FROM RV_Skill sk
        LEFT JOIN RV_User u ON sk.user_id = u.user_id
        LEFT JOIN RV_Project p ON sk.project_id = p.project_id
        ORDER BY sk.skill_name
    """)
    skills = s.cur.fetchall()

    return render_template("users/manage_skills.html", skills=skills)


@app.route('/users/skills/delete', methods=['POST'])
def delete_skill():
    if checkSession() == False or session['user']['role'] != 'admin':
        return redirect('/login')

    skill_name = request.form.get('skill_name')
    user_id = request.form.get('user_id') or None
    project_id = request.form.get('project_id') or None

    s = skill()

    if user_id and not project_id:
        s.cur.execute("DELETE FROM RV_Skill WHERE skill_name = %s AND user_id = %s AND project_id IS NULL", [skill_name, user_id])
    elif project_id and not user_id:
        s.cur.execute("DELETE FROM RV_Skill WHERE skill_name = %s AND project_id = %s AND user_id IS NULL", [skill_name, project_id])
    else:
        # Log or handle unknown cases
        print("Skill delete failed: No valid user_id or project_id.")
        return redirect('/users/skills')

    return redirect('/users/skills')





##################### STUDENT ################################
@app.route('/student/my_skills', methods=['GET', 'POST'])
def my_skills():
    if checkSession() == False or session['user']['role'] != 'student':
        return redirect('/login')

    uid = session['user']['user_id']
    msg = ''
    s = skill()

    if request.method == 'POST':
        # Delete old skills
        s.cur.execute("DELETE FROM RV_Skill WHERE user_id = %s AND project_id IS NULL", [uid])

        # Insert new skills
        skill_inputs = request.form.getlist("skills")
        count = 0
        for name in skill_inputs:
            if name.strip():
                count += 1
                if count > 5:
                    break
                s.set({
                    'skill_name': name.strip(),
                    'user_id': uid,
                    'project_id': None
                })
                s.insert()

        msg = "Skills updated successfully."

    # Fetch existing skills
    s.cur.execute("SELECT skill_name FROM RV_Skill WHERE user_id = %s AND project_id IS NULL", [uid])
    skills = [row['skill_name'] for row in s.cur.fetchall()]

    return render_template("student/manage_skills.html", skills=skills, msg=msg)

######################### PROFESSOR ###############################

@app.route('/applications/view_for_professor', methods=['GET', 'POST'])
def view_applicants_for_professor():
    if checkSession() == False or session['user']['role'] != 'professor':
        return redirect('/login')

    prof_id = session['user']['user_id']
    a = application()

    # Get all applications to this professor's posted projects
    a.cur.execute("""
        SELECT a.app_id, a.status, a.applicant_id, a.project_id,
               p.title AS project_title,
               u.user_name AS applicant_name,
               u.resume_path
        FROM RV_Application a
        JOIN RV_Project p ON a.project_id = p.project_id
        JOIN RV_User u ON a.applicant_id = u.user_id
        WHERE p.posted_by = %s
        ORDER BY p.project_id, a.app_date DESC
    """, [prof_id])
    
    applications = a.cur.fetchall()
    s = skill()

    for app in applications:
        #  Student's personal skills
        s.cur.execute("""
            SELECT skill_name 
            FROM RV_Skill 
            WHERE user_id = %s AND project_id IS NULL
            LIMIT 5
        """, [app['applicant_id']])
        student_skills = [row['skill_name'].strip().lower() for row in s.cur.fetchall()]

        #  Project's required skills
        s.cur.execute("""
            SELECT skill_name 
            FROM RV_Skill 
            WHERE project_id = %s AND user_id IS NULL
        """, [app['project_id']])
        project_skills = [row['skill_name'].strip().lower() for row in s.cur.fetchall()]

        #  Skill match %
        matches = set(student_skills) & set(project_skills)
        total_required = len(project_skills)
        match_percent = int((len(matches) / total_required) * 100) if total_required > 0 else 0

        # Attach to record
        app['skills'] = student_skills
        app['skill_match'] = match_percent

    return render_template("applications/view_applicants.html", applications=applications)




@app.route('/applications/update_status', methods=['POST'])
def update_application_status():
    if session['user']['role'] != 'professor':
        return redirect('/login')

    app_id = request.form.get('app_id')
    new_status = request.form.get('status')

    if not app_id or new_status not in ['pending', 'accepted', 'rejected']:
        return redirect('/applications/manage')

    a = application()
    a.getById(app_id)

    if not a.data:
        return redirect('/applications/manage')

    a.data[0]['status'] = new_status
    a.update()

    return redirect('/applications/manage')




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