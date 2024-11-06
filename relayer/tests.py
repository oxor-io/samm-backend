#!/usr/bin/env python3
import asyncio
from email.parser import BytesParser

from dotenv import load_dotenv
load_dotenv()

import blockchain
import crud
import db
from mailer.dkim_extractor import extract_dkim_data
from main import parse_member_message
from main import parse_body
from main import extract_tx_data
from models import TxData
from models import ProofStruct
from models import MemberMessage
from models import TransactionOperation
from utils import get_padded_email
from utils import convert_str_to_int_list
from utils import generate_merkle_tree
from utils import generate_sequences
from main import generate_zk_proof
from models import Sequence
from models import ApprovalData


approve_eml = \
b"""DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=oxor.io; s=google; t=1730381274; x=1730986074; darn=yandex.ru;
        h=to:subject:message-id:date:from:mime-version:from:to:cc:subject
         :date:message-id:reply-to;
        bh=ToQN7Uh/6z9Z882zr1qbeqB/CPiWSy5x9AwC7dsWzr0=;
        b=Od56zHSC71fwHSZQ+yMbn5GpYRIXgU7+5h+tufghBRV/ddmx0zy5oZSid1Qivy7fsC
         klF0s5l332YWPJBCNyCX6OaGkbMu5Fu0B48WkCl/0VqMH19YQ7sqfNeNdjIGzrvMXsKB
         TD8anJ6WgrxNJmRNqQFjyq2RXzUVezCgC4rXG7O5vWkeFG7GVLC3gv6ffLcPGoP4goXE
         KxEeTKhjGBezbw5Xl2S0uEnGXIpHZpQLgmJ8x8RoDsj0zHNh1L73tzKVeUwfszRtE9z6
         TNe1L7vigF5tAOC3Jgnu4qKFKY6ZxJchlWe8b8j80sr594jcl9EEslv/6D22SkiVzb/C
         bp+A==
MIME-Version: 1.0
From: Artem Belozerov <artem@oxor.io>
Date: Thu, 31 Oct 2024 16:27:42 +0300
Message-ID: <CAEMY_m35hMnDNLzpfx0S9K=YWYwiH5KOhFYCUO9a5LtWApnqaA@mail.gmail.com>
Subject: yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68=
To: oxorio@yandex.ru
Content-Type: multipart/alternative; boundary="0000000000002943b80625c5c931"
Return-Path: artem@oxor.io
X-Yandex-Forward: f531c0e9771039f750d294a362bc131e

--0000000000002943b80625c5c931
Content-Type: text/plain; charset="UTF-8"



--0000000000002943b80625c5c931
Content-Type: text/html; charset="UTF-8"

<div dir="ltr"><br></div>

--0000000000002943b80625c5c931--"""

initial_eml = \
b"""DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=oxor.io; s=google; t=1730461283; x=1731066083; darn=yandex.ru;
        h=to:subject:message-id:date:from:mime-version:from:to:cc:subject
         :date:message-id:reply-to;
        bh=274+/wYEHmdPS8e6lwiI+hPwvQV5s2qxK8/NPvtN93c=;
        b=HQ7N81hxuOnD1hOCtNRSHJZJ7AC072PvYbn/j5G+CL60gawiUWmpU/LCUQBINscOEO
         F2R5/L3ccTH2ncllNHt2ZG4yv4OfmRo9AfeZJYdRDAqaEbf6k5knZkd9ocN3Hcg9e/xX
         9GyMUBW+QkZsK/qU8GIp7sg7fdSlB3W+YZr068Y7vuVHHhwyDqvbDeGD5ea9sPuvv1+S
         f1aOD3A0O6u2haRzut+Jw7VjBLKaMABnTC03nB7a8YUUjdZ7kFBdOGld/Kr8Ndj+dAWV
         U8CUjCwM5VmHHitsUmInd6VhYKtZvyREcyK2QYfTCAR1Zgq4gMKNnUNgUKxaSY8mOeov
         UrMw==
MIME-Version: 1.0
From: Artem Belozerov <artem@oxor.io>
Date: Fri, 1 Nov 2024 14:41:12 +0300
Message-ID: <CAEMY_m0ZsjP9URUQj_NamVodrSc3N1zb3bwTavrJK2U4fSTwKg@mail.gmail.com>
Subject: yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68=
To: oxorio@yandex.ru
Content-Type: multipart/alternative; boundary="00000000000011c6110625d86a1b"
Return-Path: artem@oxor.io
X-Yandex-Forward: f531c0e9771039f750d294a362bc131e

--00000000000011c6110625d86a1b
Content-Type: text/plain; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

samm_id=3D1;to=3D0x07a565b7ed7d7a678680a4c162885bedbb695fe0;value=3D5000111=
390000000000;data=3D0xa9059cbb0000000000000000000000003f5047bdb647dc39c8862=
5e17bdbffee905a9f4400000000000000000000000000000000000000000000011c9a62d04e=
d0c80000;operation=3DCALL;nonce=3D34344;deadline=3D123123123123;

--00000000000011c6110625d86a1b
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div dir=3D"ltr">samm_id=3D1;to=3D0x07a565b7ed7d7a678680a4c162885bedbb695fe=
0;value=3D5000111390000000000;data=3D0xa9059cbb0000000000000000000000003f50=
47bdb647dc39c88625e17bdbffee905a9f44000000000000000000000000000000000000000=
00000011c9a62d04ed0c80000;operation=3DCALL;nonce=3D34344;deadline=3D1231231=
23123;<br></div>

--00000000000011c6110625d86a1b--"""

demo_eml = \
b"""DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=icloud.com; s=1a1hai; t=1730212767; bh=hXvmIASNeX8UIUgVT2cpbi5U3jxaa4fzYhFVr28fMLM=; h=To:From:Subject:Date:Message-Id:Content-Type:MIME-Version; b=ozLGDm2kG99CQk6LYftcHCDDXnbJ3ffB10zKMIhL6eihDiSuRj1qa0rhjEOUqpEzA
	 7ZD8hljHeHcXfb+04u2JfYyDID5LCLLugPkzLbBaoCFB607U6rCQQER61YmrNaU+LP
	 RpE5mavrpRicFFeXFIkHGevBwr0CW6tTE1EhkLylRFDEPRlH8xnJ7a0iHed9d0QYjO
	 pbOkS3nP10xJJzUeaadVrEIhYewBuBLPT0khH9aIxBV9uSSO+jviGrPy2l6xYUPuvf
	 JF3xl08G5bBnxXya2lRG8IkjGxe0WC3DjkffnfXKeb6xBoUXFG6XS5b8GIA727CcdG
	 e1BYC/+LjDAyw==
To: ad@oxor.io
From: swoons.00rubbing@icloud.com
Subject: hHqTyYhaHOM1/52r43r+AeTIo6GQIvXGYZCY0VwjzVo=
Date: Tue, 29 Oct 2024 14:38:59 +0000 (UTC)
Message-Id: <AE5A29F7-911A-46B6-B2AB-9BDCBBDAFB61@icloud.com>
Content-Type: multipart/alternative; boundary=Apple-Webmail-42--c98d52a5-988b-499e-bf5f-62b5b100ba74
MIME-Version: 1.0

test test
"""


