import secrets

SECERT_KEY_GENERATION = secrets.token_urlsafe(128)
print(SECERT_KEY_GENERATION)