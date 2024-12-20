from circomlibpy.merkle_tree import MerkleTree
from models import Sequence

MAX_PADDED_EMAIL_LEN = 124
CHUNK_LEN = 31
CHUNK_HEX_LEN = CHUNK_LEN * 2
TREE_HEIGHT = 8


def without_0x(x: str | bytes) -> str | bytes:
    if isinstance(x, str) and x.startswith('0x') or isinstance(x, bytes) and x.startswith(b'0x'):
        return x[2:]
    return x


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

    return MerkleTree(leafs, height=TREE_HEIGHT)


def generate_sequences(header: list[int], header_length: int, member: str, relayer: str):
    padded_member = convert_str_to_int_list(member)
    padded_relayer = convert_str_to_int_list(relayer)
    padded_from = convert_str_to_int_list('from:')
    padded_to = convert_str_to_int_list('to:')
    padded_email_start = convert_str_to_int_list('<')

    # from
    from_index = find_subseq_index(header, padded_from)
    from_seq = Sequence(index=from_index, length=find_seq_end(header, header_length, from_index)-from_index+1)
    # member
    member_index = find_subseq_index(header, padded_email_start + padded_member) + 1
    if member_index == 1:
        member_index = find_subseq_index(header, padded_member)
    member_seq = Sequence(index=member_index, length=len(padded_member))
    # to
    to_index = find_subseq_index(header, padded_to)
    to_seq = Sequence(index=to_index, length=find_seq_end(header, header_length, to_index)-to_index+1)
    # relayer
    relayer_index = find_subseq_index(header, padded_email_start + padded_relayer) + 1
    if relayer_index == 1:
        relayer_index = find_subseq_index(header, padded_relayer)
    relayer_seq = Sequence(index=relayer_index, length=len(padded_relayer))

    return from_seq, member_seq, to_seq, relayer_seq


def find_subseq_index(arr: list[int], target: list[int]):
    start_idx = 0
    
    for i in range(len(arr)):
        if arr[i:i+len(target)] == target:
            start_idx = i
            break
    
    return start_idx


def find_seq_end(arr: list[int], length: int, start: int):
    end_idx = length - 1
    
    for i in range(start, length-1):
        if arr[i] == 13 and arr[i+1] == 10:     # 13 - \r, 10 - \n
            end_idx = i-1
            break
    
    return end_idx
