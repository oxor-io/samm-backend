from prover.merkle_tree import MerkleTree

MAX_PADDED_EMAIL_LEN = 124
CHUNK_LEN = 31
CHUNK_HEX_LEN = CHUNK_LEN * 2
TREE_HEIGHT = 8


def convert_str_to_int_list(x: str) -> list[int]:
    return list(map(ord, x))


def get_padded_email(email: str):
    padded_email = convert_str_to_int_list(email)
    padded_email_length = len(padded_email)
    if (zeros_num := MAX_PADDED_EMAIL_LEN - padded_email_length) > 0:
        padded_email += [0] * zeros_num

    return padded_email, padded_email_length


def generate_merkle_tree(emails_and_secrets: list[tuple[str, int]]) -> MerkleTree:
    leafs = []
    for email, secret in emails_and_secrets:
        # 248 = MAX_PADDED_EMAIL_LEN * 2 because of HEX
        email_hex = '{:<0248}'.format(email.encode().hex())
        email_chunks = [int(email_hex[i * CHUNK_HEX_LEN:i * CHUNK_HEX_LEN + CHUNK_HEX_LEN], 16) for i in range(4)]
        leafs.append(email_chunks + [secret])

    return MerkleTree(TREE_HEIGHT, leafs, leaf_len=len(leafs[0]))
