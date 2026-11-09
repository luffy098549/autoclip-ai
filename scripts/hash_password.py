"""Generate a password hash for ADMIN_PASSWORD_HASH; never commit passwords."""
from getpass import getpass
from werkzeug.security import generate_password_hash

first = getpass("Contraseña de administrador: ")
second = getpass("Repetir contraseña: ")
if len(first) < 12:
    raise SystemExit("Usa al menos 12 caracteres")
if first != second:
    raise SystemExit("Las contraseñas no coinciden")
print("\nCopia este hash a ADMIN_PASSWORD_HASH en tu archivo .env (NO en GitHub):")
print(generate_password_hash(first))
