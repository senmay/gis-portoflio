# pianostore/email.py
from flask import current_app, render_template
from flask_mail import Message
from threading import Thread

# This is a placeholder for the Mail object, which will be initialized in app.py
mail = None

def _send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    """Helper function to send an email."""
    app = current_app._get_current_object()
    msg = Message(
        subject,
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[to]
    )
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    
    # Send email in a background thread
    thr = Thread(target=_send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_purchase_link_email(purchase):
    """Sends an email with the download link to the customer."""
    token = purchase.purchase_token
    product_title = purchase.product.title
    send_email(
        purchase.customer_email,
        f'Your sheet music is here: {product_title}',
        'pianostore/email/purchase_link',
        product_title=product_title,
        download_token=token
    )
