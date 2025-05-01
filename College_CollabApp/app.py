'''
app.py

Main Flask application for managing users, projects, skills, and applications.
''' 
#===============================================================================
# Standard library imports
#===============================================================================
import os
import time
import datetime
from datetime import timedelta

#===============================================================================
# Third-party imports
#===============================================================================
from flask import (
    Flask, render_template, request, session,
    redirect, url_for, send_from_directory
)
from flask_session import Session
from werkzeug.utils import secure_filename

#===============================================================================
# Local application imports
#===============================================================================
from project import project
from skill_model import skill
from application import application
from user import user

#===============================================================================
# Application setup
#===============================================================================
app = Flask(__name__, static_url_path='')

# Session and secret key configuration
app.config['SECRET_KEY'] = '5sdghsgRTg'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

# Initialize server-side session handling
sess = Session()
sess.init_app(app)

#===============================================================================
# Jinja2 template filters and context processors
#===============================================================================
@app.context_processor
def inject_user():
    """Inject the current user into all templates as 'me'."""
    return dict(me=session.get('user'))


def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """
    Jinja2 filter to format datetime objects in templates.
    Returns empty string if value is None or not a datetime.
    """
    if value is None:
        return ''
    try:
        return value.strftime(format)
    except AttributeError:
        return 'NA'

app.jinja_env.filters['format_datetime'] = format_datetime

#===============================================================================
# Utility functions
#===============================================================================
def checkSession():
    """
    Verify if the user session is still active.
    If inactive for more than 500 seconds, mark session timed out.
    """
    if 'active' in session:
        elapsed = time.time() - session['active']
        if elapsed > 500:
            session['msg'] = 'Your session has timed out.'
            return False
        session['active'] = time.time()
        return True
    return False

#===============================================================================
# Route handlers
#===============================================================================
@app.route('/')
def home():
    """Redirect to login page."""
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login. Validates credentials, checks status,
    and stores user info in session.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        print("FORM Submitted:", email, password)

        u = user()
        if u.tryLogin(email, password):
            user_data = u.data[0]
            if user_data['status'] == 'pending':
                return render_template(
                    'login.html', title='Login',
                    msg='Your account is pending admin approval. Please try again later.'
                )
            session['user'] = user_data
            session['active'] = time.time()
            return redirect('/main')

        return render_template(
            'login.html', title='Login',
            msg='Incorrect username or password.'
        )

    msg = session.pop('msg', 'Type your email and password to continue.')
    return render_template('login.html', title='Login', msg=msg)

@app.route('/logout', methods=['GET','POST'])
def logout():
    """Log out the current user and clear session data."""
    session.pop('user', None)
    session.pop('active', None)
    return render_template('login.html', title='Login', msg='You have logged out.')