def _create_test_body(samm_id: int) -> str:
    tx_to = '0x07a565b7ed7d7a678680a4c162885bedbb695fe0'
    tx_value = 5000111390000000000
    tx_data = '0xa9059cbb'\
           '0000000000000000000000003f5047bdb647dc39c88625e17bdbffee905a9f44'\
           '00000000000000000000000000000000000000000000011c9a62d04ed0c80000'
    tx_operation = TransactionOperation.call.value
    tx_nonce = 34344
    tx_deadline = 123123123123
    body = f'samm_id={samm_id};'\
           f'to={tx_to};'\
           f'value={tx_value};'\
           f'data={tx_data};'\
           f'operation={tx_operation};'\
           f'nonce={tx_nonce};'\
           f'deadline={tx_deadline};'
    return body


def test_parse_body():
    msg = BytesParser().parsebytes(initial_eml)
    body = parse_body(msg)
    samm_id, tx_data = extract_tx_data(body)

    assert samm_id == 1
    assert tx_data.to == '0x07a565b7ed7d7a678680a4c162885bedbb695fe0'
    assert tx_data.value == 5000111390000000000
    assert tx_data.data == b'0xa9059cbb'\
                           b'0000000000000000000000003f5047bdb647dc39c88625e17bdbffee905a9f44'\
                           b'00000000000000000000000000000000000000000000011c9a62d04ed0c80000'
    assert tx_data.operation == TransactionOperation.call
    assert tx_data.nonce == 34344
    assert tx_data.deadline == 123123123123


