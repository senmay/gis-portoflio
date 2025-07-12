# pianostore/models.py
import uuid
from datetime import datetime
from app import db

class SheetMusicProduct(db.Model):
    """Represents a sheet music product in the store."""
    __bind_key__ = 'pianostore'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    cover_image_filename = db.Column(db.String(120), nullable=False)
    pdf_filename = db.Column(db.String(120), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<SheetMusicProduct {self.title}>'

class Purchase(db.Model):
    """Represents a customer's purchase."""
    __bind_key__ = 'pianostore'
    id = db.Column(db.Integer, primary_key=True)
    customer_email = db.Column(db.String(120), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('sheet_music_product.id'), nullable=False)
    purchase_token = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_paid = db.Column(db.Boolean, default=False) # This will be True in our placeholder logic

    product = db.relationship('SheetMusicProduct', backref=db.backref('purchases', lazy=True))

    def __repr__(self):
        return f'<Purchase {self.id} by {self.customer_email}>'
