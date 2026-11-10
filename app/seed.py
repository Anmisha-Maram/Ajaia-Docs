from .security import hash_password

DEMO_PASSWORD = "ajaia-demo"
DEMO_USERS = [
    ("alice@ajaia.test", "Alice Johnson"),
    ("bob@ajaia.test", "Bob Martinez"),
    ("carol@ajaia.test", "Carol Nguyen"),
]


def seed_users(conn) -> None:
    """Insert the demo users once. Safe to run on every startup."""
    for email, name in DEMO_USERS:
        exists = conn.execute("SELECT 1 FROM users WHERE email = %s", (email,)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
                (email, name, hash_password(DEMO_PASSWORD)),
            )