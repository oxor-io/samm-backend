import re
import base64
import logging

from dkim import DKIM
from dkim.asyncsupport import get_txt_async
from dkim.asyncsupport import load_pk_from_dns_async
from dkim import hash_headers
from dkim import CanonicalizationPolicy
from dkim import InvalidCanonicalizationPolicyError
from dkim import MessageFormatError
from dkim import HASH_ALGORITHMS
from dkim import HashThrough

# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)


async def extract_dkim_data(raw_email: bytes) -> tuple[str, list[int], int, int, list[str], list[str], list[str]]:
    # dkim_obj = DKIM(raw_email, logger=logger)
    dkim_obj = DKIM(raw_email)

    idx = 0
    prep = dkim_obj.verify_headerprep(idx)
    if not prep:
        # No signature
        # TODO: exception
        return False
    sig, include_headers, sigheaders = prep

    dns_name, domain, signature = get_dns_params(sig)
    key_size, pubkey_modulus_limbs, redc_params_limbs, signature_limbs = await extract_limbs(dns_name, signature)

    # NOTE: dkim signatures could be more than 1, but we use only first one
    headers, headers_length = extract_header(sig, include_headers, sigheaders[idx], dkim_obj.headers)

    return (
        domain,
        headers,
        headers_length,
        key_size,
        pubkey_modulus_limbs,
        redc_params_limbs,
        signature_limbs,
    )


def get_dns_params(sig: dict[bytes: bytes]) -> tuple[str, str, int]:
    name = sig[b's'] + b"._domainkey." + sig[b'd'] + b"."
    domain = sig[b'd'].decode()

    signature_bytes = base64.b64decode(re.sub(br"\s+", b"", sig[b'b']))
    signature = int.from_bytes(signature_bytes)

    return name, domain, signature


async def extract_limbs(dns_name: str, signature: int) -> tuple[int, list[str], list[str], list[str]]:
    # TODO: add try-cache for network exceptions
    pk, key_size, _, _ = await load_pk_from_dns_async(dns_name, get_txt_async)

    pubkey_modulus_limbs = calc_limbs(pk['modulus'])

    # TODO: (1 << (2 * keysize + 4)?
    # https://docs.rs/noir-bignum-paramgen/latest/src/noir_bignum_paramgen/lib.rs.html#25
    redc_params_limbs = calc_limbs((1 << (2 * key_size)) // pk['modulus'])

    signature_limbs = calc_limbs(signature)

    return key_size, pubkey_modulus_limbs, redc_params_limbs, signature_limbs


def calc_limbs(modulus: int) -> list[str]:
    out = []
    hhh = bin(modulus)[2:]
    for i in range(len(hhh), 0, -120):
        if (i - 120) < 0:
            val = hex(int(hhh[0:i], 2))
        else:
            val = hex(int(hhh[i-120:i], 2))
        if len(val) % 2:
            val = val.replace('0x', '0x0')
        out.append(val)
    return out


def extract_header(
        sig: dict[bytes: bytes],
        include_headers: list[bytes],
        sig_headers: tuple[bytes],
        original_headers: list[list[bytes]]
) -> tuple[list[int], int]:
    try:
        canon_policy = CanonicalizationPolicy.from_c_value(sig.get(b'c', b'simple/simple'))
    except InvalidCanonicalizationPolicyError as e:
        raise MessageFormatError("invalid c= value: %s" % e.args[0])

    hasher_algorithm = HASH_ALGORITHMS[sig[b'a']]
    hasher = HashThrough(hasher_algorithm(), debug=False)
    headers = canon_policy.canonicalize_headers(original_headers)
    signed_headers = hash_headers(
        hasher, canon_policy, headers, include_headers, sig_headers, sig)

    signed_headers_merged = b''.join([b'%s:%s' % (k, v) for k, v in signed_headers])
    dkim_headers_without_sig = sig_headers[1].strip().split(b'; b=')[0]
    signed_headers_merged += b'dkim-signature:' + dkim_headers_without_sig + b'; b='

    # TODO: 1024 only?
    signed_headers_merged_len = len(signed_headers_merged)
    if (zeroes_num := 1024 - signed_headers_merged_len) > 0:
        signed_headers_merged += b'\x00' * zeroes_num

    return [i for i in signed_headers_merged], signed_headers_merged_len
