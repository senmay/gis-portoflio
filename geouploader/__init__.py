from flask import Blueprint

# Tworzymy Blueprint o nazwie 'geouploader'
# 'template_folder' wskazuje, że ten komponent ma swój własny,
# oddzielny folder z szablonami HTML.
geouploader_bp = Blueprint(
    'geouploader', 
    __name__, 
    template_folder='templates'
)

# Importujemy logikę ścieżek (routes), aby zostały one powiązane z naszym Blueprintem.
# Robimy to na końcu, aby uniknąć problemów z cyklicznym importem.
from . import routes
