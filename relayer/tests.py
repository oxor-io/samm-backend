#!/usr/bin/env python3
import asyncio
from email.parser import BytesParser

from dotenv import load_dotenv
load_dotenv()

import crud
import db
from mailer.dkim_extractor import extract_dkim_data
from main import parse_member_message
from main import parse_body
from main import extract_tx_data
from models import MemberMessage
from models import TransactionOperation
from utils import get_padded_email
from utils import convert_str_to_int_list
from utils import generate_merkle_tree


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
b"""DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=icloud.com; s=1a1hai; t=1729173732; bh=tT+TucubgvFM8RdXdC2h4AY1qF+wUY+Hvp7ydoZaHH8=; h=To:From:Subject:Date:Message-Id:Content-Type:MIME-Version; b=klBw8OFqfvvj87jKIb/MXkkSKK/TDPHzZG4cZRyZ1BzA+fzpsy7j1iDBzC8B1Y52U
     1VwFUmJFFxMjebdVreIzivpds7+an6MdwqBpC5+PDdECqv+/oyo3uy03gK2fewLCVc
     G/xfe7+docdWq6vaN9psDXC8BT/PqmdoJv0uegMV/p2M2ZcLp2tSo+W889vanQhITQ
     j8vsdrW9W/js7po8gXVBTRB4eOyBnVDGvOZcoDIDSc2BpQQQFQ0vkLihNALSw+fQBn
     7y/ED8iz2/8WmvfVZ+N9bEmnxg3/BxDJ0s2dVHvy2/vATKReYv1qjkN7yjZM3RijEj
     SiKYq/GkluStQ==
To: ad@oxor.io
From: swoons.00rubbing@icloud.com
Subject: yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68=
Date: Thu, 17 Oct 2024 14:02:08 +0000 (UTC)
Message-Id: <BD7C7F1A-A229-4AD8-9F4C-F0FE5DEEB72C@icloud.com>
Content-Type: multipart/alternative; boundary=Apple-Webmail-42--6364c478-2d2d-4d92-86dd-abf68e6baf8d
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
    assert tx_data.data == '0xa9059cbb'\
                           '0000000000000000000000003f5047bdb647dc39c88625e17bdbffee905a9f44'\
                           '00000000000000000000000000000000000000000000011c9a62d04ed0c80000'
    assert tx_data.operation == TransactionOperation.call
    assert tx_data.nonce == 34344
    assert tx_data.deadline == 123123123123


async def test_dkmi_extraction():
    # https://github.com/oxor-io/samm-circuits/blob/master/builds/samm_2048/Prover.toml

    header = [116, 111, 58, 97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 13, 10, 102, 114, 111, 109, 58, 115, 119,
              111, 111, 110, 115, 46, 48, 48, 114, 117, 98, 98, 105, 110, 103, 64, 105, 99, 108, 111, 117, 100, 46, 99,
              111, 109, 13, 10, 115, 117, 98, 106, 101, 99, 116, 58, 121, 120, 68, 110, 83, 110, 73, 54, 71, 84, 82,
              115, 85, 50, 68, 120, 111, 108, 47, 85, 73, 101, 71, 101, 115, 84, 112, 89, 81, 81, 104, 70, 80, 121, 52,
              116, 117, 88, 70, 43, 87, 54, 56, 61, 13, 10, 100, 97, 116, 101, 58, 84, 104, 117, 44, 32, 49, 55, 32, 79,
              99, 116, 32, 50, 48, 50, 52, 32, 49, 52, 58, 48, 50, 58, 48, 56, 32, 43, 48, 48, 48, 48, 32, 40, 85, 84,
              67, 41, 13, 10, 109, 101, 115, 115, 97, 103, 101, 45, 105, 100, 58, 60, 66, 68, 55, 67, 55, 70, 49, 65,
              45, 65, 50, 50, 57, 45, 52, 65, 68, 56, 45, 57, 70, 52, 67, 45, 70, 48, 70, 69, 53, 68, 69, 69, 66, 55,
              50, 67, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 62, 13, 10, 99, 111, 110, 116, 101, 110, 116,
              45, 116, 121, 112, 101, 58, 109, 117, 108, 116, 105, 112, 97, 114, 116, 47, 97, 108, 116, 101, 114, 110,
              97, 116, 105, 118, 101, 59, 32, 98, 111, 117, 110, 100, 97, 114, 121, 61, 65, 112, 112, 108, 101, 45, 87,
              101, 98, 109, 97, 105, 108, 45, 52, 50, 45, 45, 54, 51, 54, 52, 99, 52, 55, 56, 45, 50, 100, 50, 100, 45,
              52, 100, 57, 50, 45, 56, 54, 100, 100, 45, 97, 98, 102, 54, 56, 101, 54, 98, 97, 102, 56, 100, 13, 10,
              109, 105, 109, 101, 45, 118, 101, 114, 115, 105, 111, 110, 58, 49, 46, 48, 13, 10, 100, 107, 105, 109, 45,
              115, 105, 103, 110, 97, 116, 117, 114, 101, 58, 118, 61, 49, 59, 32, 97, 61, 114, 115, 97, 45, 115, 104,
              97, 50, 53, 54, 59, 32, 99, 61, 114, 101, 108, 97, 120, 101, 100, 47, 114, 101, 108, 97, 120, 101, 100,
              59, 32, 100, 61, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 59, 32, 115, 61, 49, 97, 49, 104, 97, 105,
              59, 32, 116, 61, 49, 55, 50, 57, 49, 55, 51, 55, 51, 50, 59, 32, 98, 104, 61, 116, 84, 43, 84, 117, 99,
              117, 98, 103, 118, 70, 77, 56, 82, 100, 88, 100, 67, 50, 104, 52, 65, 89, 49, 113, 70, 43, 119, 85, 89,
              43, 72, 118, 112, 55, 121, 100, 111, 90, 97, 72, 72, 56, 61, 59, 32, 104, 61, 84, 111, 58, 70, 114, 111,
              109, 58, 83, 117, 98, 106, 101, 99, 116, 58, 68, 97, 116, 101, 58, 77, 101, 115, 115, 97, 103, 101, 45,
              73, 100, 58, 67, 111, 110, 116, 101, 110, 116, 45, 84, 121, 112, 101, 58, 77, 73, 77, 69, 45, 86, 101,
              114, 115, 105, 111, 110, 59, 32, 98, 61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

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

    signature_limbs = ["0x93374628c48d288a62afc6925b92b5", "0xfcb6fef013291798bf5aa390def28d",
                       "0xdf5b1269f1837fc1c43274b367551e", "0x19fbcbf103f22cf6ffc5a6bdf559f8",
                       "0x9410405434be42e284d00b4b0f9f40", "0xe3b20675431af3997280c80d273606",
                       "0xdad6f56fe3b3ba68f205d5053441e1", "0xd4a8f96f3cf6f6a7421213423f2fb1",
                       "0xda09bf4b9e80c57fa7633665c2e9da", "0xd5aaeaf68df69b035c2f014ff3ea99",
                       "0x02b67dec0b095706ff17deefe76871", "0x2e7e3c37440aabfefe8ca8deecb4de",
                       "0xb788ce2be976cefe6a7e8c770a81a4", "0x8e76535570154989145c4c8de6dd56",
                       "0x1cc0f9fce9b32ee3d620c1cc2f01d5", "0x491228afd30cf1f3646e1c651c99d4",
                       "0x5070f0e16a7efbe3f3b8ca21bfcc5e", "0x92"]

    _header, _header_length, _pubkey_modulus_limbs, _redc_params_limbs, _signature_limbs = \
        await extract_dkim_data(demo_eml)

    assert _pubkey_modulus_limbs == pubkey_modulus_limbs
    assert _redc_params_limbs == redc_params_limbs
    assert _signature_limbs == signature_limbs
    assert _header == header
    assert _header_length == header_length


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
    msg_hash = [121, 120, 68, 110, 83, 110, 73, 54, 71, 84, 82, 115, 85, 50, 68, 120, 111, 108, 47, 85, 73, 101, 71,
                101, 115, 84, 112, 89, 81, 81, 104, 70, 80, 121, 52, 116, 117, 88, 70, 43, 87, 54, 56, 61]

    email_subject = 'yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68='

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


async def test_parse_member_initial_message():
    db.init_db()
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
    assert member_message.initial_data.tx_data.data == '0xa9059cbb'\
           '0000000000000000000000003f5047bdb647dc39c88625e17bdbffee905a9f44'\
           '00000000000000000000000000000000000000000000011c9a62d04ed0c80000'
    assert member_message.initial_data.tx_data.operation == TransactionOperation.call.value
    assert member_message.initial_data.tx_data.nonce == 34344
    assert member_message.initial_data.tx_data.deadline == 123123123123
    assert len(member_message.initial_data.members) == 4
    assert member_message.initial_data.members[0].email == 'artem@oxor.io'


async def test_parse_member_approval_message():
    db.init_db()
    await crud.fill_db_approval_tx(first_user_email='artem@oxor.io')
    uid: int = 123

    member_message: MemberMessage = await parse_member_message(uid, approve_eml)

    assert member_message.member.email == 'artem@oxor.io'
    assert member_message.tx.msg_hash == 'yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68='
    assert member_message.initial_data is None
    assert member_message.approval_data is not None


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    test_parse_body()
    loop.run_until_complete(test_parse_member_initial_message())
    loop.run_until_complete(test_parse_member_approval_message())
    loop.run_until_complete(test_dkmi_extraction())
    loop.run_until_complete(test_padded_emails())
    loop.run_until_complete(test_msg_hash_convert())
    test_tree_generation()
