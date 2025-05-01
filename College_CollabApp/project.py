from baseObject import baseObject

class project(baseObject):
    def __init__(self):
        self.setup()  # load fields first
        self.data = []  # initialize cleanly
    
    def createBlank(self):
        d = {}
        for field in self.fields:
            d[field] = ''
        self.set(d)

    def verify_new(self, n=0):
        self.errors = []
        if len(self.data[n]['title'].strip()) == 0:
            self.errors.append("Title cannot be empty.")
        if len(self.data[n]['description'].strip()) < 10:
            self.errors.append("Description is too short.")
        if int(self.data[n]['people_required']) <= 0:
            self.errors.append("At least one person is required.")
        if self.data[n]['deadline'] == '':
            self.errors.append("Deadline must be set.")
        return len(self.errors) == 0
