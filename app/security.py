import bcrypt


async def hash_password(password: str) -> str:
    password = password.encode()
    password_hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    return password_hashed.decode()


async def check_password(password: str, password_hashed: str) -> bool:
    password = password.encode()
    password_hashed = password_hashed.encode()
    return bcrypt.checkpw(password, password_hashed)