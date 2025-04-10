import pymysql
import yaml
from pathlib import Path

class baseObject:
    def setup(self):
        self.data = []
        self.errors = []
        self.fields = []
        self.pk = None
        config = yaml.safe_load(Path("config.yml").read_text())

        #print(type(self).__name__)
        self.tn = config['tables'][type(self).__name__]
        self.conn = pymysql.connect(host=config['db']['host'], port=config['db']['port'], user=config['db']['user'],
                       passwd=config['db']['pw'], db=config['db']['db'], autocommit=True)
        self.cur = self.conn.cursor(pymysql.cursors.DictCursor)
        self.getFields()
    def getFields(self):
        self.fields = []
        sql = f"DESCRIBE `{self.tn}`;"
        self.cur.execute(sql)
        for row in self.cur:
            #print(row)
            if row['Extra'] == 'auto_increment':
                self.pk = row['Field']
            else:
                self.fields.append(row['Field'])
    
    def set(self, d):
        row = {}
    
        # Assign only database fields
        for field in self.fields:
            row[field] = d.get(field, '')

        extras =['password2']
        for extra in extras:
            if extra in d:
                row[extra] = d[extra]

        self.data = [row]
        
    def insert(self,n=0):
        sql = f'INSERT INTO {self.tn} ('
        vals = ''
        tokens = []
        for field in self.fields:
            sql += f'`{field}`,' + ' '
            vals += '%s, '
            tokens.append(self.data[n][field])
        sql = sql[0:-2]
        vals = vals[0:-2]
        sql += ') VALUES '
        sql += f'({vals});'
        #print(sql,tokens)
        self.cur.execute(sql,tokens)
        self.data[0][self.pk] = self.cur.lastrowid
        return True

    def update(self,n=0):
        sql = f'UPDATE `{self.tn}` SET '
        parameters = []   
        n=0
        for field in self.fields:
            if field in self.data[n].keys():
                sql += f'`{field}` = %s,' 
                parameters.append(self.data[n][field])
        sql = sql[0:-1]
        sql += f' WHERE `{self.pk}` = %s;'
        parameters.append(self.data[0][self.pk])
        #print(sql,parameters)
        self.cur.execute(sql, parameters)
    def getAll(self):
        sql = f'SELECT * FROM `{self.tn}`;'
        self.cur.execute(sql)
        self.data = []
        for row in self.cur:
            self.data.append(row)
    def getById(self,id):
        sql = f'SELECT * FROM `{self.tn}` WHERE `{self.pk}` = %s;'
        self.cur.execute(sql,[id])
        self.data = []
        for row in self.cur:
            self.data.append(row)
    def getByField(self,field,value):
        sql = f'SELECT * FROM `{self.tn}` WHERE `{field}` = %s;'
        self.cur.execute(sql,[value])
        self.data = []
        for row in self.cur:
            self.data.append(row)
    def deleteById(self,id):
        sql = f'DELETE FROM `{self.tn}` WHERE `{self.pk}` = %s;'
        self.cur.execute(sql,[id])
        self.data = []
        for row in self.cur:
            self.data.append(row)
    def createBlank(self):
        d = {}
        for field in self.fields:
            d[field] = ''
        self.set(d)