async def test_dkmi_extraction():
    # https://github.com/oxor-io/samm-circuits/blob/master/builds/samm_2048/Prover.toml

    header = [116, 111, 58, 97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 13, 10, 102, 114, 111, 109, 58, 115, 119, 111, 111, 110, 115, 46, 48, 48, 114, 117, 98, 98, 105, 110, 103, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 13, 10, 115, 117, 98, 106, 101, 99, 116, 58, 104, 72, 113, 84, 121, 89, 104, 97, 72, 79, 77, 49, 47, 53, 50, 114, 52, 51, 114, 43, 65, 101, 84, 73, 111, 54, 71, 81, 73, 118, 88, 71, 89, 90, 67, 89, 48, 86, 119, 106, 122, 86, 111, 61, 13, 10, 100, 97, 116, 101, 58, 84, 117, 101, 44, 32, 50, 57, 32, 79, 99, 116, 32, 50, 48, 50, 52, 32, 49, 52, 58, 51, 56, 58, 53, 57, 32, 43, 48, 48, 48, 48, 32, 40, 85, 84, 67, 41, 13, 10, 109, 101, 115, 115, 97, 103, 101, 45, 105, 100, 58, 60, 65, 69, 53, 65, 50, 57, 70, 55, 45, 57, 49, 49, 65, 45, 52, 54, 66, 54, 45, 66, 50, 65, 66, 45, 57, 66, 68, 67, 66, 66, 68, 65, 70, 66, 54, 49, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 62, 13, 10, 99, 111, 110, 116, 101, 110, 116, 45, 116, 121, 112, 101, 58, 109, 117, 108, 116, 105, 112, 97, 114, 116, 47, 97, 108, 116, 101, 114, 110, 97, 116, 105, 118, 101, 59, 32, 98, 111, 117, 110, 100, 97, 114, 121, 61, 65, 112, 112, 108, 101, 45, 87, 101, 98, 109, 97, 105, 108, 45, 52, 50, 45, 45, 99, 57, 56, 100, 53, 50, 97, 53, 45, 57, 56, 56, 98, 45, 52, 57, 57, 101, 45, 98, 102, 53, 102, 45, 54, 50, 98, 53, 98, 49, 48, 48, 98, 97, 55, 52, 13, 10, 109, 105, 109, 101, 45, 118, 101, 114, 115, 105, 111, 110, 58, 49, 46, 48, 13, 10, 100, 107, 105, 109, 45, 115, 105, 103, 110, 97, 116, 117, 114, 101, 58, 118, 61, 49, 59, 32, 97, 61, 114, 115, 97, 45, 115, 104, 97, 50, 53, 54, 59, 32, 99, 61, 114, 101, 108, 97, 120, 101, 100, 47, 114, 101, 108, 97, 120, 101, 100, 59, 32, 100, 61, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 59, 32, 115, 61, 49, 97, 49, 104, 97, 105, 59, 32, 116, 61, 49, 55, 51, 48, 50, 49, 50, 55, 54, 55, 59, 32, 98, 104, 61, 104, 88, 118, 109, 73, 65, 83, 78, 101, 88, 56, 85, 73, 85, 103, 86, 84, 50, 99, 112, 98, 105, 53, 85, 51, 106, 120, 97, 97, 52, 102, 122, 89, 104, 70, 86, 114, 50, 56, 102, 77, 76, 77, 61, 59, 32, 104, 61, 84, 111, 58, 70, 114, 111, 109, 58, 83, 117, 98, 106, 101, 99, 116, 58, 68, 97, 116, 101, 58, 77, 101, 115, 115, 97, 103, 101, 45, 73, 100, 58, 67, 111, 110, 116, 101, 110, 116, 45, 84, 121, 112, 101, 58, 77, 73, 77, 69, 45, 86, 101, 114, 115, 105, 111, 110, 59, 32, 98, 61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    header_length = 531
    pubkey_modulus_limbs = ["0xe5cf995b5ef59ce9943d1f4209b6ab", "0xe0caf03235e91a2db27e9ed214bcc6",
                            "0xafe1309f87414bd36ed296dacfade2", "0xbeff3f19046a43adce46c932514988",
                            "0x324041af8736e87de4358860fff057", "0xadcc6669dfa346f322717851a8c22a",
                            "0x8b2a193089e6bf951c553b5a6f71aa", "0x0a570fe582918c4f731a0002068df2",
                            "0x39419a433d6bfdd1978356cbca4b60", "0x550d695a514d38b45c862320a00ea5",
                            "0x1c56ac1dfbf1beea31e8a613c2a51f", "0x6a30c9f22d2e5cb6934263d0838809",
                            "0x0a281f268a44b21a4f77a91a52f960", "0x5134dc3966c8e91402669a47cc8597",
                            "0x71590781df114ec072e641cdc5d224", "0xa1bc0f0937489c806c1944fd029dc9",
                            "0x911f6e47f84db3b64c3648ebb5a127", "0xd5"]

    redc_params_limbs = ["0xa48a824e4ebc7e0f1059f3ecfa57c4", "0x05c1db23f3c7d47ad7e7d7cfda5189",
                         "0x79bb6bbbd8facf011f022fa9051aec", "0x24faa4cef474bed639362ea71f7a21",
                         "0x1503aa50b77e24b030841a7d061581", "0x5bbf4e62805e1860a904c0f66a5fad",
                         "0x5cbd24b72442d2ce647dd7d0a44368", "0x074a8839a4460c169dce7138efdaef",
                         "0x0f06e09e3191b995b08e5b45182f65", "0x51fad4a89f8369fe10e5d4b6e149a1",
                         "0xdc778b15982d11ebf7fe23b4e15f10", "0xa09ff3a4567077510c474e4ac0a21a",
                         "0xb37e69e5dbb77167b73065e4c5ad6a", "0xecf4774e22e7fe3a38642186f7ae74",
                         "0x16e72b5eb4c813a3b37998083aab81", "0xa48e7050aa8abedce5a45c16985376",
                         "0xdd3285e53b322b221f7bcf4f8f8ad8", "0x0132"]

    signature_limbs = ["0x0ef6ec271d19ed41602ffe2e30c0cb", "0x729e6fac41a145c51ba5d2e5bf0620", "0x11bc2248c6c5ed160b70e391f7e77d", "0xf7c9177c65d3c1b96c19f15f26b695", "0xe4923be8ef886acfcb697ac5850fba", "0x87b006e04b3d3d24847f5a231055f6", "0x2de73f5d31249cd479a69d56b10885", "0x727b6b488779df5dd106233a96ce91", "0xd4c4d448642f295114310f4651fcc6", "0x270515e5c52241c67af070af4096ea", "0x5626acd694f8b3d1a44e666afae946", "0xb6c16a808507ad3b53aac2410111eb", "0x8bb625f6320c80f92c22cbba03e4cc", "0x913303b643f219631de1dc5df6fed3", "0xe8a10e24ae463d6a6b4ae18c4394aa", "0x20c35e76c9ddf7c1d74cca30884be9", "0x32c60e6da41bdf42424e8b61fb5c1c", "0xa3"]

    _domain, _header, _header_length, _key_size, _pubkey_modulus_limbs, _redc_params_limbs, _signature_limbs = \
        await extract_dkim_data(demo_eml)

    assert _pubkey_modulus_limbs == pubkey_modulus_limbs
    assert _redc_params_limbs == redc_params_limbs
    assert _signature_limbs == signature_limbs
    assert _header == header
    assert _header_length == header_length
    assert _domain == 'icloud.com'
    assert _key_size == 2048


async def test_padded_emails():
    padded_member = [115, 119, 111, 111, 110, 115, 46, 48, 48, 114, 117, 98, 98, 105, 110, 103,
                     64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


    member_length = 27

    padded_relayer = [97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    relayer_length = 10

    member_email = 'swoons.00rubbing@icloud.com'
    relayer_email = 'ad@oxor.io'

    _padded_member, _padded_member_len = get_padded_email(member_email)
    _padded_relayer, _padded_relayer_len = get_padded_email(relayer_email)

    assert _padded_member == padded_member
    assert _padded_relayer == padded_relayer
    assert _padded_member_len == member_length
    assert _padded_relayer_len == relayer_length


async def test_msg_hash_convert():
    msg_hash = [104, 72, 113, 84, 121, 89, 104, 97, 72, 79, 77, 49, 47, 53, 50, 114, 52, 51, 114, 
        43, 65, 101, 84, 73, 111, 54, 71, 81, 73, 118, 88, 71, 89, 90, 67, 89, 48, 86, 119, 106, 122, 86, 111, 61]

    email_subject = 'hHqTyYhaHOM1/52r43r+AeTIo6GQIvXGYZCY0VwjzVo='

    _msg_hash = convert_str_to_int_list(email_subject)

    assert _msg_hash == msg_hash


def test_tree_generation():
    root = "3693852034816220969980398025931646744713742489852125909138985185751997118833"
    path_elements = [
        "12181380747766530663019567607642183183842923227107503250029079799455572184768",
        "14752333704901535729870671529802743390978931851983497868673528090961169705309",
        "16538135409515176547194568220928820916682786764828918280336228751737583509415",
        "11286972368698509976183087595462810875513684078608517520839298933882497716792",
        "3607627140608796879659380071776844901612302623152076817094415224584923813162",
        "19712377064642672829441595136074946683621277828620209496774504837737984048981",
        "20775607673010627194014556968476266066927294572720319469184847051418138353016",
        "3396914609616007258851405644437304192397291162432396347162513310381425243293",
    ]
    path_indices = [0, 0, 0, 0, 0, 0, 0, 0]

    TEST_EMAIL_ADDRESSES = [
        "swoons.00rubbing@icloud.com",
        "aa@oxor.io",
        "ab@oxor.io",
        "ac@oxor.io",
        "ad@oxor.io"
    ]
    TEST_SECRETS = [
        1,
        2,
        3,
        4,
        5
    ]

    tree = generate_merkle_tree(list(zip(TEST_EMAIL_ADDRESSES, TEST_SECRETS)))
    _path_elements, _path_indices = tree.gen_proof(leaf_pos=0)

    assert str(tree.root) == root
    assert [str(i) for i in _path_elements] == path_elements
    assert _path_indices == path_indices


async def test_sequence_genration():
    # https://github.com/oxor-io/samm-circuits/blob/master/builds/samm_2048/Prover.toml

    header = [116, 111, 58, 97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 13, 10, 102, 114, 111, 109, 58, 115, 119, 111, 111, 110, 115, 46, 48, 48, 114, 117, 98, 98, 105, 110, 103, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 13, 10, 115, 117, 98, 106, 101, 99, 116, 58, 104, 72, 113, 84, 121, 89, 104, 97, 72, 79, 77, 49, 47, 53, 50, 114, 52, 51, 114, 43, 65, 101, 84, 73, 111, 54, 71, 81, 73, 118, 88, 71, 89, 90, 67, 89, 48, 86, 119, 106, 122, 86, 111, 61, 13, 10, 100, 97, 116, 101, 58, 84, 117, 101, 44, 32, 50, 57, 32, 79, 99, 116, 32, 50, 48, 50, 52, 32, 49, 52, 58, 51, 56, 58, 53, 57, 32, 43, 48, 48, 48, 48, 32, 40, 85, 84, 67, 41, 13, 10, 109, 101, 115, 115, 97, 103, 101, 45, 105, 100, 58, 60, 65, 69, 53, 65, 50, 57, 70, 55, 45, 57, 49, 49, 65, 45, 52, 54, 66, 54, 45, 66, 50, 65, 66, 45, 57, 66, 68, 67, 66, 66, 68, 65, 70, 66, 54, 49, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 62, 13, 10, 99, 111, 110, 116, 101, 110, 116, 45, 116, 121, 112, 101, 58, 109, 117, 108, 116, 105, 112, 97, 114, 116, 47, 97, 108, 116, 101, 114, 110, 97, 116, 105, 118, 101, 59, 32, 98, 111, 117, 110, 100, 97, 114, 121, 61, 65, 112, 112, 108, 101, 45, 87, 101, 98, 109, 97, 105, 108, 45, 52, 50, 45, 45, 99, 57, 56, 100, 53, 50, 97, 53, 45, 57, 56, 56, 98, 45, 52, 57, 57, 101, 45, 98, 102, 53, 102, 45, 54, 50, 98, 53, 98, 49, 48, 48, 98, 97, 55, 52, 13, 10, 109, 105, 109, 101, 45, 118, 101, 114, 115, 105, 111, 110, 58, 49, 46, 48, 13, 10, 100, 107, 105, 109, 45, 115, 105, 103, 110, 97, 116, 117, 114, 101, 58, 118, 61, 49, 59, 32, 97, 61, 114, 115, 97, 45, 115, 104, 97, 50, 53, 54, 59, 32, 99, 61, 114, 101, 108, 97, 120, 101, 100, 47, 114, 101, 108, 97, 120, 101, 100, 59, 32, 100, 61, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 59, 32, 115, 61, 49, 97, 49, 104, 97, 105, 59, 32, 116, 61, 49, 55, 51, 48, 50, 49, 50, 55, 54, 55, 59, 32, 98, 104, 61, 104, 88, 118, 109, 73, 65, 83, 78, 101, 88, 56, 85, 73, 85, 103, 86, 84, 50, 99, 112, 98, 105, 53, 85, 51, 106, 120, 97, 97, 52, 102, 122, 89, 104, 70, 86, 114, 50, 56, 102, 77, 76, 77, 61, 59, 32, 104, 61, 84, 111, 58, 70, 114, 111, 109, 58, 83, 117, 98, 106, 101, 99, 116, 58, 68, 97, 116, 101, 58, 77, 101, 115, 115, 97, 103, 101, 45, 73, 100, 58, 67, 111, 110, 116, 101, 110, 116, 45, 84, 121, 112, 101, 58, 77, 73, 77, 69, 45, 86, 101, 114, 115, 105, 111, 110, 59, 32, 98, 61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    header_length = 531

    member_email = 'swoons.00rubbing@icloud.com'
    relayer_email = 'ad@oxor.io'

    from_seq, member_seq, to_seq, relayer_seq = generate_sequences(header, header_length, member_email, relayer_email)

    assert from_seq == Sequence(index=15,length=32)
    assert member_seq == Sequence(index=20,length=27)
    assert to_seq == Sequence(index=0,length=13)
    assert relayer_seq == Sequence(index=3,length=10)


async def test_prover():
    # https://github.com/oxor-io/samm-circuits/blob/master/builds/samm_2048/Prover.toml

    header = [116, 111, 58, 97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 13, 10, 102, 114, 111, 109, 58, 115, 119, 111, 111, 110, 115, 46, 48, 48, 114, 117, 98, 98, 105, 110, 103, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 13, 10, 115, 117, 98, 106, 101, 99, 116, 58, 104, 72, 113, 84, 121, 89, 104, 97, 72, 79, 77, 49, 47, 53, 50, 114, 52, 51, 114, 43, 65, 101, 84, 73, 111, 54, 71, 81, 73, 118, 88, 71, 89, 90, 67, 89, 48, 86, 119, 106, 122, 86, 111, 61, 13, 10, 100, 97, 116, 101, 58, 84, 117, 101, 44, 32, 50, 57, 32, 79, 99, 116, 32, 50, 48, 50, 52, 32, 49, 52, 58, 51, 56, 58, 53, 57, 32, 43, 48, 48, 48, 48, 32, 40, 85, 84, 67, 41, 13, 10, 109, 101, 115, 115, 97, 103, 101, 45, 105, 100, 58, 60, 65, 69, 53, 65, 50, 57, 70, 55, 45, 57, 49, 49, 65, 45, 52, 54, 66, 54, 45, 66, 50, 65, 66, 45, 57, 66, 68, 67, 66, 66, 68, 65, 70, 66, 54, 49, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 62, 13, 10, 99, 111, 110, 116, 101, 110, 116, 45, 116, 121, 112, 101, 58, 109, 117, 108, 116, 105, 112, 97, 114, 116, 47, 97, 108, 116, 101, 114, 110, 97, 116, 105, 118, 101, 59, 32, 98, 111, 117, 110, 100, 97, 114, 121, 61, 65, 112, 112, 108, 101, 45, 87, 101, 98, 109, 97, 105, 108, 45, 52, 50, 45, 45, 99, 57, 56, 100, 53, 50, 97, 53, 45, 57, 56, 56, 98, 45, 52, 57, 57, 101, 45, 98, 102, 53, 102, 45, 54, 50, 98, 53, 98, 49, 48, 48, 98, 97, 55, 52, 13, 10, 109, 105, 109, 101, 45, 118, 101, 114, 115, 105, 111, 110, 58, 49, 46, 48, 13, 10, 100, 107, 105, 109, 45, 115, 105, 103, 110, 97, 116, 117, 114, 101, 58, 118, 61, 49, 59, 32, 97, 61, 114, 115, 97, 45, 115, 104, 97, 50, 53, 54, 59, 32, 99, 61, 114, 101, 108, 97, 120, 101, 100, 47, 114, 101, 108, 97, 120, 101, 100, 59, 32, 100, 61, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 59, 32, 115, 61, 49, 97, 49, 104, 97, 105, 59, 32, 116, 61, 49, 55, 51, 48, 50, 49, 50, 55, 54, 55, 59, 32, 98, 104, 61, 104, 88, 118, 109, 73, 65, 83, 78, 101, 88, 56, 85, 73, 85, 103, 86, 84, 50, 99, 112, 98, 105, 53, 85, 51, 106, 120, 97, 97, 52, 102, 122, 89, 104, 70, 86, 114, 50, 56, 102, 77, 76, 77, 61, 59, 32, 104, 61, 84, 111, 58, 70, 114, 111, 109, 58, 83, 117, 98, 106, 101, 99, 116, 58, 68, 97, 116, 101, 58, 77, 101, 115, 115, 97, 103, 101, 45, 73, 100, 58, 67, 111, 110, 116, 101, 110, 116, 45, 84, 121, 112, 101, 58, 77, 73, 77, 69, 45, 86, 101, 114, 115, 105, 111, 110, 59, 32, 98, 61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    header_length = 531

    msg_hash = [104, 72, 113, 84, 121, 89, 104, 97, 72, 79, 77, 49, 47, 53, 50, 114, 52, 51, 114, 
        43, 65, 101, 84, 73, 111, 54, 71, 81, 73, 118, 88, 71, 89, 90, 67, 89, 48, 86, 119, 106, 122, 86, 111, 61]
    
    padded_member = [115, 119, 111, 111, 110, 115, 46, 48, 48, 114, 117, 98, 98, 105, 110, 103,
                     64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    member_length = 27
    
    secret = 1

    padded_relayer = [97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    relayer_length = 10

    root = "3693852034816220969980398025931646744713742489852125909138985185751997118833"
    path_elements = [
        "12181380747766530663019567607642183183842923227107503250029079799455572184768",
        "14752333704901535729870671529802743390978931851983497868673528090961169705309",
        "16538135409515176547194568220928820916682786764828918280336228751737583509415",
        "11286972368698509976183087595462810875513684078608517520839298933882497716792",
        "3607627140608796879659380071776844901612302623152076817094415224584923813162",
        "19712377064642672829441595136074946683621277828620209496774504837737984048981",
        "20775607673010627194014556968476266066927294572720319469184847051418138353016",
        "3396914609616007258851405644437304192397291162432396347162513310381425243293",
    ]
    path_indices = [0, 0, 0, 0, 0, 0, 0, 0]

    from_seq = Sequence(index=15,length=32)
    member_seq = Sequence(index=20,length=27)
    to_seq = Sequence(index=0,length=13)
    relayer_seq = Sequence(index=3,length=10)

    pubkey_modulus_limbs = ["0xe5cf995b5ef59ce9943d1f4209b6ab", "0xe0caf03235e91a2db27e9ed214bcc6",
                            "0xafe1309f87414bd36ed296dacfade2", "0xbeff3f19046a43adce46c932514988",
                            "0x324041af8736e87de4358860fff057", "0xadcc6669dfa346f322717851a8c22a",
                            "0x8b2a193089e6bf951c553b5a6f71aa", "0x0a570fe582918c4f731a0002068df2",
                            "0x39419a433d6bfdd1978356cbca4b60", "0x550d695a514d38b45c862320a00ea5",
                            "0x1c56ac1dfbf1beea31e8a613c2a51f", "0x6a30c9f22d2e5cb6934263d0838809",
                            "0x0a281f268a44b21a4f77a91a52f960", "0x5134dc3966c8e91402669a47cc8597",
                            "0x71590781df114ec072e641cdc5d224", "0xa1bc0f0937489c806c1944fd029dc9",
                            "0x911f6e47f84db3b64c3648ebb5a127", "0xd5"]

    redc_params_limbs = ["0xa48a824e4ebc7e0f1059f3ecfa57c4", "0x05c1db23f3c7d47ad7e7d7cfda5189",
                         "0x79bb6bbbd8facf011f022fa9051aec", "0x24faa4cef474bed639362ea71f7a21",
                         "0x1503aa50b77e24b030841a7d061581", "0x5bbf4e62805e1860a904c0f66a5fad",
                         "0x5cbd24b72442d2ce647dd7d0a44368", "0x074a8839a4460c169dce7138efdaef",
                         "0x0f06e09e3191b995b08e5b45182f65", "0x51fad4a89f8369fe10e5d4b6e149a1",
                         "0xdc778b15982d11ebf7fe23b4e15f10", "0xa09ff3a4567077510c474e4ac0a21a",
                         "0xb37e69e5dbb77167b73065e4c5ad6a", "0xecf4774e22e7fe3a38642186f7ae74",
                         "0x16e72b5eb4c813a3b37998083aab81", "0xa48e7050aa8abedce5a45c16985376",
                         "0xdd3285e53b322b221f7bcf4f8f8ad8", "0x0132"]

    signature_limbs = ["0x0ef6ec271d19ed41602ffe2e30c0cb", "0x729e6fac41a145c51ba5d2e5bf0620", "0x11bc2248c6c5ed160b70e391f7e77d", "0xf7c9177c65d3c1b96c19f15f26b695", "0xe4923be8ef886acfcb697ac5850fba", "0x87b006e04b3d3d24847f5a231055f6", "0x2de73f5d31249cd479a69d56b10885", "0x727b6b488779df5dd106233a96ce91", "0xd4c4d448642f295114310f4651fcc6", "0x270515e5c52241c67af070af4096ea", "0x5626acd694f8b3d1a44e666afae946", "0xb6c16a808507ad3b53aac2410111eb", "0x8bb625f6320c80f92c22cbba03e4cc", "0x913303b643f219631de1dc5df6fed3", "0xe8a10e24ae463d6a6b4ae18c4394aa", "0x20c35e76c9ddf7c1d74cca30884be9", "0x32c60e6da41bdf42424e8b61fb5c1c", "0xa3"]


    approval_data = ApprovalData(
        domain='icloud.com',
        header=header,
        header_length=header_length,

        msg_hash=msg_hash,

        padded_member=padded_member,
        padded_member_length=member_length,
        secret = secret,
        padded_relayer=padded_relayer,
        padded_relayer_length=relayer_length,

        pubkey_modulus_limbs=pubkey_modulus_limbs,
        redc_params_limbs=redc_params_limbs,
        signature=signature_limbs,

        key_size=2048,
        root=root,
        path_elements=path_elements,
        path_indices=path_indices,

        from_seq=from_seq,
        member_seq=member_seq,
        to_seq=to_seq,
        relayer_seq=relayer_seq,
    )

    zk_proof = await generate_zk_proof(approval_data)


async def test_parse_member_initial_message():
    await db.init_db()
    samm = await crud.fill_db_initial_tx(first_user_email='artem@oxor.io')

    uid: int = 123
    member_message: MemberMessage = await parse_member_message(uid, initial_eml)

    assert member_message.member.email == 'artem@oxor.io'
    assert member_message.tx is None
    assert member_message.initial_data is not None
    assert member_message.approval_data is not None

    assert member_message.initial_data.samm_id == samm.id
    assert member_message.initial_data.msg_hash == 'yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68='
    assert member_message.initial_data.tx_data.to == '0x07a565b7ed7d7a678680a4c162885bedbb695fe0'
    assert member_message.initial_data.tx_data.value == 5000111390000000000
    assert member_message.initial_data.tx_data.data == b'0xa9059cbb'\
           b'0000000000000000000000003f5047bdb647dc39c88625e17bdbffee905a9f44'\
           b'00000000000000000000000000000000000000000000011c9a62d04ed0c80000'
    assert member_message.initial_data.tx_data.operation == TransactionOperation.call.value
    assert member_message.initial_data.tx_data.nonce == 34344
    assert member_message.initial_data.tx_data.deadline == 123123123123
    assert len(member_message.initial_data.members) == 4
    assert member_message.initial_data.members[0].email == 'artem@oxor.io'


async def test_parse_member_approval_message():
    await db.init_db()
    await crud.fill_db_approval_tx(first_user_email='artem@oxor.io')
    uid: int = 123

    member_message: MemberMessage = await parse_member_message(uid, approve_eml)

    assert member_message.member.email == 'artem@oxor.io'
    assert member_message.tx.msg_hash == 'yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68='
    assert member_message.initial_data is None
    assert member_message.approval_data is not None


async def test_blockchain_execution_transaction():
    proofs = [
        ProofStruct(
            proof=b'000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000000ac0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000c9b957f94c58eec64b688ccdfed79aac6a000000000000000000000000000000000020c98cd39cb55e2ad6a289e7e175bc000000000000000000000000000000bb5fb5d23596fd5abcc9ad00a4275c20d80000000000000000000000000000000000074620fcb1575a1adac6dc77da2d7b000000000000000000000000000000b4722beddb96011800a36cd791781cf09c000000000000000000000000000000000010ccac2de1c42190e76e1a4fb22fc700000000000000000000000000000007e5e51827c6b64852cc7b7a2b1d44247300000000000000000000000000000000001199e032c757e560db0611a505ceaa0000000000000000000000000000007dbf05935fd6bdc4f2bfa30e4749cac88e0000000000000000000000000000000000076a3fabd5e1deb971d55d3e023c51000000000000000000000000000000c1b42d23e34ba575e0c47f8f70c7b9802e0000000000000000000000000000000000208bbac8f671b28b4a3a695e3f849d0000000000000000000000000000005b9b3611c1636571422f1ce8e063f33a9e00000000000000000000000000000000001fceada00528fb209840097d2cdd18000000000000000000000000000000a44c6b393ecb26d8fed8d6109ebf6f540000000000000000000000000000000000001f44addc9f2bbf5b0fd7bf77846dd20000000000000000000000000000007307a59c59f613f21d34372a3261e8ca16000000000000000000000000000000000003779650c8431646434c5b23d50f69000000000000000000000000000000c1783b1f794400a68491de7d2c3bfe29750000000000000000000000000000000000141aed242bfbf36c8b0ae768a083a2000000000000000000000000000000ee417b44dbbd83ba7b188484dce1e72df5000000000000000000000000000000000003c5e9f35c1a3bb7ca0af2ab78791f000000000000000000000000000000b5a5c1156a15812f40e5e81a098b0812d5000000000000000000000000000000000015c2cf1ebb3aaa0721ebcfb37c053d000000000000000000000000000000d45904d4066812f925ef510fd46f3fc32c00000000000000000000000000000000001277900b95eb2363ae46fb86311276000000000000000000000000000000a3e4c57168b12f431519899a4eee15cf8d00000000000000000000000000000000001c604967c84d9874a0a385ab7a8a0b0000000000000000000000000000007ecc723c819d9f7f4978ff5d102d48959c000000000000000000000000000000000024ce49a962e7bb429817dcecf42dad00000000000000000000000000000000d41c251ec1da7c109d65cd1ee600fd6f00000000000000000000000000000000000121b90b29049161b553e9c9f5634403b311ef89217d7270142a96bcfbc65b8888165801dfdfa5a4d70bd449b07f902cb13c83581022b7483c1b1fc48592019fabd1f077d990eb9f0ae9bfa64f8071242fddd2ff921c16dea92cf9660e3c7d7d395b56d2eff66237bceabf601983eb302447f36320257ba3f9a2df194f6fdfc10aea2a99bc48bb8f07efbeba9364e614663db70529c1e84f0ade9ef94484c3444df15a5d67887283c5e6d90e8328e22a9ec38f8a8a09a028dc681d6dc70268152ed0b152f1851de49687174588fdca072d459947151b8f10b39092a5da7f009de93ae26c0d1e4345ed1fbc45552baa265ff5d455dd56ab199797ae8e4ee2be851ea046b9937e1e2dbe4ce27a7afa6526c6a26e44a5a12d7faad98b23963cf29503405feb38ddf87d7acd5348b68efe18f11c437961f14a312e3569b9f3f177a5e1e080b763f75bf850966b8277f94e2c4c9a11649b9d52784e8861cc9fd214eb5dc975b4778b5873c24d68dae661c4093da18f45725e96c15815dcaa5e724b19e339be718930a9d69381375462a5d90177bc49581bc41b6da4cb3b0a1ce61997a2041b3459feca46e5109ab1636e15258ae5d2fce1e6a2e5c6dd4ae05a3ad6c9392552d40fdd7e708aea5a5ad24ccc2b439de045093f30d68c13ba21eebf55e6f26f68213f812717e6c04eff37d4912c56e091dc400fdba94f95b81de13ee29177fe8ca84a4c13ef8168dc45e26c821a4d62c4de96cce44a7507007e7aa23c88c3339da3facbaf91217e2a8712e0d905f1f4b7deb452658b82cfee6be5e2f7e1e89b3673baa119983df0fe0d3cbf362cbc56444272f30673408dac7eae5c8aaceb1ec8e3422de602735f724bd712631c8c7d069f658df47b6cbac848e918c0f50cf76a22b061633afa75a4f86a73f812fe3cb9f2bfe4a658c3522bff949019b9280a1f48f0f7ee48fab48180fb6c5304b46161da4c3f3a88e75529e20683f33f13a55f471fa225ffaa5a241ba2366917c924d07d6b673b9b4a27a572d6b78d6aba224dce8d52ad37f29635caefd511031c6319ba9d02770683a5a3458abd10677f6488db8adae7173b6fd162aa473512cd774ef0a6119651f6f718ec9d2a0eac031320acfa1e78f62872a4d7ef88c8138925007172534e60db7bd251bd404071535261aad912ca0d01e304e11b71002800257e4fc7437a57f96a3c12853fb0425640065fc1f54be489a3548d0287b51cfe0a5a694bb30b244c3c93de79b75ba9ad2814b922f737f83c4c3aa34b89b117efaa6cd7eb10e815ee6e0adb4c59a38353f07d0473c1641f4ea1802de6475b1f9460d622bfcc21c69793ee87b660a9447e1bb4e254b04655dbefeaa1fb9e1c2f65c32c59ef2e7d300b16aa2147bf953846c7e2c9c076e3ec379dfccf4ad29c248cdec496de37f25b5486d2fc7818e4b04f48eda3105c3c9e94a4cbbdf5d55f1344498ccd611d65b9c10099f9b136bf23538d2dadd83451954649e858016e491ddf4a512c84be417a171811d9463c87ef9a49c35ab39f38bd7f9125bb936f5608ef49652b347780c857745fb9018408e9352ab3bb7de556e3f234aef8d35f790ea5f413eb941d4a26bca651f6322c0f185058fae04d55e0db4db195c23634ee290fe86851e2c13fa026d662a12f788833aaa3cf5381630ce6ff68ab61ce207000f417d3636312057252f7e8a1f176354eb739946e9987bb5e5903ff03fe1c8127ca2c65aa4ccc47817ac00b542608fedd048a9bf8abb902c2efcf3976eca42c2cc5779c94d121c656a901bdd1a5f5d6f1b116d108ac078c527f6804a2178c6f2b397949c8e37bcf3e00bbb68bad62061c5ce1f19ede2702ac938f8f9394579a2b72d85811325d7cfd11fdc7726f1a3cf312ef7089175b0e49966be2cde46fe000ef2039e8c8f14d9850cc018e22e1f4832da4ffd26896f620f75100e79e102a0970d632c7e817c258f96ea8559e07bf68729626025ed1b077e28507e0cd6398069ed7109fe9d6922e6cddf040838fd0bfb4dc4d58fa73bbe609801b430d99d1227ad26f938af661eaf6799015b8e7751c0a1f1f91497683cb0ade2944af63ae2f7f5af7fd1703491703507437cc743ab325bc10f65f38b30fdafab4953d03d40dd86210a06627d83aed0baf94635720c6d9d4c6ddef53f7636ec0f9c7f9e7180171f27e3f50af27d5fce36e9f9c5f77a17cda244cc20c41dd091c21dd16c2a31fac7fa8d73ced2666a19b0780b3288b3ea16dd6e46d8e532e132615d5022adc25e23ccd4bc7dff4bce8090fc9b3ff248ee5741ac681b29ed1c4350531172aad0b4d0482b84f0fae6090fc03a02bd703437c4ab1a0344cb8df29c4bdb58d281b01c3315f8b093985fc890f14255b3c54dbcb313a4f542c3352253147cbd225ea1827f3aef6611afbe1d7299f9f24a852d60f6fafd07eca8802e2824f64cf1398244e91b20f581f9529703c14a4c5b72c803db630fec260366136b84f0782535b194c37b8d2c8a0ed10cf5539802b6a88700cb9181ef2decc0aceee0e5ba0eacd0948ff46b356645cc0870a04412e8685f2b36383848b3305ffccfb408ba5b7f314dcd94c8bbcb0b0b278aa8a9e03a03a8a538f9e0e8d6f8dbe8d12b4f4f1dc782850ff89bb33e15fec0c8a81793999ddf9072d9cf35cc52a75f6af96d69600661079405f35e5e19937e33986557932055b548cc6af508721b08444e5bcad029822cf22f2e0a0b0fafa1bc461797b0014b0f8797ca7f931db881a13d034e631ce0e00bf8eb165c6f25e32c3e00a27b554e478cf070c73f3737fad0eb194bd1fa729abc7c9573307cd7f139fe4cb0e5fd36240d2f356a374f2c916eb0caab9a1291af55cada2a45f02f68cb063bb9eb90c8ff8bc8a49d8be82f381fa2c90dca6ff079f3a1c5a0d0fbe021fb9f9f93933c1df3961de3ecf2893f57e8a529954e06d15d0a55d0855f5715d3a2a5e63d17c0623bcc72ccff149e5a6020bf6837088350df9626d33e0fe29516a383e99e6035228cb4a0147471c5484d96ca62996584f2da85c0cf43499e45aba9feab4fcc9cde84979c757854c9db6f870e5b8c7e56c0070f5840a9e0ce447ff7502d907a1f35b8a68c6cbc3c0611327ea942862750d06060e7dc5839aced53e0326d1270ab6d1dad6266dcf6d485ec2187f5088f1450fee1c25db88f8552d8b3e9687da47edbc3e7034ef324e4b2232c41af06f24b2161764cddb8ca7740d69fd77c18cbf70c33f55d4c7d550fd631b64a9b65284670621a8fa819582072f27347b362cbfe3c20207844cb0200da1ddcc857591dada1a0c2e2a516f8d1501419616be826bc9ac2b57733012c45f5fdd00df77ce893b27cf3d84386278935a0af4ebc29d5c10f13893d6011fe39b9f96ad585f5456331f0985aa1cfd3b340d2e9975b6b2520b15c0cde8510a0c6dd9955ac0559f20b5054df3ebef479fd68b74b25004c49c4b49f7992d3cf68042f88b4a6f84c6b1912419d074ed347cc4afb95e1cfc7661b4863a2e92721682e36396f19bf68a2c28240c5b34608d9ed823fbba6552c84b8a4f113d14f60ee4df3b1684f465ddd317110bd463416bdd136ea2463741267492f70b61d676e33723073e3661d62ddc6430470d5ae292f56cb7b2471251c0845fa2574627305beb49df11c4160c1f4eec17199a0b949ffde3d441a0bbc221d3f41ee3d29f383e61036621c7b90a0e434e27ef5b46b85d99a3b5346b32a68e5e73c804285fcbb3e12a7036fa4c5aef220e2b072b924717a3ad8de4b009c71d3fc8e7748ffbd822d22a48a08a9288f3156a184691938fc57b050793b21adbb1adbd87e4ea55e83e121dcc23051be3a4859021ae4f64b70633bb49cf71b6692b803d0b5f56050109509dea131a2344f56c8b16d127776766bc300168cc7e1d6c71fe2e8c589f8cfc28d0bd426c3a2edd0d3629ded6365f7e85a7309e3f2deaec72650a3827df6c49cb28d426980bd6ff74d91836251c33859459c838425abbd68cb9b11d3f370d3dda0b1440d0fe9eec224d0d462eab1ec2304ac5e8bef12587effc24fc49dab88bf7b0e192253349c1960300381a7e56df229728d229c1825e8f5b29dfd474599b75b83f53b3a290947b660864d83258abccad089c13db242f76254a6197e8d45059df18bedff2634cc64924d098d572f5779083ccd4a92477e2a2988e4b21040ba75f81823358191d179a0b3bff183b15a687a603fdb72c3e0fdf610a9c494528dd5602a819b138a9eb9924a45104416c6872464060ad369a05c933e9271e0a15298bad2d9828f58845a21cdabc6a0dd20bd6c122d086452d1f3336b1c6191f211fa8d178363989eb8dfb1eddfffc05a60d098493c8e156c581feeff6e90701165d36859b189edd36a48511f143fc4c3fe19e8793107c3f1bd1d615ce2ad3e37c8f010229da439cbcd4d801b01b0451825f7785fcf0f1ee2bcdf2ee9075f8d2eada866acdfe7abb9294ad1c145fd5b495b50e8e8f55a2330fe209583813ed76d831cf77f3b1a04144785210d1038162a9d25a1d1394444e7d834d9716f16c21ba45fd407c03de343c52f7269eaf8a101e306f1944c6ca1b1e85615ce14799ee179be987231760956f7613236063decd76cdbca0c5609d6006a2cd8d8522aa37b2a157079ab8cc362943852328fc72f83652dedcc849fd98da5930c53fc2834dc2b8f77b193b49af29d16e18dd52dde4ee71fb3e88ff5dfe642953bd1765e18e0f61105ea1ea05bf32ba7c1f6214eaafb84806de8e7a3cbcaeb902eef1ef767162322d653e6c32e73019ec1e10cad7c7190b64fe84acc185b0654c2671906757f97f7a9dac45f4682461d41d4b51733dea2cbb186add3bd39d0d6d3115db1fb94aa79848836dcc90d7fa9f0a9b1f67c66ae60f57a1228fe91f1ac040aa4e0f246e13678e4e39b25d2794b629163a7bb77ed0b709079bee1a2fdbc3ae24f67bcf8a6abd29861d02e21becff1d74eb4a4aaba225759bfd3725b5fecc4d268cd82cf5a5e104e867b8b45e5ccb0dbc70c75389cd6d2a49715006b89d263fdab4e9cbe0900824b1a67ae1cb25b60084ba4296ed01db04f77f3e565fc13b37933b813c0ade97524e441a557ca3d41761b22d801228b9072f033921707e44b3654b7e6e0c0067270b0126ab86f5dc0e0d66932925f3af46c01a98e06b593a1c9c9d19f8731e84b20a3a5416d226d3010c9dc7775769618d03db66bcf6f9eea43ffd824ea1bd6bc16de1cf2d0078080370902cca05fe09a88f6acfa98b7fadfa052ae3162edd202f71568c2bf778ce0463365dfbf30f672b5d121fc2494fba75318cca269a80ec11741cc75659204011b95db64630c7243759ceee4bb73c892ee19f1cef04da4a924f645d9b6bcf341635cbae4e1d6a4f83692f2d428a7377d99393caae55e1bf8585cfcfc4ecc801122dcfd2d9e22688136469021483815ea11e2d001bcb78a32dd680d843537033057fdf51a5f1f18dced8a4a2a2b71edd368a419dade3094fe6b238a2aac50fe02e794901e81941f76ad941304eeb0f6b5d3e815e2fbdc999156ee69b16f693d021a66215ee45a1a956c339af70d3738511dec6693c29c2f2846f43f174e941d5251cd60ce9c0a73ad67124c1e7fbfeb6bf0d8a923151a428103d41b2e60a24f317b4fd9d062ae83c8b4355a932a01b9dc7b64e123e659d2d8e4cd19b649c0bc21dfaafc8cdacb73f80b4fc16c7ed42af395a7cd98e94118b8e2ddd2f452add010ade66c3c6775af764855ec1530004a1ec634a6331242382f4a24270318a9422034892ca2b5fe66ef4206128bf1503ff031f200e60676c36cbd2a822ecef03380eea8d63b0a2cf2213e6a1898c67cf5ff978e073c77b41176ae75e7535888b310f825fc9b325460f1fc36cb0eef36d7f9726ef06fba28f3336fd4016c6e19189201d1f19ea33787cb94fb2aa222010c73760d92d7630cebd20a71d27316b48bf238a457d111b6bf7e7ef66cee12b7f343b818f2e42da0ad9612168fb339ca12626988a0fa71781d64aee0364b96866d32f8463806a6b414c759bc3857a455c7c065fd651033f67f7243cc71f3eaac9003bf069a08c47283ee64c0e1b40a35a610981bfb5d4d601520598b898b0c8bf2f95080755067a7b3a3b7d23529bec13d120fe9e9ab60a56dc7fbc8e9ac056e92a88ef2ac767dc9edfd4ca493a9360d3c32e9072a67ee9843f95ab929184dac4b3297afd5ace6b1b3b7a86e3a85754b8542213655d2bd45c3e7fca4fdfba2c4f95de5334807d26ab801181de4816ec934e11e5b4d6bcf441d2ad8dd1b43c10c276cf413d9795aa5702df80a5fc12eed2b80517c2a9754905b196847626eef4168aa08d0baf57be4bcf8cbaee15fb72f27829763c7de6250a18290eb9a30ab63e753576091460991670b20b31d9cb38325e0819a44fc715a6b4d7c4c85724447e00345b1f6e89df5ef64a8f42ae443ea04820b7bcbfa7d9b1179794da1fabb885ad6001df3cd65548fb30763fce0ed5261c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000183ab34fe72108d2a6ee9e85fcb3564f39690b716cc55480c7c0909e1974a92d111498f47cc6c00858191c75326527dddeb14d09f9566c3e7207cebf51944f491448cfdd1841420f9461d005ab426248153c144f9a8647073944a1b408b878690f1e8ba7a6df8959ec1cab606b2840e52ee24340302c3c7e011705cdf965b05827c133ec816b324745a262e9abd2a14b6734170182d8912cd959093725c22ce603b3d04202712d641eb04f6eefa0255d2aa3bc03a15918fa17670ce046363b2b14d4f3f46e143934ea955a92f0b1ac3eeed020d7974a734a54ee50635ec0651625057654ab9941145b00a81c2ecfc3aae97342005f895f23f6d00f8398cc10a31e69b6a13df93cb5cb8f51593f0f0d54178c8335bb3ef79adadec1de12fd6a7e232ef6d6a0ed066b74bc8a9cc451e7f78c2a66abbe2650973c54c2f0927ad58220b74e533ec600ac7029dfb06f83fa1b51e27431d44d356cb24a8fefeb66cec30e4b9ba0dcc419a06e78401ca786e32ab3356438f6c3740cb650a480b80f45992925771fe1353c822a41e568c60aea5f04c627e1606a7e2a0a3fb3e33a72a670210407fab96edc5328ee803bc51f364b0efd901e8caeb37efc55fdeed1e53e112397f6eba49bba40613cc601fb6002feffb535660fe1578d50def81d51252ddf09be072516a9e60e087ab85dc48a02a1997b312a3d7ffc2831eef79e3baa98b6069957b4e3012bb26ce1664a16922f84e64af1b1a5357da7b7f0f5fccea901f7135737415a3111d53d67fab50a33fc3f36af31911c29369e7d153be011c04a9527c752deaa0fd4aeb0485e847cf0fd6f6b8b8e037876177cc0cc2a705f9951c42e9174dd29eae5a6d0ba968b4a5f24417cde19e64f7ffdc5d6cf9dfd7eb4bfe513ba9a4b015924c6ccd9831bf8d291f352c26d9ad900069bd8dad15e120d06a20a22f9ca9606e60647e0db96274b192524eae401f1c0a7040066132d6d949538057d65eb1be9b19886cf172bf0ee21904e7e47816d925acf9a1a39952e979c410f829a4b5583a48b334fa75ef3c7e8212c5ee085ef071d8c6e0d931d2c326a6d1d5e0fe77b6c7216da0631d37ab1aaeb11c55df506468e5dd29acc8476fbd29f1643996f6d0a3c0cdf36f8658d660467966852e8d7cbc64105e4f01806db6c140a9ea1f216d222be39a73ea3f8e66ad9df67442c5e49be9daf832e511fbecedc04c7d4bed2334cbce80f6cf473c0b589b2cfdebb621d525c16c64cf0be99ccba17bed6f3f1484a498f53a65d7501cf22b3b858e48e06cbd63c2026d3e27dd58d2654de8d3a6ced69ea1c8932e5bd39053e16a032f0e0578de55a678723022cd10c79c497102698211afc60aa5ac18fc30bfcbcd4ae03783caee4670db837881a11e55a566ee1d72f8d5980f1e0db07358afb36207b78b5c3bf1b5abfb0108f7f043c17f46a7ddb9a758713bfd616e4df73dedd9e7b9d5d42cad5311695728b7124a27c4861fa8c532e5ff20d7193e2b08ebb3aea5c586a024465a73f2f2e55ae21e006ca0ab56430b664514a4dcf8c00448ea141298b5717337c561df7b5e1430ee2df10ae989eb86ba75e8a65e60d3c8aa0db5b0611f9efe27a3bcd8ddd9f8d20cc71693018e2558bb27568fc5a4a8b3e53a27036052695ae52b4f3002f9e6d022aa08eb1b40acecd5a104aa564ebe87116fda1edda52dd8ca47c6a7b8f097d24e90357f57281f23353f0827b90b66b5fed939ed8f70df8a3bf087dbc21f6a011705bb2148d14b8ae7ce0653f753ddd1c21727523ccbe7da6293ccd025387bd0d4b192b23ca726fdfe8a8c74d16585859c993c25b4731ebcf9c3b503eccf8180a7b4b62f14906c44ca7e8a99eeb7785a95720a60bd1adb6b359bec1bd170dcf2020c602d420c91ddd3e8114d0c3179e1f570744d9ecd8d613e883740899c0c311594a7e2cd8c5d13c33721052b15660a50a4ea375f93f97641cc58959797b13',
            commit=int('0x01e756223c5baeccc9076912dcb9c1dc0d6f1c24187f678682017e93920784e8', 16),
            domain='domain.com',
            pubkeyHash=int('0x17655f0139cacecc80f4143fd28e7107ce6038374ea9d5cfcf5d3fb5ce0086e6', 16).to_bytes(length=32),
            is2048sig=True,
        ),
    ]
    tx_data = TxData(
        to='0x96B4215538d1B838a6A452d6F50c02e7fA258f43',
        value=123123123123,
        data=b'123123123',
        operation=TransactionOperation.call,
        nonce=0,
        deadline=11123123123123123,
    )
    res = await blockchain.execute_transaction(
        samm_address='96B4215538d1B838a6A452d6F50c02e7fA258f43',
        tx_data=tx_data,
        proof_structs=proofs,
    )
    # TODO: uncomment
    # assert res


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("start tests");

    loop = asyncio.get_event_loop()
    test_parse_body()
    loop.run_until_complete(test_parse_member_initial_message())
    loop.run_until_complete(test_parse_member_approval_message())
    loop.run_until_complete(test_dkmi_extraction())
    loop.run_until_complete(test_padded_emails())
    loop.run_until_complete(test_msg_hash_convert())
    loop.run_until_complete(test_sequence_genration())
    loop.run_until_complete(test_prover())
    loop.run_until_complete(test_blockchain_execution_transaction())
    test_tree_generation()

    print("end tests");
