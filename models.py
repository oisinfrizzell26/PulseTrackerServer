from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class HeartRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)
    rate = db.Column(db.Integer, nullable=False)
    mode = db.Column(db.Integer, nullable=False)
