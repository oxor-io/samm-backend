#!/usr/bin/env python3
import asyncio
from datetime import datetime
from email import policy
from email.parser import BytesParser

import conf
import blockchain
import crud
import db
from mailer.dkim_extractor import extract_dkim_data
from member_message import parse_member_message
from member_message import parse_body
from member_message import extract_txn_data
from models import ApprovalData
from models import MemberMessage
from models import ProofStruct
from models import Samm
from models import Sequence
from models import Txn
from models import TxnOperation
from models import TxnStatus
from models import TxnData
from utils import get_padded_email
from utils import convert_str_to_int_list
from utils import generate_merkle_tree
from utils import generate_sequences
from prover import generate_zk_proof
from txn_execution import execute_txn


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

demo2048_eml = \
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

demo1024_eml = \
b"""DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=yandex.com; s=mail; t=1730212994; bh=7S8rs22kKpminHR00NMjbzOCbY5cbeOIG4QteRHQG8g=; h=Message-Id:Date:Subject:To:From; b=kAPtf2OeJNjQZsP3PCIfp6OFSDTxcFJ2EnW63QXmLHAxyQyt+wnGyrORDUZSusBsP
	 iFijNMiBsaNOFDKRfphuaRda6CbKLAaEl/cxJBiLGQZ7bvfa5BJIZ+sG2WCZPxjVWi
	 Rby+zWYhgKnwn9hrJ91oxfhFuyF8tYSWWXnyjbao=
From: Dry 914 <dry.914@yandex.com>
To: "ad@oxor.io" <ad@oxor.io>
Subject: hHqTyYhaHOM1/52r43r+AeTIo6GQIvXGYZCY0VwjzVo=
Date: Tue, 29 Oct 2024 15:43:13 +0100
Message-Id: <1227201730212975@mail.yandex.ru>
Content-Type: text/html
MIME-Version: 1.0

test test
"""


plain_eml = b"""Delivered-To: samm@oxor.io
Received: by 2002:a98:afd0:0:b0:219:8ba7:644f with SMTP id z16csp1822960eil;
        Sun, 15 Dec 2024 21:01:28 -0800 (PST)
X-Received: by 2002:a05:6a21:3287:b0:1e0:da90:5f1f with SMTP id adf61e73a8af0-1e1dfd58f6emr17446330637.16.1734325287938;
        Sun, 15 Dec 2024 21:01:27 -0800 (PST)
ARC-Seal: i=1; a=rsa-sha256; t=1734325287; cv=none;
        d=google.com; s=arc-20240605;
        b=YS0zhIJZf9zjQEutblYXiu5fS+4OYr0LZRfg4Z0kdqjPC8gWJgN+D8gLdHw0/mtTGD
         sumMvH/3Uk5fp7xfT6N7QT2igeDgoSa7y4ZEuelNvrLdaKRFeJ2hrnTq34Zfc/9P8OB0
         NYm3LHXteAD9eSDjEzW3v3dsCo3dg+VhMA9XOfjZHY3MrcUVQS1MKqu0gN9Yk3Yg9Jdk
         YHv+i+gmINgLq53jUmqY0vZo0csfBZ3r/16KXk0lekiMAYrUM6a79/pFlDGs12I0eruh
         NUj42sX6Dh5nLNU5DKLetrTVkyoiIgu4ldRxVzUGpsFLGDkJ6mEzgoGc98JS2PiGNSQv
         3OXw==
ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20240605;
        h=to:date:message-id:subject:mime-version:content-transfer-encoding
         :from:dkim-signature;
        bh=eG6hWw8Qs69j+BqDJVblYmfkkVXvKVcD1irUuoQP5VI=;
        fh=moYPGEXsPPB6a64Iv50+dgEaJXETlJbJutRWBIp5fHs=;
        b=X70RL5WFwT7YVv/Y26tNbOYGskQk/7vUYRTRCTK+UISnUdYH5Ockg/TYdUvZEIzfXH
         qpaYwElyBXEojF4BsP3+cN/i5jU/08jMnRE6ByFkv+wucysSezIaiI0QfMrOL+cGmo5K
         5ZQmFQiU7rybC23yn71H0u7ZORcKP9KgHpQryex9A+43ACvBVBgoTGdLlpRmi4uFEqi4
         grraYi2b64NJlG1SLwy/uO3rt/WMDMGiija1dbqy5/AavsnLJZ1/ZDb61zLsAijO8+5z
         SyIUGHsTbaFRFGUSrPttNEQGuaZZA2omztvVCW0ievpCB4vXj/LDpblseMvwndE5RIgQ
         EJ3A==;
        dara=google.com
ARC-Authentication-Results: i=1; mx.google.com;
       dkim=pass header.i=@gmail.com header.s=20230601 header.b=U7WIyBGq;
       spf=pass (google.com: domain of svetlana.moisienko@gmail.com designates 209.85.220.41 as permitted sender) smtp.mailfrom=svetlana.moisienko@gmail.com;
       dmarc=pass (p=NONE sp=QUARANTINE dis=NONE) header.from=gmail.com;
       dara=pass header.i=@oxor.io
Return-Path: <svetlana.moisienko@gmail.com>
Received: from mail-sor-f41.google.com (mail-sor-f41.google.com. [209.85.220.41])
        by mx.google.com with SMTPS id d2e1a72fcca58-72918bcedc3sor1807093b3a.9.2024.12.15.21.01.27
        for <samm@oxor.io>
        (Google Transport Security);
        Sun, 15 Dec 2024 21:01:27 -0800 (PST)
Received-SPF: pass (google.com: domain of svetlana.moisienko@gmail.com designates 209.85.220.41 as permitted sender) client-ip=209.85.220.41;
Authentication-Results: mx.google.com;
       dkim=pass header.i=@gmail.com header.s=20230601 header.b=U7WIyBGq;
       spf=pass (google.com: domain of svetlana.moisienko@gmail.com designates 209.85.220.41 as permitted sender) smtp.mailfrom=svetlana.moisienko@gmail.com;
       dmarc=pass (p=NONE sp=QUARANTINE dis=NONE) header.from=gmail.com;
       dara=pass header.i=@oxor.io
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=gmail.com; s=20230601; t=1734325287; x=1734930087; darn=oxor.io;
        h=to:date:message-id:subject:mime-version:content-transfer-encoding
         :from:from:to:cc:subject:date:message-id:reply-to;
        bh=eG6hWw8Qs69j+BqDJVblYmfkkVXvKVcD1irUuoQP5VI=;
        b=U7WIyBGqoNj7rOJOpKIMa4VnDscmXhfR01HKTWYchKrrJIatfr5JnVGz3iAkYm0Hrd
         r9UXxsxckNqUd7wg3QhmmQoPUp6SMKCnczHsXWVREbuw8Y2vQZXIdmhpWzSwVLdQb2LE
         MUPnYZlgk2jEVQqt0A8AGyVgmOnwqK6esoO3rOfTYjLy2IoIc7YnkZ+E1K3xgSpBC1wI
         bxJ6gUW+87pcDMHgif8cRnmpgq4H8jn1QoWZ+/wm47JtfFjr7z/lvy9IAh0Cz1dDLfmM
         Lv8xQCo05/9qyC+p0d8aMfRLBixHdQw8drTt8/xKDkhLvV7VATosVyaNHqoB0pUFjXH7
         CUIw==
X-Google-DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=1e100.net; s=20230601; t=1734325287; x=1734930087;
        h=to:date:message-id:subject:mime-version:content-transfer-encoding
         :from:x-gm-message-state:from:to:cc:subject:date:message-id:reply-to;
        bh=eG6hWw8Qs69j+BqDJVblYmfkkVXvKVcD1irUuoQP5VI=;
        b=NIvBuiVHBz+AmjY0c6SQt4OFLNGXSqHpiZZJ+yylZ3G9ONmh3mBAL+FvdIz61Zo0kx
         VpiSCaAF0BOo9THQVWugBDl9RfI2q4ucyQaAcl5TPdU+677vEYyc21+tQJoHz613oqOi
         vIUSqsTh+nJK8iCABx839SYyeLVbAr2sxS7rb2s9akpZZMp0uS6rzUBrO0zJARL5JhDE
         tVnO1T+COuPhhlDZjaksQeeyb+1N7Lm1N+BmVmGZ0bURD6Me4GhGvTP2BSh+/vu3mm32
         BL8Gvwkv//zbUdqQIkBPOSCgndSkbWHor/1DAR1ooLHGdnlkkmb9UCbSjdLki6DEp5t5
         HvUA==
X-Gm-Message-State: AOJu0Yw/PiWBFTCuD+UeGI6MDeKTBxiTlFyqCaeDbvDGoJo6ChVuG/H6 SIUYebsxmYU2KrHM+vLvj3hbCgoy7HX4ZLGuCGaLo24PiatPiYiuLtW13Q==
X-Gm-Gg: ASbGncskcGo15KY5q74lZstgIO7j+qMnMAsDajig1/MjgPoWsNNgkD4qokB8UwJ8/49 jf3apuF3t0Zm28Y+X+z9IYZ82IHaX9sLiqdnJteCv3nvfWCokO++gGhKl011DCaC8dBYObLjgZD TSjXKJOl7GNnmCLvyfixmardRWJDOBL92HN7JSbuXjiVq/SvbZFDzIVbaltlV6tMVWnPHgKPVdp pRLLJeaB0xpwiPWVr8g8q9n1/MAM2ys53Pwvsw3cCw/2wXIzRomWvS4TmXSTiJXByYgcGJC63jS VeYX4iftKExSCpt1r0YDRAJe0U1D+67OTNfQ2mRJ3Fp2PGeQSY4=
X-Google-Smtp-Source: AGHT+IEu0Zw9mcqIYGJ9UoStfoxaagfuSIoJh3uLZ3X9KF6N/5KaIO6tTajKLS0Dl0teX2uTKYZyIg==
X-Received: by 2002:a05:6a20:9148:b0:1dc:c19c:b7b0 with SMTP id adf61e73a8af0-1e1dfe00077mr16976405637.33.1734325287127;
        Sun, 15 Dec 2024 21:01:27 -0800 (PST)
Return-Path: <svetlana.moisienko@gmail.com>
Received: from smtpclient.apple (ppp-171-97-42-232.revip8.asianet.co.th. [171.97.42.232])
        by smtp.gmail.com with ESMTPSA id 41be03b00d2f7-801d5c0efefsm3337021a12.52.2024.12.15.21.01.26
        for <samm@oxor.io>
        (version=TLS1_2 cipher=ECDHE-ECDSA-AES128-GCM-SHA256 bits=128/128);
        Sun, 15 Dec 2024 21:01:26 -0800 (PST)
From: Luchik <svetlana.moisienko@gmail.com>
Content-Type: text/plain; charset=us-ascii
Content-Transfer-Encoding: quoted-printable
Mime-Version: 1.0 (Mac OS X Mail 16.0 \(3826.200.121\))
Subject: 0x2b83020ddf8a5bb7ff3eec3db08761384efcd3fde7f046e3d9157585b3b4e525
Message-Id: <F7ED3F21-A678-4FCB-A5F6-8DE910BAB4E4@gmail.com>
Date: Mon, 16 Dec 2024 12:01:14 +0700
To: samm@oxor.io
X-Mailer: Apple Mail (2.3826.200.121)

samm_id=3D3;to=3D0xD4aF3d17efd18DF0D6a84b8111b9Cd71A039E4a4;value=3D1000000=
000000000;data=3D0xd0e30db0;operation=3DCALL;nonce=3D23;deadline=3D17349300=
48;
"""


