# pianostore/commands.py
import click
from flask.cli import with_appcontext
from .models import db, SheetMusicProduct

@click.group(name='pianostore')
def pianostore_cli():
    """Commands for the Piano Store."""
    pass

@pianostore_cli.command('init-db')
@with_appcontext
def init_db_command():
    """Creates the piano store database tables."""
    # This is handled by db.create_all() in app.py,
    # but can be useful for explicit initialization.
    db.create_all(bind_key='pianostore')
    click.echo('Initialized the piano store database.')

@pianostore_cli.command('add-product')
@with_appcontext
@click.option('--title', prompt=True, help='The title of the sheet music.')
@click.option('--description', prompt=True, help='A short description.')
@click.option('--price', prompt=True, type=float, help='The price in PLN.')
@click.option('--cover', prompt=True, help='Filename of the cover image in pianostore/static/img/.')
@click.option('--pdf', prompt=True, help='Filename of the PDF in pianostore/static/pdf/.')
def add_product_command(title, description, price, cover, pdf):
    """Adds a new sheet music product to the store."""
    product = SheetMusicProduct(
        title=title,
        description=description,
        price=price,
        cover_image_filename=cover,
        pdf_filename=pdf
    )
    db.session.add(product)
    db.session.commit()
    click.echo(f'Successfully added product: {title}')

def init_app(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(pianostore_cli)
