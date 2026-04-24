# handle password hashing + login verification
from passlib.context import CryptContext

# setting argon2 as hashing alogrithms
password_context = CryptContext(schemes=["argon2"], deprecated="auto")

# take plain text and convert into secure hash version
def hashing_password(password: str) -> str:
    return password_context.hash(password)

# take input(user's password) & it re-hashes and compares safely
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)
