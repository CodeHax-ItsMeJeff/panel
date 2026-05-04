from app import db

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), unique=True, nullable=False)
    added_on = db.Column(db.DateTime, server_default=db.func.now())