def _create_test_body(samm_id: int) -> str:
    txn_to = '0x07a565b7ed7d7a678680a4c162885bedbb695fe0'
    txn_value = 5000111390000000000
    txn_data = '0xa9059cbb'\
           '0000000000000000000000003f5047bdb647dc39c88625e17bdbffee905a9f44'\
           '00000000000000000000000000000000000000000000011c9a62d04ed0c80000'
    txn_operation = TxnOperation.call.value
    txn_nonce = 34344
    txn_deadline = 123123123123
    body = f'samm_id={samm_id};'\
           f'to={txn_to};'\
           f'value={txn_value};'\
           f'data={txn_data};'\
           f'operation={txn_operation};'\
           f'nonce={txn_nonce};'\
           f'deadline={txn_deadline};'
    return body


def test_parse_body():
    msg = BytesParser(policy=policy.default).parsebytes(initial_eml)
    body = parse_body(msg)
    samm_id, txn_data = extract_txn_data(body)

    assert samm_id == 1
    assert txn_data.to == '0x07a565b7ed7d7a678680a4c162885bedbb695fe0'
    assert txn_data.value == 5000111390000000000
    assert txn_data.data == b'0xa9059cbb'\
                           b'0000000000000000000000003f5047bdb647dc39c88625e17bdbffee905a9f44'\
                           b'00000000000000000000000000000000000000000000011c9a62d04ed0c80000'
    assert txn_data.operation == TxnOperation.call
    assert txn_data.nonce == 34344
    assert txn_data.deadline == 123123123123


def test_parse_body_plain_email():
    msg = BytesParser(policy=policy.default).parsebytes(plain_eml)
    body = parse_body(msg)
    samm_id, txn_data = extract_txn_data(body)

    assert samm_id == 3
    assert txn_data.to == '0xD4aF3d17efd18DF0D6a84b8111b9Cd71A039E4a4'
    assert txn_data.value == 1000000000000000
    assert txn_data.data == b'0xd0e30db0'
    assert txn_data.operation == TxnOperation.call
    assert txn_data.nonce == 23
    assert txn_data.deadline == 1734930048