@app.route('/main')
def main():
    """Render main menu based on user role."""
    if not checkSession():
        return redirect('/login')
    role = session['user']['role']
    if role == 'admin':
        return render_template('main.html', title='Main menu')
    if role == 'professor':
        return render_template('professor_main.html', title='Main menu')
    if role == 'student':
        uid = session['user']['user_id']
        u = user()
        u.getById(uid)
        resume_path = u.data[0].get('resume_path')
        return render_template(
            'student_main.html', title='Main menu',
            me=u.data[0], resume_path=resume_path
        )
    return render_template('main.html', title='Main menu')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration. Creates new user with 'pending' status
    and awaits admin approval.
    """
    u = user()
    u.createBlank()
    msg = ''
    if request.method == 'POST':
        data = request.form.to_dict()
        data['status'] = 'pending'
        data['date_of_creation'] = datetime.date.today()
        u.set(data)
        if u.verify_new():
            u.insert()
            return render_template(
                'ok_dialog.html',
                msg=" Registration successful! Await admin approval."
            )
        msg = '<br>'.join(u.errors)
    return render_template('register.html', u=u, msg=msg)

#-------------------------------------------------------------------------------
# Admin user management
#-------------------------------------------------------------------------------
@app.route('/users/manage', methods=['GET', 'POST'])
def manage_user():
    """Admin view to list, add, update, or delete users."""
    if not checkSession() or session['user']['role'] != 'admin':
        return redirect('/login')
    o = user()
    action = request.args.get('action')
    pkval = request.args.get('pkval')
    if action == 'delete':
        o.deleteById(pkval)
        return render_template('ok_dialog.html', msg="Deleted.")
    if action == 'insert':
        d = {k: request.form.get(k) for k in ['fname','email','role','password','password2']}
        o.set(d)
        if o.verify_new():
            o.insert()
            return render_template('ok_dialog.html', msg="User added.")
        return render_template('users/add.html', obj=o)
    if action == 'update':
        o.getById(pkval)
        for field in ['fname','email','role','password','password2']:
            o.data[0][field] = request.form.get(field)
        if o.verify_update():
            o.update()
            return render_template('ok_dialog.html', msg="User updated.")
        return render_template('users/manage.html', obj=o)
    if not pkval:
        o.getByRole(['student', 'professor'])
        return render_template('users/manage_user.html', obj=o)
    if pkval == 'new':
        o.createBlank()
        return render_template('users/add.html', obj=o)
    o.getById(pkval)
    return render_template('users/manage.html', obj=o)

@app.route('/users/update_status', methods=['POST'])
def update_status():
    """Admin endpoint to approve or reject user registrations."""
    if not checkSession() or session['user']['role'] != 'admin':
        return redirect('/login')
    user_id = request.form.get('user_id')
    new_status = request.form.get('status')
    if not user_id or new_status not in ['active', 'rejected']:
        return redirect('/users/manage')
    u = user()
    u.getById(user_id)
    if not u.data:
        return redirect('/users/manage')
    u.data[0]['status'] = new_status
    u.update()
    return redirect('/users/manage')

#===============================================================================
# Professor project management
#===============================================================================
@app.route('/projects/post', methods=['GET', 'POST'])
def post_project():
    """Allow professors to post new projects with associated skills."""
    if not checkSession() or session['user']['role'] != 'professor':
        return redirect('/login')
    p = project()
    msg = ''
    if request.method == 'POST':
        data = request.form.to_dict()
        data.update({'posted_by': session['user']['user_id'], 'date_posted': datetime.date.today()})
        p.set(data)
        if p.verify_new():
            p.insert()
            pid = p.data[0]['project_id']
            for name in request.form.getlist('skills'):
                if name.strip():
                    s = skill()
                    s.set({'skill_name': name.strip(), 'project_id': pid, 'user_id': None})
                    s.insert()
            msg = "Project posted successfully."
            return render_template('professor_main.html', msg=msg)
        msg = '<br>'.join(p.errors)
    else:
        p.createBlank()
    return render_template('projects/post_project.html', obj=p, msg=msg)

@app.route('/projects/myprojects')
def view_my_projects():
    """List projects posted by the current professor or all for admins."""
    if not checkSession() or session['user']['role'] not in ['professor','admin']:
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
    """Edit or delete existing projects and their skills."""
    if not checkSession() or session['user']['role'] not in ['professor','admin']:
        return redirect('/login')
    p = project(); msg = ''
    pk = request.args.get('pkval')
    # Load existing data or initialize blank
    if pk == 'new':
        p.createBlank(); skills = []
    else:
        p.getById(pk)
        s = skill()
        s.cur.execute("SELECT skill_name FROM RV_Skill WHERE project_id=%s AND user_id IS NULL LIMIT 5", [pk])
        skills = [r['skill_name'] for r in s.cur.fetchall()]
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'Delete Project':
            a = application(); a.cur.execute("DELETE FROM RV_Application WHERE project_id=%s", [pk])
            p.deleteById(pk)
            return redirect('/users/projects' if session['user']['role']=='admin' else '/projects/myprojects')
        data = request.form.to_dict()
        data.update({'posted_by': session['user']['user_id'], 'date_posted': datetime.date.today()})
        if pk != 'new': data['project_id'] = pk
        p.set(data)
        if p.verify_new():
            if pk=='new': p.insert(); pid = p.data[0]['project_id']
            else: p.update(); pid = pk
            # Refresh skills
            s = skill(); s.cur.execute("DELETE FROM RV_Skill WHERE project_id=%s AND user_id IS NULL", [pid])
            for i,name in enumerate(request.form.getlist('skills')):
                name=name.strip();
                if name and i<5:
                    s.set({'skill_name':name,'project_id':pid,'user_id':None}); s.insert()
            return redirect('/users/projects' if session['user']['role']=='admin' else '/projects/myprojects')
        msg = '<br>'.join(p.errors)
    return render_template('projects/manage_project.html', obj=p, msg=msg, skills=skills)

@app.route('/projects/browse')
def browse_projects():
    """Allow students to browse and see available projects."""
    if not checkSession() or session['user']['role']!='student':
        return redirect('/login')
    p = project()
    p.cur.execute("""
        SELECT p.*, u.user_name AS posted_by_name
        FROM RV_Project p JOIN RV_User u ON p.posted_by=u.user_id
        ORDER BY p.date_posted DESC
    """)
    p.data = p.cur.fetchall()
    for r in p.data:
        s = skill(); s.cur.execute("SELECT skill_name FROM RV_Skill WHERE project_id=%s AND user_id IS NULL LIMIT 5", [r['project_id']])
        r['skills'] = [sk['skill_name'] for sk in s.cur.fetchall()]
    return render_template('projects/browse_projects.html', obj=p)

@app.route('/projects/apply')
def apply_to_project():
    """Students apply to projects, preventing duplicate applications."""
    if not checkSession() or session['user']['role']!='student':
        return redirect('/login')
    pid = request.args.get('pid'); uid = session['user']['user_id']
    a = application()
    a.cur.execute("SELECT * FROM RV_Application WHERE project_id=%s AND applicant_id=%s", [pid,uid])
    if a.cur.fetchone():
        return render_template('ok_dialog.html', msg="You have already applied to this project.")
    a.set({'project_id':pid,'applicant_id':uid,'app_date':datetime.date.today(),'status':'pending'})
    a.insert()
    return render_template('ok_dialog.html', msg="Application submitted successfully.")

#===============================================================================
# Resume upload (students)
#===============================================================================
ALLOWED_EXTENSIONS = {'pdf','docx'}
UPLOAD_FOLDER = os.path.join('static','resumes')
@app.route('/student/upload_resume', methods=['GET','POST'])
def upload_resume():
    """Allow students to upload resume files (PDF/DOCX)."""
    if not checkSession() or session['user']['role']!='student':
        return redirect('/login')
    msg = ''
    uid = session['user']['user_id']
    user_dir = os.path.join(UPLOAD_FOLDER,str(uid))
    os.makedirs(user_dir, exist_ok=True)
    if request.method=='POST':
        file = request.files.get('resume')
        if not file:
            msg = "No file selected."
        else:
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.',1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                msg = "Only PDF or DOCX files are allowed."
            else:
                save_path = os.path.join(user_dir,filename)
                file.save(save_path)
                rel_path = os.path.join('resumes',str(uid),filename)
                u = user(); u.getById(uid)
                u.data[0]['resume_path'] = rel_path; u.update()
                msg = "Resume uploaded successfully."
    return render_template('student/upload_resume.html', msg=msg)

#===============================================================================
# Application views
#===============================================================================
@app.route('/applications/mine')
def my_applications():
    """Students view their own applications."""
    if not checkSession() or session['user']['role']!='student': return redirect('/login')
    uid = session['user']['user_id']; a = application()
    a.cur.execute("""
        SELECT a.*, p.title, p.deadline, u.user_name AS professor
        FROM RV_Application a
        JOIN RV_Project p ON a.project_id=p.project_id
        JOIN RV_User u ON p.posted_by=u.user_id
        WHERE a.applicant_id=%s
        ORDER BY a.app_date DESC
    """, [uid])
    a.data = a.cur.fetchall()
    return render_template('applications/my_applications.html', obj=a)

@app.route('/applications/manage', methods=['GET','POST'])
def admin_applications():
    """Admin view of all applications across projects."""
    if not checkSession() or session['user']['role']!='admin': return redirect('/login')
    a = application()
    a.cur.execute("""
        SELECT a.app_id, a.status, a.app_date,
               p.title AS project_title,
               u.user_name AS student_name
        FROM RV_Application a
        JOIN RV_Project p ON a.project_id=p.project_id
        JOIN RV_User u ON a.applicant_id=u.user_id
        ORDER BY a.app_date DESC
    """)
    a.data = a.cur.fetchall()
    return render_template('users/manage_applications.html', obj=a)

#===============================================================================
# Admin project & skill overviews
#===============================================================================
@app.route('/users/projects')
def admin_view_projects():
    """Admin overview of all posted projects."""
    if not checkSession() or session['user']['role']!='admin': return redirect('/login')
    p = project()
    p.cur.execute("""
        SELECT p.*, u.user_name AS professor_name
        FROM RV_Project p
        JOIN RV_User u ON p.posted_by=u.user_id
        ORDER BY p.date_posted DESC
    """)
    p.data = p.cur.fetchall()
    return render_template('users/manage_projects.html', obj=p)

@app.route('/users/skills')
def admin_view_skills():
    """Admin overview of all skills across users and projects."""
    if not checkSession() or session['user']['role']!='admin': return redirect('/login')
    s = skill()
    s.cur.execute("""
        SELECT sk.skill_name, sk.project_id, sk.user_id,
               u.user_name AS user_name,
               p.title AS project_title
        FROM RV_Skill sk
        LEFT JOIN RV_User u ON sk.user_id=u.user_id
        LEFT JOIN RV_Project p ON sk.project_id=p.project_id
        ORDER BY sk.skill_name
    """)
    skills = s.cur.fetchall()
    return render_template('users/manage_skills.html', skills=skills)

@app.route('/users/skills/delete', methods=['POST'])
def delete_skill():
    """Delete a specific skill entry by user or project."""
    if not checkSession() or session['user']['role']!='admin': return redirect('/login')
    name = request.form.get('skill_name')
    uid = request.form.get('user_id') or None
    pid = request.form.get('project_id') or None
    s = skill()
    if uid and not pid:
        s.cur.execute("DELETE FROM RV_Skill WHERE skill_name=%s AND user_id=%s AND project_id IS NULL", [name,uid])
    elif pid and not uid:
        s.cur.execute("DELETE FROM RV_Skill WHERE skill_name=%s AND project_id=%s AND user_id IS NULL", [name,pid])
    return redirect('/users/skills')

#===============================================================================
# Student skill management
#===============================================================================
@app.route('/student/my_skills', methods=['GET','POST'])
def my_skills():
    """Students manage their personal skill list."""
    if not checkSession() or session['user']['role']!='student': return redirect('/login')
    uid = session['user']['user_id']; msg=''; s=skill()
    if request.method=='POST':
        s.cur.execute("DELETE FROM RV_Skill WHERE user_id=%s AND project_id IS NULL", [uid])
        for i,name in enumerate(request.form.getlist('skills')):
            name=name.strip()
            if name and i<5:
                s.set({'skill_name':name,'user_id':uid,'project_id':None}); s.insert()
        msg='Skills updated successfully.'
    s.cur.execute("SELECT skill_name FROM RV_Skill WHERE user_id=%s AND project_id IS NULL", [uid])
    skills=[r['skill_name'] for r in s.cur.fetchall()]
    return render_template('student/manage_skills.html', skills=skills, msg=msg)

#===============================================================================
# Professor views applicants for their projects
#===============================================================================
@app.route('/applications/view_for_professor', methods=['GET','POST'])
def view_applicants_for_professor():
    """Professors view and rate applicants based on skill match."""
    if not checkSession() or session['user']['role']!='professor': return redirect('/login')
    prof_id=session['user']['user_id']; a=application()
    a.cur.execute("""
        SELECT a.app_id, a.status, a.applicant_id, a.project_id,
               p.title AS project_title, u.user_name AS applicant_name, u.resume_path
        FROM RV_Application a
        JOIN RV_Project p ON a.project_id=p.project_id
        JOIN RV_User u ON a.applicant_id=u.user_id
        WHERE p.posted_by=%s
        ORDER BY p.project_id, a.app_date DESC
    """, [prof_id])
    applications=a.cur.fetchall(); s=skill()
    for app in applications:
        s.cur.execute("SELECT skill_name FROM RV_Skill WHERE user_id=%s AND project_id IS NULL LIMIT 5", [app['applicant_id']])
        student_skills=[r['skill_name'].lower() for r in s.cur.fetchall()]
        s.cur.execute("SELECT skill_name FROM RV_Skill WHERE project_id=%s AND user_id IS NULL", [app['project_id']])
        project_skills=[r['skill_name'].lower() for r in s.cur.fetchall()]
        matches=set(student_skills)&set(project_skills)
        app['skills']=student_skills
        app['skill_match']=int((len(matches)/len(project_skills))*100) if project_skills else 0
    return render_template('applications/view_applicants.html', applications=applications)

@app.route('/applications/update_status', methods=['POST'])
def update_application_status():
    """Professors update application status (accept/reject)."""
    if session.get('user',{}).get('role')!='professor': return redirect('/login')
    aid=request.form.get('app_id'); new=request.form.get('status')
    if not aid or new not in ['pending','accepted','rejected']: return redirect('/applications/manage')
    a=application(); a.getById(aid)
    if a.data:
        a.data[0]['status']=new; a.update()
    return redirect('/applications/manage')

#===============================================================================
# Admin dashboard
#===============================================================================
@app.route('/users/dashboard')
def user_dashboard():
    """Admin dashboard showing counts and summaries."""
    if not checkSession() or session['user']['role']!='admin': return redirect('/login')
    data={}
    u=user(); u.cur.execute("SELECT COUNT(*) AS count FROM RV_User WHERE role!='admin'")
    data['user_count']=u.cur.fetchone()['count']
    u.cur.execute("""
        SELECT role, COUNT(*) AS count FROM RV_User
        WHERE role IN ('student','professor') GROUP BY role
    """)
    for r in u.cur.fetchall(): data[f"{r['role']}_count"]=r['count']
    s=skill(); s.cur.execute("SELECT skill_name, COUNT(*) AS count FROM RV_Skill GROUP BY skill_name ORDER BY count DESC LIMIT 5")
    data['top_skills']=s.cur.fetchall()
    p=project(); p.cur.execute("SELECT u.user_name, COUNT(*) AS count FROM RV_Project p JOIN RV_User u ON p.posted_by=u.user_id GROUP BY u.user_name ORDER BY count DESC")
    data['projects_per_professor']=p.cur.fetchall()
    p.cur.execute("SELECT COUNT(*) AS total FROM RV_Project"); data['total_projects'] = p.cur.fetchone()['total']
    a=application(); a.cur.execute("SELECT status, COUNT(*) AS count FROM RV_Application GROUP BY status")
    data['application_status']=a.cur.fetchall()
    return render_template('users/dashboard.html', data=data)

#===============================================================================
# Static file serving
#===============================================================================
@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files from the 'static' directory."""
    return send_from_directory('static', path)

#===============================================================================
# Application entry point
#===============================================================================
if __name__ == '__main__':
    # Run the Flask development server
    app.run(host='127.0.0.1', debug=True)
