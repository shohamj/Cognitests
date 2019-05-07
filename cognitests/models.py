from cognitests import db


class Subject(db.Model):
    __tablename__ = 'Subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    serial = db.Column(db.Text, unique=True, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('Groups.id'))
    age = db.Column(db.Integer)
    gender = db.Column(db.Text)
    dom_hand = db.Column(db.Text)
    education = db.Column(db.Integer)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Group(db.Model):
    __tablename__ = 'Groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PartOfGroup(db.Model):
    __tablename__ = 'PartOfGroup'
    subject_id = db.Column(db.Integer, db.ForeignKey('Subjects.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('Groups.id'), primary_key=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Task(db.Model):
    __tablename__ = 'Tasks'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('Subjects.id'))
    start_time = db.Column(db.REAL)
    end_time = db.Column(db.REAL)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class NbackSettings(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'NbackSettings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.TEXT, unique=True, nullable=False)
    nback = db.Column(db.Integer)
    trials = db.Column(db.Integer)
    timeout = db.Column(db.REAL)
    rest = db.Column(db.REAL)
    words = db.Column(db.TEXT)
    instructions = db.Column(db.Integer, db.ForeignKey('Instructions.id'))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class EyesSettings(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'EyesSettings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.TEXT, unique=True, nullable=False)
    open_time = db.Column(db.REAL)
    close_time = db.Column(db.REAL)
    rounds = db.Column(db.Integer)
    open_sound = db.Column(db.TEXT)
    close_sound = db.Column(db.TEXT)
    instructions = db.Column(db.Integer, db.ForeignKey('Instructions.id'))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class IAPSSettings(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'IAPSSettings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.TEXT, unique=True, nullable=False)
    images_path = db.Column(db.TEXT, nullable=False)
    rounds = db.Column(db.TEXT, nullable=False)
    rest = db.Column(db.REAL, nullable=False)
    mask = db.Column(db.TEXT, nullable=False)
    mask_duration = db.Column(db.REAL, nullable=False)
    fixation = db.Column(db.REAL, nullable=False)
    instructions = db.Column(db.Integer, db.ForeignKey('Instructions.id'))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Instructions(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'Instructions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text, nullable=False)
    paragraphs = db.Column(db.Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
