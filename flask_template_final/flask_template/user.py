from baseObject import baseObject
import pymysql
import hashlib

class user(baseObject):
    def __init__(self):
        self.setup()
        
        self.roles = [
    {'value': 'admin', 'text': 'admin'},
    {'value': 'professor', 'text': 'professor'},
    {'value': 'student', 'text': 'student'}
]

    def hashPassword(self,pw):
        pw = pw +'xyz'
        return hashlib.md5(pw.encode('utf-8')).hexdigest()
    def role_list(self):
        rl = []
        for item in self.roles:
            rl.append(item['value'])
        return rl
    def verify_new(self,n=0):
        self.errors = []
        if '@' not in self.data[n]['email']:
            self.errors.append('Email must contain @')
        if self.data[n]['role'] not in self.role_list():
            valid_roles = [r['value'] for r in self.roles]
            self.errors.append(f"Role must be one of: {', '.join(valid_roles)}")
            #self.errors.append(f'role must be one of {self.role_list()}')
        u = user()
        u.getByField('email',self.data[0]['email'])
        if len(u.data) > 0:
            self.errors.append(f"Email address is already in use. ({self.data[0]['email']})")
        if len(self.data[n]['password']) < 3:
            self.errors.append('Password should be greater than 3 chars.')
        if self.data[n]['password'] != self.data[n]['password2']:
            self.errors.append('Retyped password must match.')
        self.data[n]['password'] = self.hashPassword(self.data[n]['password'])
        
        if len(self.errors) == 0:
            return True
        else:
            return False
    def verify_update(self,n=0):
        self.errors = []
        if '@' not in self.data[n]['email']:
            self.errors.append('Email must contain @')
        if self.data[n]['role'] not in self.role_list():
            self.errors.append(f'role must be one of {self.role_list()}')
        u = user()
        u.getByField('email',self.data[0]['email'])
        if len(u.data) > 0 and u.data[0][u.pk] != self.data[n][self.pk]:
            self.errors.append(f"Email address is already in use. ({self.data[0]['email']})")
        
        if len(self.data[n]['password']) == 0:
            del self.data[n]['password']
        else:
            if len(self.data[n]['password']) < 3:
                self.errors.append('Password needs to be more than 3 chars.')
            else:
                self.data[n]['password'] = self.hashPassword(self.data[n]['password'])
     
        if len(self.errors) == 0:
            return True
        else:
            return False
    def tryLogin(self,email,pw):
        pw = self.hashPassword(pw)
        sql = f'SELECT * FROM `{self.tn}` WHERE `email` = %s AND `password` = %s;'
        tokens = [email,pw]
        print(sql,tokens)
        self.cur.execute(sql,tokens)
        self.data = []
        for row in self.cur:
            self.data.append(row)
        if len(self.data) == 1: 
            return True
        else:
            return False