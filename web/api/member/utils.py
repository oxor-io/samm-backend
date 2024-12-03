from circomlibpy.merkle_tree import MerkleTree
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

CHUNK_LEN = 31
CHUNK_HEX_LEN = CHUNK_LEN * 2
TREE_HEIGHT = 8

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def generate_merkle_tree(emails_and_secrets: list[tuple[str, int]]) -> MerkleTree:
    leafs = []
    for email, secret in emails_and_secrets:
        # 248 = MAX_PADDED_EMAIL_LEN * 2 because of HEX
        email_hex = '{:<0248}'.format(email.encode().hex())
        email_chunks = [int(email_hex[i * CHUNK_HEX_LEN:i * CHUNK_HEX_LEN + CHUNK_HEX_LEN], 16) for i in range(4)]
        leafs.append(email_chunks + [secret])

    return MerkleTree(leafs, height=TREE_HEIGHT)