async def test_dkmi_extraction_1024():
    # https://github.com/oxor-io/samm-circuits/blob/master/builds/samm_1024/Prover.toml

    header = [109, 101, 115, 115, 97, 103, 101, 45, 105, 100, 58, 60, 49, 50, 50, 55, 50, 48, 49, 55, 51, 48, 50, 49, 50, 57, 55, 53, 64, 109, 97, 105, 108, 46, 121, 97, 110, 100, 101, 120, 46, 114, 117, 62, 13, 10, 100, 97, 116, 101, 58, 84, 117, 101, 44, 32, 50, 57, 32, 79, 99, 116, 32, 50, 48, 50, 52, 32, 49, 53, 58, 52, 51, 58, 49, 51, 32, 43, 48, 49, 48, 48, 13, 10, 115, 117, 98, 106, 101, 99, 116, 58, 104, 72, 113, 84, 121, 89, 104, 97, 72, 79, 77, 49, 47, 53, 50, 114, 52, 51, 114, 43, 65, 101, 84, 73, 111, 54, 71, 81, 73, 118, 88, 71, 89, 90, 67, 89, 48, 86, 119, 106, 122, 86, 111, 61, 13, 10, 116, 111, 58, 34, 97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 34, 32, 60, 97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 62, 13, 10, 102, 114, 111, 109, 58, 68, 114, 121, 32, 57, 49, 52, 32, 60, 100, 114, 121, 46, 57, 49, 52, 64, 121, 97, 110, 100, 101, 120, 46, 99, 111, 109, 62, 13, 10, 100, 107, 105, 109, 45, 115, 105, 103, 110, 97, 116, 117, 114, 101, 58, 118, 61, 49, 59, 32, 97, 61, 114, 115, 97, 45, 115, 104, 97, 50, 53, 54, 59, 32, 99, 61, 114, 101, 108, 97, 120, 101, 100, 47, 114, 101, 108, 97, 120, 101, 100, 59, 32, 100, 61, 121, 97, 110, 100, 101, 120, 46, 99, 111, 109, 59, 32, 115, 61, 109, 97, 105, 108, 59, 32, 116, 61, 49, 55, 51, 48, 50, 49, 50, 57, 57, 52, 59, 32, 98, 104, 61, 55, 83, 56, 114, 115, 50, 50, 107, 75, 112, 109, 105, 110, 72, 82, 48, 48, 78, 77, 106, 98, 122, 79, 67, 98, 89, 53, 99, 98, 101, 79, 73, 71, 52, 81, 116, 101, 82, 72, 81, 71, 56, 103, 61, 59, 32, 104, 61, 77, 101, 115, 115, 97, 103, 101, 45, 73, 100, 58, 68, 97, 116, 101, 58, 83, 117, 98, 106, 101, 99, 116, 58, 84, 111, 58, 70, 114, 111, 109, 59, 32, 98, 61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    header_length = 378
    pubkey_modulus_limbs = ["0xe4e468d4a8aa968afb167878faf919", "0x0bbea2b2fd31d16e743acd4163e2ab", "0xdb95df2ccff3d2feb3dc38371ab5e7", "0xbc5b5d58a0649fec4cf765bc326c78", "0xffd5e9a11c12cc5bfbaf1d44908587", "0x13cb618ee314f1e928dadc546d1319", "0x96a517c4b42e3ce1139ba8a8cc05ff", "0x99898558d15fd00ac797a480819f91", "0xc9a55689988924f3"]

    redc_params_limbs = ["0xd6ddc96b326c15660fa6417b2ec470", "0x67496318ec9b005135d5a1e567cb65", "0x7856eb0e22f5d1242d784643f289d9", "0x7c5d7510c66ceedaba2ebc2e5a7214", "0xa8253b59bf60d6aae39c6fadf0d5e1", "0xb668e5277538b65054edef2f2ee11b", "0xb0fef0e6279cb9e900b5bb211ddb05", "0x64fc9654cfecbfb8fb21a7e9ad1a41", "0x01450164eb5e3eb69d"]

    signature_limbs = ["0x317e116ec85f2d6125965e7ca36daa", "0x916f2fb35988602a7c27f61ac9f75a", "0xdf6b9049219fac1b658264fc635568", "0x9b28b01a125fdcc490622c6419edbb", "0x2206c68d3850ca45fa61b9a45d6ba0", "0xc6cab3910d4652bac06c3e21628cd3", "0x761275badd05e62c7031c90cadfb09", "0xd066c3f73c221fa7a3854834f17052", "0x9003ed7f639e24d8"]

    _domain, _header, _header_length, _key_size, _pubkey_modulus_limbs, _redc_params_limbs, _signature_limbs = \
        await extract_dkim_data(demo1024_eml)

    assert _pubkey_modulus_limbs == pubkey_modulus_limbs
    assert _redc_params_limbs == redc_params_limbs
    assert _signature_limbs == signature_limbs
    assert _header == header
    assert _header_length == header_length
    assert _domain == 'yandex.com'
    assert _key_size == 1024


async def test_dkmi_extraction_2048():
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
        await extract_dkim_data(demo2048_eml)

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


async def test_sequence_generation():
    # https://github.com/oxor-io/samm-circuits/blob/master/builds/samm_2048/Prover.toml

    header = [116, 111, 58, 97, 100, 64, 111, 120, 111, 114, 46, 105, 111, 13, 10, 102, 114, 111, 109, 58, 115, 119, 111, 111, 110, 115, 46, 48, 48, 114, 117, 98, 98, 105, 110, 103, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 13, 10, 115, 117, 98, 106, 101, 99, 116, 58, 104, 72, 113, 84, 121, 89, 104, 97, 72, 79, 77, 49, 47, 53, 50, 114, 52, 51, 114, 43, 65, 101, 84, 73, 111, 54, 71, 81, 73, 118, 88, 71, 89, 90, 67, 89, 48, 86, 119, 106, 122, 86, 111, 61, 13, 10, 100, 97, 116, 101, 58, 84, 117, 101, 44, 32, 50, 57, 32, 79, 99, 116, 32, 50, 48, 50, 52, 32, 49, 52, 58, 51, 56, 58, 53, 57, 32, 43, 48, 48, 48, 48, 32, 40, 85, 84, 67, 41, 13, 10, 109, 101, 115, 115, 97, 103, 101, 45, 105, 100, 58, 60, 65, 69, 53, 65, 50, 57, 70, 55, 45, 57, 49, 49, 65, 45, 52, 54, 66, 54, 45, 66, 50, 65, 66, 45, 57, 66, 68, 67, 66, 66, 68, 65, 70, 66, 54, 49, 64, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 62, 13, 10, 99, 111, 110, 116, 101, 110, 116, 45, 116, 121, 112, 101, 58, 109, 117, 108, 116, 105, 112, 97, 114, 116, 47, 97, 108, 116, 101, 114, 110, 97, 116, 105, 118, 101, 59, 32, 98, 111, 117, 110, 100, 97, 114, 121, 61, 65, 112, 112, 108, 101, 45, 87, 101, 98, 109, 97, 105, 108, 45, 52, 50, 45, 45, 99, 57, 56, 100, 53, 50, 97, 53, 45, 57, 56, 56, 98, 45, 52, 57, 57, 101, 45, 98, 102, 53, 102, 45, 54, 50, 98, 53, 98, 49, 48, 48, 98, 97, 55, 52, 13, 10, 109, 105, 109, 101, 45, 118, 101, 114, 115, 105, 111, 110, 58, 49, 46, 48, 13, 10, 100, 107, 105, 109, 45, 115, 105, 103, 110, 97, 116, 117, 114, 101, 58, 118, 61, 49, 59, 32, 97, 61, 114, 115, 97, 45, 115, 104, 97, 50, 53, 54, 59, 32, 99, 61, 114, 101, 108, 97, 120, 101, 100, 47, 114, 101, 108, 97, 120, 101, 100, 59, 32, 100, 61, 105, 99, 108, 111, 117, 100, 46, 99, 111, 109, 59, 32, 115, 61, 49, 97, 49, 104, 97, 105, 59, 32, 116, 61, 49, 55, 51, 48, 50, 49, 50, 55, 54, 55, 59, 32, 98, 104, 61, 104, 88, 118, 109, 73, 65, 83, 78, 101, 88, 56, 85, 73, 85, 103, 86, 84, 50, 99, 112, 98, 105, 53, 85, 51, 106, 120, 97, 97, 52, 102, 122, 89, 104, 70, 86, 114, 50, 56, 102, 77, 76, 77, 61, 59, 32, 104, 61, 84, 111, 58, 70, 114, 111, 109, 58, 83, 117, 98, 106, 101, 99, 116, 58, 68, 97, 116, 101, 58, 77, 101, 115, 115, 97, 103, 101, 45, 73, 100, 58, 67, 111, 110, 116, 101, 110, 116, 45, 84, 121, 112, 101, 58, 77, 73, 77, 69, 45, 86, 101, 114, 115, 105, 111, 110, 59, 32, 98, 61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    header_length = 531

    member_email = 'swoons.00rubbing@icloud.com'
    relayer_email = 'ad@oxor.io'

    from_seq, member_seq, to_seq, relayer_seq = generate_sequences(header, header_length, member_email, relayer_email)

    assert from_seq == Sequence(index=15, length=32)
    assert member_seq == Sequence(index=20, length=27)
    assert to_seq == Sequence(index=0, length=13)
    assert relayer_seq == Sequence(index=3, length=10)


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

    from_seq = Sequence(index=15, length=32)
    member_seq = Sequence(index=20, length=27)
    to_seq = Sequence(index=0, length=13)
    relayer_seq = Sequence(index=3, length=10)

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
    samm = await crud.fill_db_initial_txn(first_user_email='artem@oxor.io')

    uid: int = 123
    member_message: MemberMessage = await parse_member_message(uid, initial_eml)

    assert member_message.member.email == 'artem@oxor.io'
    assert member_message.txn is None
    assert member_message.initial_data is not None
    assert member_message.approval_data is not None

    assert member_message.initial_data.samm_id == samm.id
    assert member_message.initial_data.msg_hash == 'yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68='
    assert member_message.initial_data.txn_data.to == '0x07a565b7ed7d7a678680a4c162885bedbb695fe0'
    assert member_message.initial_data.txn_data.value == 5000111390000000000
    assert member_message.initial_data.txn_data.data == b'0xa9059cbb'\
           b'0000000000000000000000003f5047bdb647dc39c88625e17bdbffee905a9f44'\
           b'00000000000000000000000000000000000000000000011c9a62d04ed0c80000'
    assert member_message.initial_data.txn_data.operation == TxnOperation.call.value
    assert member_message.initial_data.txn_data.nonce == 34344
    assert member_message.initial_data.txn_data.deadline == 123123123123
    assert len(member_message.initial_data.members) == 4
    assert member_message.initial_data.members[0].email == 'artem@oxor.io'


async def test_parse_member_approval_message():
    await db.init_db()
    await crud.fill_db_approval_txn(first_user_email='artem@oxor.io')
    uid: int = 123

    member_message: MemberMessage = await parse_member_message(uid, approve_eml)

    assert member_message.member.email == 'artem@oxor.io'
    assert member_message.tx.msg_hash == 'yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68='
    assert member_message.initial_data is None
    assert member_message.approval_data is not None


async def test_execution_txn():
    proofs = [
        ProofStruct(
            proof=b'000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000000ac0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000c9b957f94c58eec64b688ccdfed79aac6a000000000000000000000000000000000020c98cd39cb55e2ad6a289e7e175bc000000000000000000000000000000bb5fb5d23596fd5abcc9ad00a4275c20d80000000000000000000000000000000000074620fcb1575a1adac6dc77da2d7b000000000000000000000000000000b4722beddb96011800a36cd791781cf09c000000000000000000000000000000000010ccac2de1c42190e76e1a4fb22fc700000000000000000000000000000007e5e51827c6b64852cc7b7a2b1d44247300000000000000000000000000000000001199e032c757e560db0611a505ceaa0000000000000000000000000000007dbf05935fd6bdc4f2bfa30e4749cac88e0000000000000000000000000000000000076a3fabd5e1deb971d55d3e023c51000000000000000000000000000000c1b42d23e34ba575e0c47f8f70c7b9802e0000000000000000000000000000000000208bbac8f671b28b4a3a695e3f849d0000000000000000000000000000005b9b3611c1636571422f1ce8e063f33a9e00000000000000000000000000000000001fceada00528fb209840097d2cdd18000000000000000000000000000000a44c6b393ecb26d8fed8d6109ebf6f540000000000000000000000000000000000001f44addc9f2bbf5b0fd7bf77846dd20000000000000000000000000000007307a59c59f613f21d34372a3261e8ca16000000000000000000000000000000000003779650c8431646434c5b23d50f69000000000000000000000000000000c1783b1f794400a68491de7d2c3bfe29750000000000000000000000000000000000141aed242bfbf36c8b0ae768a083a2000000000000000000000000000000ee417b44dbbd83ba7b188484dce1e72df5000000000000000000000000000000000003c5e9f35c1a3bb7ca0af2ab78791f000000000000000000000000000000b5a5c1156a15812f40e5e81a098b0812d5000000000000000000000000000000000015c2cf1ebb3aaa0721ebcfb37c053d000000000000000000000000000000d45904d4066812f925ef510fd46f3fc32c00000000000000000000000000000000001277900b95eb2363ae46fb86311276000000000000000000000000000000a3e4c57168b12f431519899a4eee15cf8d00000000000000000000000000000000001c604967c84d9874a0a385ab7a8a0b0000000000000000000000000000007ecc723c819d9f7f4978ff5d102d48959c000000000000000000000000000000000024ce49a962e7bb429817dcecf42dad00000000000000000000000000000000d41c251ec1da7c109d65cd1ee600fd6f00000000000000000000000000000000000121b90b29049161b553e9c9f5634403b311ef89217d7270142a96bcfbc65b8888165801dfdfa5a4d70bd449b07f902cb13c83581022b7483c1b1fc48592019fabd1f077d990eb9f0ae9bfa64f8071242fddd2ff921c16dea92cf9660e3c7d7d395b56d2eff66237bceabf601983eb302447f36320257ba3f9a2df194f6fdfc10aea2a99bc48bb8f07efbeba9364e614663db70529c1e84f0ade9ef94484c3444df15a5d67887283c5e6d90e8328e22a9ec38f8a8a09a028dc681d6dc70268152ed0b152f1851de49687174588fdca072d459947151b8f10b39092a5da7f009de93ae26c0d1e4345ed1fbc45552baa265ff5d455dd56ab199797ae8e4ee2be851ea046b9937e1e2dbe4ce27a7afa6526c6a26e44a5a12d7faad98b23963cf29503405feb38ddf87d7acd5348b68efe18f11c437961f14a312e3569b9f3f177a5e1e080b763f75bf850966b8277f94e2c4c9a11649b9d52784e8861cc9fd214eb5dc975b4778b5873c24d68dae661c4093da18f45725e96c15815dcaa5e724b19e339be718930a9d69381375462a5d90177bc49581bc41b6da4cb3b0a1ce61997a2041b3459feca46e5109ab1636e15258ae5d2fce1e6a2e5c6dd4ae05a3ad6c9392552d40fdd7e708aea5a5ad24ccc2b439de045093f30d68c13ba21eebf55e6f26f68213f812717e6c04eff37d4912c56e091dc400fdba94f95b81de13ee29177fe8ca84a4c13ef8168dc45e26c821a4d62c4de96cce44a7507007e7aa23c88c3339da3facbaf91217e2a8712e0d905f1f4b7deb452658b82cfee6be5e2f7e1e89b3673baa119983df0fe0d3cbf362cbc56444272f30673408dac7eae5c8aaceb1ec8e3422de602735f724bd712631c8c7d069f658df47b6cbac848e918c0f50cf76a22b061633afa75a4f86a73f812fe3cb9f2bfe4a658c3522bff949019b9280a1f48f0f7ee48fab48180fb6c5304b46161da4c3f3a88e75529e20683f33f13a55f471fa225ffaa5a241ba2366917c924d07d6b673b9b4a27a572d6b78d6aba224dce8d52ad37f29635caefd511031c6319ba9d02770683a5a3458abd10677f6488db8adae7173b6fd162aa473512cd774ef0a6119651f6f718ec9d2a0eac031320acfa1e78f62872a4d7ef88c8138925007172534e60db7bd251bd404071535261aad912ca0d01e304e11b71002800257e4fc7437a57f96a3c12853fb0425640065fc1f54be489a3548d0287b51cfe0a5a694bb30b244c3c93de79b75ba9ad2814b922f737f83c4c3aa34b89b117efaa6cd7eb10e815ee6e0adb4c59a38353f07d0473c1641f4ea1802de6475b1f9460d622bfcc21c69793ee87b660a9447e1bb4e254b04655dbefeaa1fb9e1c2f65c32c59ef2e7d300b16aa2147bf953846c7e2c9c076e3ec379dfccf4ad29c248cdec496de37f25b5486d2fc7818e4b04f48eda3105c3c9e94a4cbbdf5d55f1344498ccd611d65b9c10099f9b136bf23538d2dadd83451954649e858016e491ddf4a512c84be417a171811d9463c87ef9a49c35ab39f38bd7f9125bb936f5608ef49652b347780c857745fb9018408e9352ab3bb7de556e3f234aef8d35f790ea5f413eb941d4a26bca651f6322c0f185058fae04d55e0db4db195c23634ee290fe86851e2c13fa026d662a12f788833aaa3cf5381630ce6ff68ab61ce207000f417d3636312057252f7e8a1f176354eb739946e9987bb5e5903ff03fe1c8127ca2c65aa4ccc47817ac00b542608fedd048a9bf8abb902c2efcf3976eca42c2cc5779c94d121c656a901bdd1a5f5d6f1b116d108ac078c527f6804a2178c6f2b397949c8e37bcf3e00bbb68bad62061c5ce1f19ede2702ac938f8f9394579a2b72d85811325d7cfd11fdc7726f1a3cf312ef7089175b0e49966be2cde46fe000ef2039e8c8f14d9850cc018e22e1f4832da4ffd26896f620f75100e79e102a0970d632c7e817c258f96ea8559e07bf68729626025ed1b077e28507e0cd6398069ed7109fe9d6922e6cddf040838fd0bfb4dc4d58fa73bbe609801b430d99d1227ad26f938af661eaf6799015b8e7751c0a1f1f91497683cb0ade2944af63ae2f7f5af7fd1703491703507437cc743ab325bc10f65f38b30fdafab4953d03d40dd86210a06627d83aed0baf94635720c6d9d4c6ddef53f7636ec0f9c7f9e7180171f27e3f50af27d5fce36e9f9c5f77a17cda244cc20c41dd091c21dd16c2a31fac7fa8d73ced2666a19b0780b3288b3ea16dd6e46d8e532e132615d5022adc25e23ccd4bc7dff4bce8090fc9b3ff248ee5741ac681b29ed1c4350531172aad0b4d0482b84f0fae6090fc03a02bd703437c4ab1a0344cb8df29c4bdb58d281b01c3315f8b093985fc890f14255b3c54dbcb313a4f542c3352253147cbd225ea1827f3aef6611afbe1d7299f9f24a852d60f6fafd07eca8802e2824f64cf1398244e91b20f581f9529703c14a4c5b72c803db630fec260366136b84f0782535b194c37b8d2c8a0ed10cf5539802b6a88700cb9181ef2decc0aceee0e5ba0eacd0948ff46b356645cc0870a04412e8685f2b36383848b3305ffccfb408ba5b7f314dcd94c8bbcb0b0b278aa8a9e03a03a8a538f9e0e8d6f8dbe8d12b4f4f1dc782850ff89bb33e15fec0c8a81793999ddf9072d9cf35cc52a75f6af96d69600661079405f35e5e19937e33986557932055b548cc6af508721b08444e5bcad029822cf22f2e0a0b0fafa1bc461797b0014b0f8797ca7f931db881a13d034e631ce0e00bf8eb165c6f25e32c3e00a27b554e478cf070c73f3737fad0eb194bd1fa729abc7c9573307cd7f139fe4cb0e5fd36240d2f356a374f2c916eb0caab9a1291af55cada2a45f02f68cb063bb9eb90c8ff8bc8a49d8be82f381fa2c90dca6ff079f3a1c5a0d0fbe021fb9f9f93933c1df3961de3ecf2893f57e8a529954e06d15d0a55d0855f5715d3a2a5e63d17c0623bcc72ccff149e5a6020bf6837088350df9626d33e0fe29516a383e99e6035228cb4a0147471c5484d96ca62996584f2da85c0cf43499e45aba9feab4fcc9cde84979c757854c9db6f870e5b8c7e56c0070f5840a9e0ce447ff7502d907a1f35b8a68c6cbc3c0611327ea942862750d06060e7dc5839aced53e0326d1270ab6d1dad6266dcf6d485ec2187f5088f1450fee1c25db88f8552d8b3e9687da47edbc3e7034ef324e4b2232c41af06f24b2161764cddb8ca7740d69fd77c18cbf70c33f55d4c7d550fd631b64a9b65284670621a8fa819582072f27347b362cbfe3c20207844cb0200da1ddcc857591dada1a0c2e2a516f8d1501419616be826bc9ac2b57733012c45f5fdd00df77ce893b27cf3d84386278935a0af4ebc29d5c10f13893d6011fe39b9f96ad585f5456331f0985aa1cfd3b340d2e9975b6b2520b15c0cde8510a0c6dd9955ac0559f20b5054df3ebef479fd68b74b25004c49c4b49f7992d3cf68042f88b4a6f84c6b1912419d074ed347cc4afb95e1cfc7661b4863a2e92721682e36396f19bf68a2c28240c5b34608d9ed823fbba6552c84b8a4f113d14f60ee4df3b1684f465ddd317110bd463416bdd136ea2463741267492f70b61d676e33723073e3661d62ddc6430470d5ae292f56cb7b2471251c0845fa2574627305beb49df11c4160c1f4eec17199a0b949ffde3d441a0bbc221d3f41ee3d29f383e61036621c7b90a0e434e27ef5b46b85d99a3b5346b32a68e5e73c804285fcbb3e12a7036fa4c5aef220e2b072b924717a3ad8de4b009c71d3fc8e7748ffbd822d22a48a08a9288f3156a184691938fc57b050793b21adbb1adbd87e4ea55e83e121dcc23051be3a4859021ae4f64b70633bb49cf71b6692b803d0b5f56050109509dea131a2344f56c8b16d127776766bc300168cc7e1d6c71fe2e8c589f8cfc28d0bd426c3a2edd0d3629ded6365f7e85a7309e3f2deaec72650a3827df6c49cb28d426980bd6ff74d91836251c33859459c838425abbd68cb9b11d3f370d3dda0b1440d0fe9eec224d0d462eab1ec2304ac5e8bef12587effc24fc49dab88bf7b0e192253349c1960300381a7e56df229728d229c1825e8f5b29dfd474599b75b83f53b3a290947b660864d83258abccad089c13db242f76254a6197e8d45059df18bedff2634cc64924d098d572f5779083ccd4a92477e2a2988e4b21040ba75f81823358191d179a0b3bff183b15a687a603fdb72c3e0fdf610a9c494528dd5602a819b138a9eb9924a45104416c6872464060ad369a05c933e9271e0a15298bad2d9828f58845a21cdabc6a0dd20bd6c122d086452d1f3336b1c6191f211fa8d178363989eb8dfb1eddfffc05a60d098493c8e156c581feeff6e90701165d36859b189edd36a48511f143fc4c3fe19e8793107c3f1bd1d615ce2ad3e37c8f010229da439cbcd4d801b01b0451825f7785fcf0f1ee2bcdf2ee9075f8d2eada866acdfe7abb9294ad1c145fd5b495b50e8e8f55a2330fe209583813ed76d831cf77f3b1a04144785210d1038162a9d25a1d1394444e7d834d9716f16c21ba45fd407c03de343c52f7269eaf8a101e306f1944c6ca1b1e85615ce14799ee179be987231760956f7613236063decd76cdbca0c5609d6006a2cd8d8522aa37b2a157079ab8cc362943852328fc72f83652dedcc849fd98da5930c53fc2834dc2b8f77b193b49af29d16e18dd52dde4ee71fb3e88ff5dfe642953bd1765e18e0f61105ea1ea05bf32ba7c1f6214eaafb84806de8e7a3cbcaeb902eef1ef767162322d653e6c32e73019ec1e10cad7c7190b64fe84acc185b0654c2671906757f97f7a9dac45f4682461d41d4b51733dea2cbb186add3bd39d0d6d3115db1fb94aa79848836dcc90d7fa9f0a9b1f67c66ae60f57a1228fe91f1ac040aa4e0f246e13678e4e39b25d2794b629163a7bb77ed0b709079bee1a2fdbc3ae24f67bcf8a6abd29861d02e21becff1d74eb4a4aaba225759bfd3725b5fecc4d268cd82cf5a5e104e867b8b45e5ccb0dbc70c75389cd6d2a49715006b89d263fdab4e9cbe0900824b1a67ae1cb25b60084ba4296ed01db04f77f3e565fc13b37933b813c0ade97524e441a557ca3d41761b22d801228b9072f033921707e44b3654b7e6e0c0067270b0126ab86f5dc0e0d66932925f3af46c01a98e06b593a1c9c9d19f8731e84b20a3a5416d226d3010c9dc7775769618d03db66bcf6f9eea43ffd824ea1bd6bc16de1cf2d0078080370902cca05fe09a88f6acfa98b7fadfa052ae3162edd202f71568c2bf778ce0463365dfbf30f672b5d121fc2494fba75318cca269a80ec11741cc75659204011b95db64630c7243759ceee4bb73c892ee19f1cef04da4a924f645d9b6bcf341635cbae4e1d6a4f83692f2d428a7377d99393caae55e1bf8585cfcfc4ecc801122dcfd2d9e22688136469021483815ea11e2d001bcb78a32dd680d843537033057fdf51a5f1f18dced8a4a2a2b71edd368a419dade3094fe6b238a2aac50fe02e794901e81941f76ad941304eeb0f6b5d3e815e2fbdc999156ee69b16f693d021a66215ee45a1a956c339af70d3738511dec6693c29c2f2846f43f174e941d5251cd60ce9c0a73ad67124c1e7fbfeb6bf0d8a923151a428103d41b2e60a24f317b4fd9d062ae83c8b4355a932a01b9dc7b64e123e659d2d8e4cd19b649c0bc21dfaafc8cdacb73f80b4fc16c7ed42af395a7cd98e94118b8e2ddd2f452add010ade66c3c6775af764855ec1530004a1ec634a6331242382f4a24270318a9422034892ca2b5fe66ef4206128bf1503ff031f200e60676c36cbd2a822ecef03380eea8d63b0a2cf2213e6a1898c67cf5ff978e073c77b41176ae75e7535888b310f825fc9b325460f1fc36cb0eef36d7f9726ef06fba28f3336fd4016c6e19189201d1f19ea33787cb94fb2aa222010c73760d92d7630cebd20a71d27316b48bf238a457d111b6bf7e7ef66cee12b7f343b818f2e42da0ad9612168fb339ca12626988a0fa71781d64aee0364b96866d32f8463806a6b414c759bc3857a455c7c065fd651033f67f7243cc71f3eaac9003bf069a08c47283ee64c0e1b40a35a610981bfb5d4d601520598b898b0c8bf2f95080755067a7b3a3b7d23529bec13d120fe9e9ab60a56dc7fbc8e9ac056e92a88ef2ac767dc9edfd4ca493a9360d3c32e9072a67ee9843f95ab929184dac4b3297afd5ace6b1b3b7a86e3a85754b8542213655d2bd45c3e7fca4fdfba2c4f95de5334807d26ab801181de4816ec934e11e5b4d6bcf441d2ad8dd1b43c10c276cf413d9795aa5702df80a5fc12eed2b80517c2a9754905b196847626eef4168aa08d0baf57be4bcf8cbaee15fb72f27829763c7de6250a18290eb9a30ab63e753576091460991670b20b31d9cb38325e0819a44fc715a6b4d7c4c85724447e00345b1f6e89df5ef64a8f42ae443ea04820b7bcbfa7d9b1179794da1fabb885ad6001df3cd65548fb30763fce0ed5261c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000183ab34fe72108d2a6ee9e85fcb3564f39690b716cc55480c7c0909e1974a92d111498f47cc6c00858191c75326527dddeb14d09f9566c3e7207cebf51944f491448cfdd1841420f9461d005ab426248153c144f9a8647073944a1b408b878690f1e8ba7a6df8959ec1cab606b2840e52ee24340302c3c7e011705cdf965b05827c133ec816b324745a262e9abd2a14b6734170182d8912cd959093725c22ce603b3d04202712d641eb04f6eefa0255d2aa3bc03a15918fa17670ce046363b2b14d4f3f46e143934ea955a92f0b1ac3eeed020d7974a734a54ee50635ec0651625057654ab9941145b00a81c2ecfc3aae97342005f895f23f6d00f8398cc10a31e69b6a13df93cb5cb8f51593f0f0d54178c8335bb3ef79adadec1de12fd6a7e232ef6d6a0ed066b74bc8a9cc451e7f78c2a66abbe2650973c54c2f0927ad58220b74e533ec600ac7029dfb06f83fa1b51e27431d44d356cb24a8fefeb66cec30e4b9ba0dcc419a06e78401ca786e32ab3356438f6c3740cb650a480b80f45992925771fe1353c822a41e568c60aea5f04c627e1606a7e2a0a3fb3e33a72a670210407fab96edc5328ee803bc51f364b0efd901e8caeb37efc55fdeed1e53e112397f6eba49bba40613cc601fb6002feffb535660fe1578d50def81d51252ddf09be072516a9e60e087ab85dc48a02a1997b312a3d7ffc2831eef79e3baa98b6069957b4e3012bb26ce1664a16922f84e64af1b1a5357da7b7f0f5fccea901f7135737415a3111d53d67fab50a33fc3f36af31911c29369e7d153be011c04a9527c752deaa0fd4aeb0485e847cf0fd6f6b8b8e037876177cc0cc2a705f9951c42e9174dd29eae5a6d0ba968b4a5f24417cde19e64f7ffdc5d6cf9dfd7eb4bfe513ba9a4b015924c6ccd9831bf8d291f352c26d9ad900069bd8dad15e120d06a20a22f9ca9606e60647e0db96274b192524eae401f1c0a7040066132d6d949538057d65eb1be9b19886cf172bf0ee21904e7e47816d925acf9a1a39952e979c410f829a4b5583a48b334fa75ef3c7e8212c5ee085ef071d8c6e0d931d2c326a6d1d5e0fe77b6c7216da0631d37ab1aaeb11c55df506468e5dd29acc8476fbd29f1643996f6d0a3c0cdf36f8658d660467966852e8d7cbc64105e4f01806db6c140a9ea1f216d222be39a73ea3f8e66ad9df67442c5e49be9daf832e511fbecedc04c7d4bed2334cbce80f6cf473c0b589b2cfdebb621d525c16c64cf0be99ccba17bed6f3f1484a498f53a65d7501cf22b3b858e48e06cbd63c2026d3e27dd58d2654de8d3a6ced69ea1c8932e5bd39053e16a032f0e0578de55a678723022cd10c79c497102698211afc60aa5ac18fc30bfcbcd4ae03783caee4670db837881a11e55a566ee1d72f8d5980f1e0db07358afb36207b78b5c3bf1b5abfb0108f7f043c17f46a7ddb9a758713bfd616e4df73dedd9e7b9d5d42cad5311695728b7124a27c4861fa8c532e5ff20d7193e2b08ebb3aea5c586a024465a73f2f2e55ae21e006ca0ab56430b664514a4dcf8c00448ea141298b5717337c561df7b5e1430ee2df10ae989eb86ba75e8a65e60d3c8aa0db5b0611f9efe27a3bcd8ddd9f8d20cc71693018e2558bb27568fc5a4a8b3e53a27036052695ae52b4f3002f9e6d022aa08eb1b40acecd5a104aa564ebe87116fda1edda52dd8ca47c6a7b8f097d24e90357f57281f23353f0827b90b66b5fed939ed8f70df8a3bf087dbc21f6a011705bb2148d14b8ae7ce0653f753ddd1c21727523ccbe7da6293ccd025387bd0d4b192b23ca726fdfe8a8c74d16585859c993c25b4731ebcf9c3b503eccf8180a7b4b62f14906c44ca7e8a99eeb7785a95720a60bd1adb6b359bec1bd170dcf2020c602d420c91ddd3e8114d0c3179e1f570744d9ecd8d613e883740899c0c311594a7e2cd8c5d13c33721052b15660a50a4ea375f93f97641cc58959797b13',
            commit=int('0x01e756223c5baeccc9076912dcb9c1dc0d6f1c24187f678682017e93920784e8', 16),
            domain='domain.com',
            pubkeyHash=int('0x17655f0139cacecc80f4143fd28e7107ce6038374ea9d5cfcf5d3fb5ce0086e6', 16).to_bytes(length=32),
            is2048sig=True,
        ),
    ]
    txn = Txn(
        id=123,
        msg_hash='0x123aaa',
        to='0x96B4215538d1B838a6A452d6F50c02e7fA258f43',
        value=123123123123,
        data=b'0123123123',
        operation=TxnOperation.call,
        nonce=0,
        deadline=11123123123123123,
        samm_id=123,
        samm=Samm(
            id=123,
            nonce=0,
            samm_address='96B4215538d1B838a6A452d6F50c02e7fA258f43',
            safe_address='123',
            threshold=1,
            expiration_period=1,
            root='1',
            chain_id=1,
        ),
        status=TxnStatus.pending,
        created_at=datetime.now(),
    )
    txn_status = await execute_txn(
        txn=txn,
        proof_structs=proofs,
    )
    # TODO: refactor to check success
    assert txn_status == TxnStatus.failed


async def test_blockchain_execution_txn():
    proofs = [
        ProofStruct(
            proof=b'000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000000ac0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000947ff1c73d520c831933beaa21beda09b200000000000000000000000000000000002d9b92b09038e978bef378e9330cee000000000000000000000000000000dec8bca73212d94d3cb3d7c87029806b2e000000000000000000000000000000000006e1b42f333e8bbe823e02936ee81e000000000000000000000000000000a21ee96288fcf843b8c54162e9fcf6e85d0000000000000000000000000000000000115cac21fde280a5cbf99cd1786d5e000000000000000000000000000000fc6245d8a2eced6ddbf00d4384c318ef7a00000000000000000000000000000000001cbdf140fe044bdd520dbb382af53b0000000000000000000000000000006086b145f4e64f4c579003eb06fcbbb31e000000000000000000000000000000000011171918a9ee63f5cf4aefe8e93711000000000000000000000000000000e0bbdb32952e632e57cfc230e2164725cd000000000000000000000000000000000000dc1222305a5f61119176d6fab07b000000000000000000000000000000990e880e62cf29d5ddb481ee695810b9780000000000000000000000000000000000081237a4c4b20ae0405b5466cd0bbf000000000000000000000000000000826a76c7c02b571b579d5aaf1c082c417c000000000000000000000000000000000021d0d3d93d12ab1faeebb9f89e3f42000000000000000000000000000000d9752b81ce0c4ec397d6efd3310c3e229700000000000000000000000000000000002056b96d91f3d248816c320e2457eb000000000000000000000000000000346b10cb48abf4996e240aa0b557c5de5e000000000000000000000000000000000013a165d378237ac8cc43405cdef6170000000000000000000000000000007184b23780e530bc29a2d637f616a7409000000000000000000000000000000000002693b71c8384fe39647b640c06448e000000000000000000000000000000fc87c446202ed7c6b5c82dff2871fafe160000000000000000000000000000000000178d4e1b0880c55674f07b3f74905e0000000000000000000000000000005b11ceef66a3313ce619f402fdee79e45200000000000000000000000000000000002002d73b54e0dc9a4284ffbda5061c000000000000000000000000000000444ccfa1a6d8ed165bf0ab751124ba88e600000000000000000000000000000000002d445a5676da957cc33ca561a0fbcf0000000000000000000000000000005b0ba1456a47aecb5d7f12de31a64120f60000000000000000000000000000000000286343afba29ce3197c2f66562429c0000000000000000000000000000005c116efe546961d728bdc8073984cac1e500000000000000000000000000000000000ece2076c4fdea06d4adbb5f064eec020b80f79ad1964f0abe6ff32a93a0cd46893ccbb0fc4e7623942b5987cab5812e58cd7b466009daad91d5c356edb78fe1aaab7cc8bd221b204dca3a68354a8028161d2ad8e7bf563d1362cb7feaf778c9790c14836814003674fd73196a74ba2b43ed509fe670fbe0e1e48e2a92dc371dd0a6453d54d1f2454ea013272e95250c5936cf84ed10f2ae8b31df97b7dab1fec7f858d7fb5eb47bf87052ae2211cc303f32000ca0535f5ba82e7ee6013217149fe7cdd452548aee93bf777c8efb29297a0ce8f6fb05cc6523c54f07b7821cb0f1bdaf2a2bdb9e297130fff36b1fdb1512d9f1410e18501c24336f34f8784ac6946e4bb3203389eb126fadf78e8ed32c88ccacd47ff90da7d4aee78ab456895585cd1629fac48b274d2262c856be7e0e199ca88a066635dc8e5465f494a427bd230b57a34027a043500b9f403f0b3010a2ba15e7be4bc13fcdd211a3847444f994da514541b37f386dd9949db4c13206542a5c4d4cb8160a906869f2e9fd5a18d91a106069881bbb23d7aa69f8104e2362328db723803ada07b5dcedaf0243505769a76a695a4db9a0aa2173651dbc077b11468fc21e6e42efaec224243dc7870e527ac542c214f56eab537ecbe52b11661170d3007df325b20db0114ee42e2b4ef71f715175661aa3f5a5ed6a279e2a7ac5916cd0d4a1661c096320486a7e275735f142e6aa38f0b35e6d0b16dd73220ad0d6b43a1c3b6f6b17204992d82bda14ef9c7811e80c11565f351079cdc5228dabee8a688e561f6162b54df2e287a9f119be2b3dcd766752289f29c77d2928b7eeed235178b41cccd6a5f872974de963c0107dcf447e663c22b62f79edb101c1443a6bf6719d053774bcdfaf3a8cb25bd951b9b282cd1b83e5bbca3d80fb1c7b12a1f4074d5f8138bf4f83c03a83cb20e9c931b46cbdaa314cb95483a7b00eba1ecc255840fa9ae3c9754d99fc4203b942a1540b1215109cb07ee249414114872c59e714f2310ada2caaf0ae84fdaa090e9253e24e5819b12382228bb7e92fd0315cb343a77ab702b787bf002fa9f6d2cac4c50e18b9f7dcb9b41d3f8be90ff324dc23d35869039c3bf58cf93860f48d39d36dfa0953ab08fdb5aa87a746185ab8edc19216a9b09809440e28e51b97ba7a6369a213abe56366b43a7f35ab0a74d0126c449816cc02f0a39b1cbfa8750922bb47665e6baaee1fcb7bc9e40905865126ce484cbbf80f899efe8a463a54d1f5cc79d2168b5afe182777b2ebba2c5b35de8138d10aa6571094f9d11d37d923d8bd0087eedd207e8682d702b3c2145e92ce22a65153550a7c972daf80fc6a987029230a27d96a7ff52f00dbcd80046f2e0defa02b50479981f5ee38fb7a0de70e3988c002c76bf1dd3e773c276128e9f5097c763e337e3b5fbb9b0b2ac91b8a602df4427d4df61135dbdc79181d013b0b64969131cdeef1c1f5685ea4fbdd018f69340d0ec4dfa89450326684031fa5211d177e78b620b633782f05ae6748482e60539daf4483cb25a128aef033231855a91b123ef42f5d92bf910a5fd8548cbaf7d213b767e85a418a9c9ab0c220e3dcee4c3babd26997b07ca1922c523d9a8e1b405e2a0c0d47d6e0391cb3d715a38d83050ae9682427dda868ca55418a3817bac709e5a1bd8842ef843df062249ccca827aaab21c41f681031b56e36068d6fe78eeade16cc42dffcb79d6220030fc21ce37abe9cb407096bc976f84ea33a46a3d1023ec149a64d60447ce18721a2a0af0c1958c1c809c290cc6c66b86eff3f9d1976f0f1ad082dc5abab0e45259d52b237ed4134302bff110e874026bdbe0a19b32c2c7186841d1853037c17167f472db6a15f45c59ebf5a799ddc9f869285e2bd1324d50faebada0048e97e270c8b99c09c65bf2e7bafdc70d8438953424abe23b49cb1871d799d32643ee31b06d4c14e8670cbc127855478834861af7a764f86e520c0d47fecfb3059a00d27faa83892b18d3c6675915416954e0afcff3364dda1f9838bdce2888f84f0351f3bea0d049d9ab56d5f2e3138f8e6711472c41fb537c498c813d876c4e4bd260a9ed62a5e6e30a2e99352a7dcf4055ba959cdfaaddcf5a8ddb2a8ba2b8f1b67175150cbf41b640a8a344466bf7f0a641a52e8f4094ab0607582d7b55273c07806059ceb0550692ebb527b670dea6c82d700a2c7af77cebd5002a6073d5852342d72c4b17782a0461b47370b06f617e9098eacd0b6c3e85dd0790c1efff3a971204bbf4e22b548aeae93e399c1642501cf661749c67a018047caa1e6fb8c95dd209d20f67e0de6bb59a35f2146aa9c605aba9f0650bd584c1640cabad634e39b190df6a66b180f4a395ec7ecfe369ebd89840b9e3979ff73503b7d4b53380605053a65a9e4847f1320fdf37980d4f255c86129396156c89aaae30abca4967bea2bcb19eb4fbda7cd2fd4f919e5cda9c5e66ab2cb328ca1d7fb2dc18b170c81c82d1d4188f3fa88e840ea50d8e953f255dbaff8bcbe90aac144f7c070f7d209322fa08f28986583b0155fb52616ee2b940926661afaed4a1db511bebc71cb70212b9b3644af84274e861778cf1c7582f735d1383958de2a814330f9e6cfc4c4880c9d78f13dee6d5776ba00eac8b117633b66c404f317422630f0483ba29a6629164c90b8f2336d1441e5ce18cfaee76ee2d7d3318d124a7a85c47b3eb7c897ec04e9c28e092ee7a28fe8f56393078d137a37d9749442629712b47a09114b85a4183f36ccd3322bc4ea162ee1a77c188c0147ec9fddf09b79595b5c68c3771a621690f701ad587706cddd729870a87ff66c35b5542e60a7ac05f4340772c8a74419efd67ca58efd8b903f54c7aa1786cd3c67f6dacd7065b64f314b5104c409931d32461ecacd084e6fa702c9c7da465ba646d6fe6f8dba9d0f372c32c6b61b0816270cf80282783533dbe49e4b099d2cd2cc23c455d8c12f945f99a352781b4a1c2c8d8ea5cf5b4b278047e225b265fc4c4dd87a9d44397f21384be5a9598818224d00cdf7903ff59dc38b7ea659a99e2e86b6e5642aa881ef6b85e64011360f133da49803f60b703e06afde55ca49dc364197af45fb4673101993f281f62b7129658fff80f6a80767c04baea2bf8e14d08ed328f8dc02800f692d2aae13928a13fb8667a6299d426746666957cf2a6ae0deaaad77eb023863d50a51ad1baf1a2f1ef64cc0b584c647dc80492e2088b36b3a5b6da6e333d69f43f54d3eada42a1e7284d8a77137ff3de066f14f3fbab41b946b8f59d605842c552d5463ae97292a1478135b35c3e75146d3b48488b2f5b44e158fd01835b9fa9aed47417d33132f1d3bfbc1f063dc35419c82c56e948ef83caf77794051456fc84ad8556b854b2f6548ba3623f2b62963eb2931ad3cf54ccc7ed4c4d545c866de4e095a8a795e145a637538e01b7d437ae4c7795bd7b350776353ea847a818f2422f889076b87026aa53f16da47b4464368ca0787ded36d7b96341ad10c40b72055d9eda941140d03c59008fd359be259426848246f825b32558433e05c02f49cf439bc13d5ba2c65a12da462b2ee33d2740212dcc9668c7c25aaa81148fbe2ac7f0625901e601104aafb50570a6ccbab55a29eb63e867181d409717267ef3a90d364b8fb077e1cd46bf9410095be986ad1b842cbc074490160ea4884f99a977901b67bf3a2a527471dcf57ff0f6028be370075ae59bf8927561d0bf112167cd386f109f132ca24efb6b3a5d0e16313d82319e8399988e83853a202bbe3e575438dc1e40e1666210e2714fd0fd3eef175c70db7f5da50116b5749424f97df7327c006caff582b1752a8135422682c1a0c71d036da3f8eeb9a85eb69a4a2974ceb7b104d8ad3960ace8f0b311ada6698ef658fbe752313467f1f156671618e1c772223925e87661fafe3c43bc1a89e0bbdfe990721813509f40596b972858cd721b1789d380d482262e0defd07934915ae846db1bc0e7b35e30fcc17581331817be0f072e04d9213f94b93ec7514ac898cd1c923d7f0e359606c9f6054c557e8b6d36c48d53558140a612c7588626698724cd91f2ba56fa3a77fcccd79a10a55e412b870d82a411847253a7a00df6c83d0a8b0069b8a045cc0ea6389158def498992139e6cb20305269dbb8e6303d9ae0d2bdba53ef8e1bfdba3e4c89f3fec7ef74744d755810d09368e6552e158c3dfe663855bc83a764dde360b804242ffea24c10f1e15a5462d2b7db6c6e80d2ea5ba4974ff76748b22a8869370d7b9a0d0f495312774bc4f161d0daac3a694e76fb391e320da0f0d502c955f76975129611681473896ee0809bb9fb79efcdc6a4c9093a6c8ff2eb4aa44f74e3d48ec1f53348029e0c4d3f31043f729b26599545105efc5739b49e3b6e59be9a70df2820c346fd0a2263f721717c9f4e1ba41dc50096456750f7d5b1b3873a1618ec4e86043c45a5e7a6daa256f18da289959609e5efe455d8d4a648704ca77d2a4b12ffbf5e51049dbb36913022c307023c27f4c17e1e1ee81cc535b361b88b0bd027d82866bc385050f070bfa6c42ad172b4fd37015d6b6d6550c583655f0ce08290d77933484c6027f560aeeef081c804d6f97da41a8655e368557b6ccaf2859dda190dd583299abdc981ea9f988914130daf3cb0898f533cf7450dfce4f222cd6ac60d8ee8d963460cc25185235367e3073d24551568225c9b3e23a0c606adce62de279f30b76e9f2d226f78c9ebd0ae7c87727857aef7b6512c3fdf212db1de082fb145dfbca39256c02910cd9cc02b3f104323ca23a989faf9e194382ed4a7453574daff059d42dc60b6fdb31f7fcccdb22e4777c0a93b846da683baaa4c08f6c79b5cf2555af005d0b4418aef291b47cea0aaf2388fd637cb6b7fb9d6a84b38062bb2c5455dab0ee12a83edac620188243b55374ab16c335e3724ee04e3fdfba584490ede43a438100de32d618a5ef07c2383e44760c37dda68a0346d0690da761b75a6e3dd82bc01fbbe568bc47d43908d37c0919ba817a28d81edf023b63760a13c0a924acb344217173ff8b8ed7ebc2f8905e3a827d6ef931deb9430fd0a28429712781e9de7d1a5099113796a77a111402d76aa2bbdd829c6acf02476f6ddc15de30e6d58f4f01edcfbc6472c6438fc9611f42ed8eef8b6403b526925a138d30dee66c362f2812174a9503cd6e341939e7172ae8528d85ac84e4e5b8522d37272579d428db770eeb0fb62f66e458d705ed262d08aeea4c87a9c9354bd4eec2738aeb0fcaca2b25ba6993d3f68314995bda89a20e45069d531d86d8cc4dcb4ada5ca5673218510464f0f25f7463ac8dda223442189865df94096f521f502aee9d1c92e108fda41e528c99308d95b0681698da02f5a10076bead4c8a84b9b5dca13d4d18c7b1b905895241c7d220b32565bfd1cc0009f551d111e5a07a453e4685a9436ee3ca8d1fe957c808f43f94b093ceb9cb0a34ece05f39674818d388b9120064dfada0eb2ffcaf481510849a9734b3239f1e5cf1ebdf231a2955e3a29b82611e4f9c89ab1af9ef915b8fd817aa35a038029bb5df74352a7f04462a4c2bfebcc7080d1f2215f4ae8576187a8db8ae708c1c3a75c3e5114e725e18051ef3b89f81ce0ef51a2df5fc24dd108989903dfea8c72ec7e25578e9484c0682c06c1d825ff211e534084eb168f6047e93de8419d352658b6d6cdf78a451d47d9ec5659e88ecd791e52490289023ac5c01814f74160dfc5139a5d86d44a536ed7cbcf591024d67f83a2a00129cd273e1939830901402998c7c5a7c20110695614945cbd824e250afbd1f0f3abebd4079f7d244dd0d4bdf6434cb9ff85f6ba5ca61370f3807492095970f32f7efa03a6a72b8b548fc69207cca80710b7bf1850ab7f3eaf0ad86d79097119bb86972c4efb44fbb4ea680af4c2269aa6a4bd3482da4fdb308401b4d47bf0fe3f45bc084c9825eaa04a36b06ad08bcd6ec1fd3f96ba3df178ada9f078343238deae325ba81aae2257e6c0d33f8f052b76bb1dd331bcfa147b8404fe482fb1e80469ca8fb0e16defaf2fc6a3dbcba32793348bca633d07de2ba469e61d03b02db2f82ca752e7760a4d7375b3538f879c75f2fd805c29989b9376e3bc83320033dcd1705dad93106a23a2f82a02bf34c453715a219a09dc6f564346c0a02d101173830edab036325cb486440ef1f6e4264252855f148858a96dad6da8f46b320950767cb72c329f0d893ca2f5884a6ea970e334e119bbd87b85c0a606d94142309de3a9555250fc286c3515263cfd80bef8ddf068665fb02ec048467d978b01ffe31d8bec034100a4054bad41860af707b5495af9bf16cbc9b04db58630596097546951873179ef2ab835c5b27de509e0997fc29c37819a0da74d8acebdd2709a6549c5a4643a4439674e51cdf6ed3d25441c208403de9151b10595b63a4c52a4cca4fd2ebcaa704717169a4b68c426e4f096a982d46a73b4201c4745756370000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000021a7c9f6765f6609d436fa015bb1beeb1109ea4423abb514ca84aea016357474183a0b8cfc11341616fda6bdb24c041b7dfd58bbab411167a316c86da761a4a00234a13526c4b3d26a8647f1b90c8504824539d614d597dc857a1472b3916a2b0b4455e590cb2ac3ca7b2bc2a0d4d9ace6209febd29f9574c39e2ac710e6f37e1e19577fce0fbd826f0250a6d80fac9891ed768b758795e3051cc74a9035b06112c167f17675ea35f6d69192abd496006686cfe607c91422aa9647d8f458f28b19f7e46baf78ec10b9f99ae74769e8d32d35e5c891fc1d9d122fab7838e2f717270a1d61c8d2406eccb35b055c2e863b69c8bbecf4b75827aa2340c63f95cde7163c048405963a82c1503a65e1f9123701e04acdd64bcbde603ddfd1e65977c51d279238f4fb194518117bd714f5a2e66feeff4a6665e3bdc4a752673a85fa801b78117e0a7e220e3f497cd692c9ef332dc18ca136b6c00f0fa1796a9c1bc3142d31955a52a5e293c4c11998cd32fe49da121226d0a1855c2bea4be78405f6ea2ca11e214fa1c2085653241b44d6695de343a2a32a54f9d036152c56455ae64512f2da8df4cb0088d1e1b8e60caf5ca732b077158cdadc3c76859e670553088413bad448232d7bd18cf151ab06aaf267988ae1902efa532f849a4dd073e854d00d80532fc271ed9707de1290cae424f093631100177345aae97316192d7ae1c903fec0c97a8908b4de73a20d94ee39809657ac114ee373aeab0c03485289a61a204730251f7d1f91c35abee1a298e1a70cd00d122f17c8e55d543da5573227630879eff6cd9e149ee576918bae9cef592a5c02331803791f9b86336d9aeeef14155b95985ca5596473c5da99f7d318bed5b5b85de5799b17b56b034166042e4a200eec587a832efead72cb3b06d330c1bdc5434ea330b95c541ee580c52e66dc2e0cad44472be4028b3b19293702d473c16f74b2a68c08889a207e99c8a22dbc2e17b9140c45ea5b6e1205f4af4398e295270a54e42b4c8912f74375f35b4df000a9461dd4b34254195e39e87d5f1dc24309437a498052c5c24d3cda7d8e36ef299f96c727cb6682ff1ec5b3c9132d81d3f17a6e1ddeb93713fa122994c693fe1a1676987fce8bbb77161c64aecd0eabf5c13a469c03fc1d567b79c810e0371b05cfd7a7bb3c325b833fefd08eb1afa0fffe914d317a1a0b88a4e78df7b8e1bd2f05efd3154a705d2a8815f5d475678ce2ca522461d497ea725b26437f89f45a11ad0f5d0a18bf43fa089e6860481567b5124e5f9543d2de60f0f0f0347bdb662eb2d2cf22ed7239f435ec2370f829cdfdc1ece650f7912b263d13c0d6e1cf870f6cce1a6c17812e0ef410363426fe138527e8aa0e94517875faedb696ab3dd90adf2507a53e00bc4b4454f2feb2785e9b99c3205efde5be99349679299958fb28b595e1479761c22b5e91d87f3e4c037cbc0acba06e0ed29195ae2dacc034b32148b91bd9c93227f7487601551cebe709e0f632fef8ee9ea439e401f54cf59e193254951087dfd56a8121a9104a2e607ac567ebe32e07a1ff754b8f942f574a10aed4aebfbfaca71f8d8b169eb7221ab7c586e23195f71150e486f48f54116e2bc047dc270bfc9d53f5b98d5decb9e540cb21bf97b4f49f41207142bd8e322200aa09ffd3cb83d88aa9453c3e1520cee1e458ece0b9c10117329b713ab8ce002f34a2af24a186725acd78366e97b1c755e617a2d76899dd3b5c13f11dbc84ae04cbb36d68f9774ba9ee5425e12d64c2d7a2426136553906faa6457af9fe8df12096242cd21879707ef2de36e437ad1e784ed5a544b765332bc533a6570286c50e66b9763f492b24a25c6416f5a3b624d5546f6505db15038fe5f285a5c9c31b26c397cbe34b70bbd617dd8ddb1f54909bfd1b9ff9548938dc2fa74d47ef22340aa850c62f3fe57a10d97c7c69f1aa332e25f19d595205901ef8fddd305fef80',
            commit=0x14eb420594df3412311521e035957609c8c827292dd741220b6500f5308cdf93,
            domain='oxor.io',
            pubkeyHash=b"#LxA\x85\xe6\x91\xfb\xef\xdc'\xca\xb2\xcfgl\xaa\x00;\\\x8a2\xf0\xd4R6n\xe6\x13\x99\xf9\x86",
            is2048sig=True,
        ),
    ]

    txn_data = TxnData(
        to="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        value=0,
        data=b"0x18160ddd",
        operation=TxnOperation.call,
        nonce=0,
        deadline=4884818384,
    )

    await blockchain.execute_txn(
        samm_address='478dC0AF4ABf508b9Cf21004D891C34632FA9986',
        txn_data=txn_data,
        proof_structs=proofs,
    )


async def test_get_msg_hash():
    params = {
        'to': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'value': 0,
        'data': '0x18160ddd',
        'operation': 0,
        'nonce': 0,
        'deadline': 4884818384,
    }
    msg_hash: bytes = await blockchain.get_message_hash('0x478dC0AF4ABf508b9Cf21004D891C34632FA9986', **params)
    # print(base64.b64encode(msg_hash))
    assert msg_hash.hex() == '294e5e3ca094c9568cbcef7dcd1af0dee8025eb45be106f2d4f84ad8ceffc0bc'


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("start tests")

    loop = asyncio.get_event_loop()

    test_parse_body()
    test_parse_body_plain_email()
    loop.run_until_complete(test_parse_member_initial_message())
    loop.run_until_complete(test_parse_member_approval_message())
    loop.run_until_complete(test_dkmi_extraction_1024())
    loop.run_until_complete(test_dkmi_extraction_2048())
    loop.run_until_complete(test_padded_emails())
    loop.run_until_complete(test_msg_hash_convert())
    loop.run_until_complete(test_sequence_generation())
    loop.run_until_complete(test_prover())
    loop.run_until_complete(test_execution_txn())
    # loop.run_until_complete(test_blockchain_execution_txn())
    test_tree_generation()
    loop.run_until_complete(test_get_msg_hash())

    print("end tests")
