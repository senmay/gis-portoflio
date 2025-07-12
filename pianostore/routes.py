# pianostore/routes.py
import os
from flask import (render_template, request, flash, redirect, url_for, 
                   current_app, send_from_directory)
from . import pianostore_bp
from .models import db, SheetMusicProduct, Purchase
from .email import send_purchase_link_email

@pianostore_bp.route('/')
def shop():
    """Displays the main shop page with a list of products."""
    products = SheetMusicProduct.query.all()
    return render_template('pianostore/shop.html', products=products)

@pianostore_bp.route('/buy/<int:product_id>', methods=['GET', 'POST'])
def buy(product_id):
    """
    Handles the placeholder purchase process.
    GET: Shows a form to enter an email.
    POST: Simulates a purchase and sends a download link.
    """
    product = SheetMusicProduct.query.get_or_404(product_id)
    
    if request.method == 'POST':
        customer_email = request.form.get('email')
        if not customer_email:
            flash('Email address is required.', 'danger')
            return redirect(url_for('.buy', product_id=product.id))

        # --- Payment Placeholder Logic ---
        # In a real app, you would redirect to Stripe/PayU here.
        # We simulate a successful payment immediately.
        
        new_purchase = Purchase(
            customer_email=customer_email,
            product_id=product.id,
            is_paid=True  # Simulate successful payment
        )
        db.session.add(new_purchase)
        db.session.commit()

        # Send the download link via email
        send_purchase_link_email(new_purchase)
        
        flash('Thank you for your purchase! A download link has been sent to your email.', 'success')
        return redirect(url_for('.shop'))

    return render_template('pianostore/buy_form.html', product=product)

@pianostore_bp.route('/download/<purchase_token>')
def download_sheet(purchase_token):
    """Provides a secure way to download the purchased PDF."""
    purchase = Purchase.query.filter_by(purchase_token=purchase_token).first_or_404()

    if not purchase.is_paid:
        flash('This download link is invalid or the payment was not completed.', 'danger')
        return redirect(url_for('.shop'))

    pdf_filename = purchase.product.pdf_filename
    pdf_directory = os.path.join(current_app.root_path, 'pianostore', 'static', 'pdf')
    
    return send_from_directory(pdf_directory, pdf_filename, as_attachment=True)
