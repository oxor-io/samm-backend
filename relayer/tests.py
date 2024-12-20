#!/usr/bin/env python3
import asyncio
import base64
from datetime import datetime
from email import policy
from email.parser import BytesParser

import conf
import blockchain
import crud
import db
from mailer.dkim_extractor import extract_dkim_data
from mailer.body_parser import parse_body
from member_message import parse_member_message
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

html_eml = b"""Received: from postback26d.mail.yandex.net (postback26d.mail.yandex.net [2a02:6b8:c41:1300:1:45:d181:da26])
	by mail-notsolitesrv-production-main-548.klg.yp-c.yandex.net (notsolitesrv/Yandex) with LMTPS id Gibp6vREHKqW-WE0G9Za6
	for <oxorio@yandex.ru>; Wed, 18 Dec 2024 22:24:39 +0300
Received: from mail-nwsmtp-mxback-production-main-87.iva.yp-c.yandex.net (mail-nwsmtp-mxback-production-main-87.iva.yp-c.yandex.net [IPv6:2a02:6b8:c0c:2801:0:640:b0b5:0])
	by postback26d.mail.yandex.net (Yandex) with ESMTPS id 3F25860906
	for <oxorio@yandex.ru>; Wed, 18 Dec 2024 22:24:39 +0300 (MSK)
Received: from mail.yandex.ru (2a02:6b8:c0c:16a7:0:640:8515:0 [2a02:6b8:c0c:16a7:0:640:8515:0])
	by mail-nwsmtp-mxback-production-main-87.iva.yp-c.yandex.net (mxback/Yandex) with HTTPS id XOX5Xj6Ox4Y0-ijGuIvEi;
	Wed, 18 Dec 2024 22:24:39 +0300
X-Yandex-Fwd: 1
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=yandex.ru; s=mail;
	t=1734549879; bh=rDkEA62kZ5rHmnwkoCg9d2smSOo4LLL4pzG6nnDxXuk=;
	h=Message-Id:Date:Subject:To:From;
	b=X87YjUuR7YqLDvLkxvBM7QFoc8MwdKxXq6vR8B17u5ChXTLXA5zlP7Ohc26S+l5VN
	 nrbIpV45vBRTBey5pc5e7rd+qhC8v1MhvosbqnC8jR9r8YK1iyA9qEFjmokDFrSj4w
	 Ad+qEDh0uD00a9YefCClaBx0QoHI7fd43NRyj1ZE=
Authentication-Results: mail-nwsmtp-mxback-production-main-87.iva.yp-c.yandex.net; dkim=pass header.i=@yandex.ru
X-Yandex-Spam: 1
Received: by qnb4xdsvdwd5l2mw.iva.yp-c.yandex.net with HTTP;
	Wed, 18 Dec 2024 22:24:38 +0300
From: Artem B <oxorio@yandex.ru>
To: "samm@oxor.io" <samm@oxor.io>
Subject: gaVfYAY9pLtCkNetwVx+BDxKP3kWv9mKm5Nm7L+hKrY=
MIME-Version: 1.0
X-Mailer: Yamail [ http://yandex.ru ] 5.0
Date: Wed, 18 Dec 2024 22:24:38 +0300
Message-Id: <1778131734549859@mail.yandex.ru>
Content-Transfer-Encoding: 7bit
Content-Type: text/html
Return-Path: oxorio@yandex.ru

<div><div>samm_id=11;to=0xD4aF3d17efd18DF0D6a84b8111b9Cd71A039E4a4;value=0;data=0x28b5e32b;operation=CALL;nonce=0;deadline=1735154640;</div></div>
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


def test_parse_body_html_email():
    msg = BytesParser(policy=policy.default).parsebytes(html_eml)
    body = parse_body(msg)
    samm_id, txn_data = extract_txn_data(body)

    assert samm_id == 11
    assert txn_data.to == '0xD4aF3d17efd18DF0D6a84b8111b9Cd71A039E4a4'
    assert txn_data.value == 0
    assert txn_data.data == b'0x28b5e32b'
    assert txn_data.operation == TxnOperation.call
    assert txn_data.nonce == 0
    assert txn_data.deadline == 1735154640


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


async def test_sequence_generation_1024():
    # https://github.com/oxor-io/samm-circuits/blob/master/builds/samm_1024/Prover.toml

    header = [109, 101, 115, 115, 97, 103, 101, 45, 105, 100, 58, 60, 55, 52, 49, 51, 49, 50, 49, 55, 51, 52, 53, 53, 49, 52, 53, 53, 64, 109, 97, 105, 108, 46, 121, 97, 110, 100, 101, 120, 46, 114, 117, 62, 13, 10, 100, 97, 116, 101, 58, 87, 101, 100, 44, 32, 49, 56, 32, 68, 101, 99, 32, 50, 48, 50, 52, 32, 50, 50, 58, 53, 49, 58, 53, 51, 32, 43, 48, 51, 48, 48, 13, 10, 115, 117, 98, 106, 101, 99, 116, 58, 82, 47, 57, 48, 48, 118, 76, 65, 116, 76, 55, 56, 100, 109, 77, 114, 85, 81, 49, 116, 87, 120, 49, 101, 101, 79, 76, 111, 49, 79, 116, 99, 121, 48, 120, 50, 102, 103, 74, 69, 57, 122, 119, 61, 13, 10, 116, 111, 58, 34, 115, 97, 109, 109, 64, 111, 120, 111, 114, 46, 105, 111, 34, 32, 60, 115, 97, 109, 109, 64, 111, 120, 111, 114, 46, 105, 111, 62, 13, 10, 102, 114, 111, 109, 58, 65, 114, 116, 101, 109, 32, 66, 32, 60, 111, 120, 111, 114, 105, 111, 64, 121, 97, 110, 100, 101, 120, 46, 114, 117, 62, 13, 10, 100, 107, 105, 109, 45, 115, 105, 103, 110, 97, 116, 117, 114, 101, 58, 118, 61, 49, 59, 32, 97, 61, 114, 115, 97, 45, 115, 104, 97, 50, 53, 54, 59, 32, 99, 61, 114, 101, 108, 97, 120, 101, 100, 47, 114, 101, 108, 97, 120, 101, 100, 59, 32, 100, 61, 121, 97, 110, 100, 101, 120, 46, 114, 117, 59, 32, 115, 61, 109, 97, 105, 108, 59, 32, 116, 61, 49, 55, 51, 52, 53, 53, 49, 53, 49, 52, 59, 32, 98, 104, 61, 87, 109, 70, 89, 69, 122, 84, 72, 97, 48, 71, 57, 67, 114, 105, 104, 116, 98, 57, 53, 52, 82, 115, 86, 121, 98, 122, 68, 53, 66, 67, 103, 101, 107, 49, 77, 78, 105, 120, 84, 57, 104, 56, 61, 59, 32, 104, 61, 77, 101, 115, 115, 97, 103, 101, 45, 73, 100, 58, 68, 97, 116, 101, 58, 83, 117, 98, 106, 101, 99, 116, 58, 84, 111, 58, 70, 114, 111, 109, 59, 32, 98, 61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    header_length = 379

    member_email = 'oxorio@yandex.ru'
    relayer_email = 'samm@oxor.io'

    from_seq, member_seq, to_seq, relayer_seq = generate_sequences(header, header_length, member_email, relayer_email)

    assert from_seq == Sequence(index=172, length=31)
    assert member_seq == Sequence(index=186, length=16)
    assert to_seq == Sequence(index=138, length=32)
    assert relayer_seq == Sequence(index=157, length=12)


async def test_sequence_generation_2048():
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


async def test_prover_1024():
    # https://github.com/oxor-io/samm-circuits/blob/master/builds/samm_1024/Prover.toml

    header = [109, 101, 115, 115, 97, 103, 101, 45, 105, 100, 58, 60, 55, 52, 49, 51, 49, 50, 49, 55, 51, 52, 53, 53, 49, 52, 53, 53, 64, 109, 97, 105, 108, 46, 121, 97, 110, 100, 101, 120, 46, 114, 117, 62, 13, 10, 100, 97, 116, 101, 58, 87, 101, 100, 44, 32, 49, 56, 32, 68, 101, 99, 32, 50, 48, 50, 52, 32, 50, 50, 58, 53, 49, 58, 53, 51, 32, 43, 48, 51, 48, 48, 13, 10, 115, 117, 98, 106, 101, 99, 116, 58, 82, 47, 57, 48, 48, 118, 76, 65, 116, 76, 55, 56, 100, 109, 77, 114, 85, 81, 49, 116, 87, 120, 49, 101, 101, 79, 76, 111, 49, 79, 116, 99, 121, 48, 120, 50, 102, 103, 74, 69, 57, 122, 119, 61, 13, 10, 116, 111, 58, 34, 115, 97, 109, 109, 64, 111, 120, 111, 114, 46, 105, 111, 34, 32, 60, 115, 97, 109, 109, 64, 111, 120, 111, 114, 46, 105, 111, 62, 13, 10, 102, 114, 111, 109, 58, 65, 114, 116, 101, 109, 32, 66, 32, 60, 111, 120, 111, 114, 105, 111, 64, 121, 97, 110, 100, 101, 120, 46, 114, 117, 62, 13, 10, 100, 107, 105, 109, 45, 115, 105, 103, 110, 97, 116, 117, 114, 101, 58, 118, 61, 49, 59, 32, 97, 61, 114, 115, 97, 45, 115, 104, 97, 50, 53, 54, 59, 32, 99, 61, 114, 101, 108, 97, 120, 101, 100, 47, 114, 101, 108, 97, 120, 101, 100, 59, 32, 100, 61, 121, 97, 110, 100, 101, 120, 46, 114, 117, 59, 32, 115, 61, 109, 97, 105, 108, 59, 32, 116, 61, 49, 55, 51, 52, 53, 53, 49, 53, 49, 52, 59, 32, 98, 104, 61, 87, 109, 70, 89, 69, 122, 84, 72, 97, 48, 71, 57, 67, 114, 105, 104, 116, 98, 57, 53, 52, 82, 115, 86, 121, 98, 122, 68, 53, 66, 67, 103, 101, 107, 49, 77, 78, 105, 120, 84, 57, 104, 56, 61, 59, 32, 104, 61, 77, 101, 115, 115, 97, 103, 101, 45, 73, 100, 58, 68, 97, 116, 101, 58, 83, 117, 98, 106, 101, 99, 116, 58, 84, 111, 58, 70, 114, 111, 109, 59, 32, 98, 61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    header_length = 379

    msg_hash = [82, 47, 57, 48, 48, 118, 76, 65, 116, 76, 55, 56, 100, 109, 77, 114, 85, 81, 49, 116, 87, 120, 49, 101, 101, 79, 76, 111, 49, 79, 116, 99, 121, 48, 120, 50, 102, 103, 74, 69, 57, 122, 119, 61]

    padded_member = [111, 120, 111, 114, 105, 111, 64, 121, 97, 110, 100, 101, 120, 46, 114, 117, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    member_length = 16

    secret = 1903

    padded_relayer = [115, 97, 109, 109, 64, 111, 120, 111, 114, 46, 105, 111, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    relayer_length = 12

    root = "19784567368917694627616026563131106212262468231239849638835610782052174261261"
    path_elements = [
        '3035447771851554437838619175450331829996564400984508347694600085723905209853',
        '14744269619966411208579211824598458697587494354926760081771325075741142829156',
        '7423237065226347324353380772367382631490014989348495481811164164159255474657',
        '11286972368698509976183087595462810875513684078608517520839298933882497716792',
        '3607627140608796879659380071776844901612302623152076817094415224584923813162',
        '19712377064642672829441595136074946683621277828620209496774504837737984048981',
        '20775607673010627194014556968476266066927294572720319469184847051418138353016',
        '3396914609616007258851405644437304192397291162432396347162513310381425243293',
    ]
    path_indices = [1, 0, 0, 0, 0, 0, 0, 0]

    from_seq = Sequence(index=172, length=31)
    member_seq = Sequence(index=186, length=16)
    to_seq = Sequence(index=138, length=32)
    relayer_seq = Sequence(index=157, length=12)

    pubkey_modulus_limbs = [
        '0x0d71454db865833bd24183ce11474b',
        '0x54111bb3de7212b36b489acd64c801',
        '0x16fe312df80c86e90a00a2d07c503b',
        '0x3e3c66ea95c9d943c9f2de77403abf',
        '0x48f9fc8d82ef632668756d4c5ccda8',
        '0xcfd84f5ed624c7c6159925d201e090',
        '0xa531db02e88d879f5336620a3ca5d2',
        '0x32312e47accf3d5d6331887cf1fca9',
        '0xc473a2e473d90b1e',
    ]

    redc_params_limbs = [
        '0x7fa126f8caddad0484799b70222629',
        '0x72e3986faae498cfa0f6e5ae53927c',
        '0x135a1f36fb7cff2c8f87a7a84ca5a0',
        '0xbfffe144785d18c615a038e2207a75',
        '0x81bf17327eea8c4b1e24e2f00123',
        '0x749fb6a4401abbf2fc54347ee7aa76',
        '0xeff5be07f8eada2d199f9979865854',
        '0xc14a830cbd2156474d941a818514a9',
        '0x014d993956f5d74034',
    ]

    signature_limbs = [
        '0x31546317a7cda1d775ec386503b505',
        '0xae84169c6313889b00c1e7fd799b7f',
        '0xbf61fc20e15ffd0ce2ac057d306826',
        '0x2461fb7e9e620c97dd66cbd4704c3f',
        '0xcbe2b567a7d9722326eb7b4e69744c',
        '0x564e1d8a1778def32bdb6e2ba6e8d6',
        '0xd58e39541156e471b297283082666d',
        '0xf2f551753d17d2f093ff1e2f141638',
        '0x05dd8b6deb1b54a8',
    ]

    approval_data = ApprovalData(
        domain='yandex.ru',
        header=header,
        header_length=header_length,

        msg_hash=msg_hash,

        padded_member=padded_member,
        padded_member_length=member_length,
        secret=secret,
        padded_relayer=padded_relayer,
        padded_relayer_length=relayer_length,

        pubkey_modulus_limbs=pubkey_modulus_limbs,
        redc_params_limbs=redc_params_limbs,
        signature=signature_limbs,

        key_size=1024,
        root=root,
        path_elements=path_elements,
        path_indices=path_indices,

        from_seq=from_seq,
        member_seq=member_seq,
        to_seq=to_seq,
        relayer_seq=relayer_seq,
    )

    zk_proof = await generate_zk_proof(approval_data)
    assert zk_proof is not None


async def test_prover_2048():
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

    signature_limbs = [
        "0x0ef6ec271d19ed41602ffe2e30c0cb",
        "0x729e6fac41a145c51ba5d2e5bf0620",
        "0x11bc2248c6c5ed160b70e391f7e77d",
        "0xf7c9177c65d3c1b96c19f15f26b695",
        "0xe4923be8ef886acfcb697ac5850fba",
        "0x87b006e04b3d3d24847f5a231055f6",
        "0x2de73f5d31249cd479a69d56b10885",
        "0x727b6b488779df5dd106233a96ce91",
        "0xd4c4d448642f295114310f4651fcc6",
        "0x270515e5c52241c67af070af4096ea",
        "0x5626acd694f8b3d1a44e666afae946",
        "0xb6c16a808507ad3b53aac2410111eb",
        "0x8bb625f6320c80f92c22cbba03e4cc",
        "0x913303b643f219631de1dc5df6fed3",
        "0xe8a10e24ae463d6a6b4ae18c4394aa",
        "0x20c35e76c9ddf7c1d74cca30884be9",
        "0x32c60e6da41bdf42424e8b61fb5c1c",
        "0xa3",
    ]

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
    assert zk_proof is not None


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
    assert member_message.txn.msg_hash == 'yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68='
    assert member_message.initial_data is None
    assert member_message.approval_data is not None


async def test_execution_txn_failed():
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

    success, txn_receipt = await blockchain.execute_txn(
        samm_address='478dC0AF4ABf508b9Cf21004D891C34632FA9986',
        txn_data=txn_data,
        proof_structs=proofs,
    )
    assert success == TxnStatus.success


async def test_blockchain_execution_txn2():
    proofs = [
        ProofStruct(
            proof=b'000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000000ac0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000b385f5d44811ae2af047efb39be214f5e700000000000000000000000000000000002be8c19f8336b8f9ac700c5597feaa000000000000000000000000000000393122004d402392f8171083cb4581cf3b00000000000000000000000000000000002400d790bfd2ac8e1835f2b0cdbe150000000000000000000000000000000df8cdd5e720a8e8cafa7c8cc1d86bd84200000000000000000000000000000000000958cd0a37ec023ebba5a7d23a137c0000000000000000000000000000002c6a123c7ae1646ce402122d7826bb187600000000000000000000000000000000001637596e470dd04631c0a1a5197801000000000000000000000000000000fd7cb744c7bc690c50536aa27c633ced4d00000000000000000000000000000000000c17cb55cb2e8134aba5507dd60a43000000000000000000000000000000bdb24899a759fab0ad9fdf1ba40b0a45bd00000000000000000000000000000000000d33eb6528d1568dea0d92a513fc43000000000000000000000000000000ef11c32ebd5b11cdcbed5ecd996be321a400000000000000000000000000000000001e171a750dfb8593106a23b306ef52000000000000000000000000000000b472dffa0c824884270fe4db0fc376499700000000000000000000000000000000003013ef879ea7cfa5b077f673bd13d80000000000000000000000000000002bf07d177aa0ad334ad01df4d50a40c5bc0000000000000000000000000000000000131d0acf526d5fb55fbc58af4bf4ea0000000000000000000000000000008941bb35891024de2456c3a13e71ea1bc400000000000000000000000000000000001d6560677cfd71f209c2532985f53900000000000000000000000000000022ee321382ca81ed75778ece44136b43b3000000000000000000000000000000000012ad43172288f75d6fb882bf23c9440000000000000000000000000000006f6ec2e709868e6c7f6e36e813b5b9b046000000000000000000000000000000000009235bbb8be017fb156d09bbccdcab000000000000000000000000000000237c69be03ed52919087c5f2e64c199d3f000000000000000000000000000000000021fb7d07dd1c84971645eaf3c207880000000000000000000000000000001b05d1829a4bdfb92f2140b9cb3fe174cf000000000000000000000000000000000012bca6d02b1dc7c00246ea65a464140000000000000000000000000000002ef1c0e903e0c5b2719ddae642b56e802300000000000000000000000000000000001c1ad2a419b0afbe6f079bbd5060d60000000000000000000000000000002214e199b2e6c808b34ed6884dc663f13b00000000000000000000000000000000002831245df877ee8e976a6041fe62a308067fc33d90d0b64c07bb74236c32ee188fbb9e902d176b2985e646e62edf15285dceafa3a0cf736c488a425e15256f0fa42ca9e98c59261a5c0f4d09d120ec0d3ce90c3e1254415e787cbd8ee0e458d076e5df7ee21049db5543071ffcc28d0cfe215e8cd83604355b3cf841d5545b360d39f18f16e1619feb566fe4b38a4521b4d45963d0d4de59cba9013549d2c87c759158996c084a69dcde8700b7766a098cb8b4c685499d2bc5451848c3903adea70911a83130761a99b99532f138071e98f26ef2410bcabb3a8b009b7f84cf893a653e13b8616f202ab4f264962845103250bb6499abf2cc0400be4415d08186f1bb659baa6719c356eba2980db88229447ec151971263c454e82d65160b143f571c6bc1b4f2397001c0edcc6877de1f985a39dded820525db790e6816de21c49332327a66502b11e0b63b07336ced2c6c02c3d4aaf6e576242202a0131f897e11b59be32ebf18e1e8d19360190f6d260a9e3ab96f4f85338eb20b06c9e6cbdcb1fd632123fdf6697d9ab15466ee832c8b79610cdb45b3379b92bc3314fdc2249d0e137542d6da1e8803a1e364a3ea2bfea8b3f3818a36dff7ee2b37dfac751db679d8c58ca76518d51057891ea5900421ddaf83455bf97962d7cb51bc58b41266294711f1a1de308baf96c31b883420a9e3807a4eb66fa4628ed5192cebcf9ff69f51019f3b1a52dc316b66d8743a2f84449c813ecf8f73c0fd9228a8b4d4717ac54f52a7cf03ef8e03c62bf7a0f6293c162b4eed22bde7d885952118c4fce30c34f66a810c9803961d4b96956d641115553b43a58dd9df07a0e17b95581e72c04735bdd5c88d1226e4998b3606272923b80c3451a9a4180a38af4a7b42bcee37234b13859a91b7aa7f2bf0d70ffe0f89884743b3e32a9160de55a54d38977467952b84d2bd8f0a7ba87570c9e2872fe7df7b05a45f88282ca3b954529ad9c2f395e9f194ea3a5dce5b2f1d00555b2b60659f74df911d56f086e4f2990489c225b8be00f6452e9cca8e005581577f1e2e113f90d00f863ad1e3a24b6ade45529be764e059eb929df2fa91bfeeafcc20d291f32dbc2616e9f3d82fd8956628c11825652427fcd03b176bd7d97b44da08e6ddbe24b2155809693b506e4e1466972b46e0ccc4e7ed7d3a39874cfe9c592c7c2004cf9d55e0032f8b2fc6a58a4b310da47a803d17c7ee064f69473f283f291487c25890cbe3ba5f8997f11af5945cb5f6ffd48c00bee5c51f469b83c39a06700115f8b1892816cb18e3c9ced66c340431c8c0f9ce555829e7ee352126c8002e3b39dafa882a9ff4332a1b25ccb587f58a17fa2eee528c49461b5749eafe1dc1e03c829ab9b35d5149de2c99cf8c1fd6d1b111d73da26dfe5a78c8f370e02174f5aae596d0916797e875d5757e31c5a15accacaa77af7e9da8a4d6398cb014779a704d1e252316e737219643ab8f54e0007b04a0969b3f8f76e0a19edb5f2e3f525c9d4450e501a80436cefee7c0bf865b21aac82ce258216f217d9cf6622fc141e96a28ab7a6130467dcc38d1f50ce9a400a3e9792ad9f0f5b61cacf4fd017fdf296cdcec10fcb8282543bb1741a15ddfcfa7d08d6b42fe1fdd4417926228b2e116382de894d83e66663ddf62b8d7db056caa2a7df7c61f128ee44487ad17caafa115dd719d43a74d8750097293af6bae14f1de275f16fc1c77cf264e2316493ac480820e880cc423f1075f090fcbf4a2fac0dca83952d70244094ff9d90c3c2747e32bd6723bf7867610ff055348f003586af392b701dec8eed8aaf00b1ee65d52edeaf93c0f7158e33ceaba583e2214c70d97965d35e12dbc4795041326919c66d69938bfd0fe3e121aed8343aae0fdb5ac294c3cc0bcb0887ffdc44e272f5c62ea7d63719643eb3ada88fd964b31451f56ea392a9c76c1829cb52db027ce528cf589030e4e2c447620f7a238e769bf7665ab2146dc2bda399780953522a1bfef8bcc7c226a12c9f541e82d355fd4833079fba3ba220056481775eeee077af3ef4ae6aba226e7e4f53198391536754392ddc0482cfa1ddaef894766391f6a691d3c39222646acdad48a37537dd4931635e4c43fd1264c1c25b637de2b0551fed74ea7ecbaad4baa1b37fc9b37cc9ef047fcf07e383e3adec1abc92b2a2b0e9cb90aad948f7cc0d57f16d5e94aaac8da6c579072536ae409f7c506e22a2cf0d2ff732f9fd73f4d1a6da354de89a73b7966c5d0ed51f3eadd1123c2055f1732b44e9ad88a5c09bcb225b32b1cbeb74158841e2ab792dd4f50612f9d315316ea44dc2503694333c749ba3d59b95689e4ed8464d2fe0081f68323a22fba72230558fdaca94693008fb5bb45d5a52a1eef3db18e4ba659fe08906194e64a0003b7fc3f5eaca29224160d694e9e5f115984ff4577b99f6b8b001a8516d0d88e300936c19b2dc11a1876c9e05b6760b74702d8a016eda4339b4a4f9e671e9eb30e521ed0a461b5e83b497ddf21716ee031152994e80f8c6a6bc870c33aa2c51b028852d3282095b3bcbb0f01a20a8002774de9b994cf38b205558c8363b20b2712b88ec3b6246b798f7cb4e30e32bc96838bf5c8aeef48eacb29f9382941637a19decfaf811219a255b4fdd4ced7029fc0b369b2e46e4ef53f0c29c5318e47f4020e1377a0d9b74b8606c177f349e64395ac6145981f16f9f59e5ba0bea23b8116d9bbdba3fabd195103e84580663b3b85ec19c01ace7958e0c43c01796e9af127af91e1a017dffb0fe2f31b2c991de377eda13a852a359ffc47922d385b261625fb47c20d1d98670407ee104c651f2ebb68a7c7595ee213f323f18d75a45dad2a6d97fcfd0cddccec4acba08364baa8f38e9b772c8c812a7f2142566365e84b16e53c3f501d3707853bf6afc61e22cd2e9f2330fbe1ce9fc3cbab850e57d89d049f33381db481795a164978bd397676955b3fe384a1b4582af3689fcdf2c6ad026c0e5a16bc719392be0a31a57db21049cbcd6c61d2faa7cbd3c4f66dce396f08d2673ac328b9fb144798a9c186e82b5c2da6d4e0b547bb6e03e804701e6e9525a62ca63a6532ca91f0b1ce4d2c4f5b0f23ba36f268ef52a72a237dc069d93e0627de917ce68542560dab763604943f24d28c0714f694029f72d3a6414cc5af242c69330b3fe16a94ddf80718f7b9d2fc7c4e9235285f7f7f3a1f6f60cf6c850e4a98dc87f3cca594982cb7a4f5550931657f30f05a46b479f25a9dec5f6de82a24eddc4a89fb7876d189f7ad87086273a0b8ad754a578dd324f65981ad081c2c47c7596d9e7ad310825dfb4c7a55dfc12b21b0bd4aa1e76e9b0613aa20b5db1925b89ab45b78eabf39ca0e67c04a1fa52a94d36a7715a73891da525c2a05a8131ee1f76407e65d6941ab85a309cf542d781cba5b54b2fb068c6ae570b8ab72202f939c53908b3ae27cbce3a8cc9aeec42606097efba175a11d0e6716acc350299dd111580ef4df695dd5bcb15ea6e824aabe30400dc01d52c1c53e602322ac0fdc4e45b3285c8942918baa06851f7f8389cbde5f9c12a707b3472506da57090e02fe1bfe204758159408ad734b1f89748fc4f6af9281703328addd2b24081e2cbfbc8eda5173300fbfa34676dac5ea1cbfc55cf7eca57501814fbaae547d7c19696f5bfd9f43e233d3d582d8b8a96a8213a11c1ae84b40390e81b68e41d7832467896432b29cb496582d725aedbfbfd68e2c29ce95c6dbd5503c4cbb149096026b18648bb2912178e5cbd2e63e2b84a5eb5614c37d41943bd979ce0b3a05e01ce84a08d5fca7bab30c978d9dd06f224f51242559e14b01af1a0fef53afa83e24dc105030cce9cced9c5cfea60929df77b0d7899efb2a2f188fe1dc20f3e75e02be64d902d8c2cb251aa4c8b5cb121abd3becca5e6226b38efcdde4bd0b06bc1726749e7cd9d3e8a542a2b4fd3cc9136dc88db9719ced972bb8c498ad24c23b255941d265e053dec2bc06fd23692a6a370619a061a12d40d8886e7f1a3f047d1079d42f92478114d774a87a93cf4488b86aa3533e5c6a2165b92aca422c60d20ec36a6a406e28338567257da7177c5820a6d974eb229b8baddb7993b0a2947e0379c8f62cf1528166216d6292b176d8e0acc8a7815cebccad2334f5e4c2f4da0a5e2eef73bcb0c38eb93a1833803919613eece223b34896d137fcc78b8837be196ebb654d1dcadd4a21dac00e6c1147e565ba5fb6c865c6723fd7b773539fa51b35c6312ff490d88c1fc0cd6ba16bb7e2de18e01c5d4723dfa72017c2e931f819a4875d5e1e71e7c78f3bcbbc996a88a852a91df9852fea5c255e3b5c69e81906e5d69e191135f2713e7af73cc3bd2b71c6b191332bfec75b06f2f7aeee6d5519d91fcce887e6d0ef0bc2d3407354dcbbdf38cbc1743631f6166a95a198df0a1bf5c57a75f973c00c3796c59792d6527bc3005526e07a1dc46a107b1471705b1a62b1315d141231dd963a268b95ad3882f1259f3e39ac69b276d2e3524468582bff9941024a0236cf2f5e80c847dbc504eb1ae05a4ae615d71663cf35eb83ca1b080ad12a330506079f80b611fbe651ab08ec6b184cfe47e51f052cc94bbc9114042d72fc481f746ff078b9660aa5d26aad48fd1d4788752535d01c2904e83a1848ad0566a468ae944cf75fe327bfab3827f6b61bebab1282e7aa7c4b6104662b67b1b8bf7c5dc7854c3dbea09d4b0bcee882a14e2845c2f5b1471dea43008a23035d3bc66a25a046668b1f9bc442368b19c4d62f6b63dcbef217b8cfa38c9f2a534492a72c5072ac1ff1d6174fda435eccf5eca9d4ca870a3b1cf4e2a028d10f8d925cdfb376239374cdbb4ddfa1c7fa8bf8b0bb1e4183ea15bc675f37a2a00f10a09dd108b2746148fa266bb73f76b34fa235b06006a5d53ad90b287b4aff21d9d8ae1f0e47a8c0d2b3a6d29571725b4df325a6fda1ee5b00b8b2d2ea78a62f6b0698e0ff2178c72d94d1ed328ca4df02eacd377be47113ddf89155a8a87a274be2ed7dc26dd8744a7957ae17553f7789a069a79a0b730ddee16eaabe89c9079b0e899564ae63ca1fa8a98f2301bef11825f2b150495ca64109aae2dee20714e6d83c8623167bd452052fc1d741cc1fffdab8797cb1583aa1889bd1cb738c0e9f5ab079f069848cbcbdc46b4d85dbff10af8e24e0eacd139d140f3f1f76e70841523a67b68c8f6327c07c761b7ac39a742aad834f24647db5fa30af9da394105a7f79c536854dafa7958f86c1359b85b97aec2ee392e27602840ff8e3a34d10f09f5db908c9a2fac1f33f9be852f9f7428d9906b5adba90d184a6d81e9d4413b392ebabaceca690be866a43305f0c2444d44f16e255305394e1c9a37d535c28bd9b3a1f22d8b1aeaad547fe092c394f60b4b529a1740a6e382fd34c5bc98927cc1cf19ef8acebe16c70421a80efc512c7369912265144635ee657f803ee2f1715187513d7a5a5d8bd9778675a22a8a23fc457e1899f04a08cccf079f6fcd61960e40659fc3e6694752ab7c26d53860f620ab2d4d96eaed0b349a86d21d9f02a1ac46b9fc5ed720ddf35db96357f8294bf9ce71f65df8accd6ee9e5248ec010dfe6923df5aba69a5c8ef3d02d62a568bc3f5fdf2eed49533c7e6fe36eb39d40182f6c3d6811d0fcf908d8965e1f1f46cbe33c1671aa10e017ee6af030620261703d88d3c9c31ecc5661bb97fb87417c237a7bfacaaab7a96999e6af492b2480f46b12f17f9844c7640d2baf36e4a332a21f3fb997c4ded94768bd595b2c76e0837dfccc774051e94356a3f9c7bd9860251581ad64a96f8524acc709e296e89043aff9ffc5521706eb371d64599a18c91d16be7d7aa666a7950503d5dd88252084573770804b37def76c735ba3c7b1fc0214884340a11b79c5330de270a0e6514408d1b54adaad0f81eccbf3149d5b2ccb8824a18ed0d3a738d346e990693550f52b58212997db79f6e36eff29e452c79ae8c2c9d0ea2c282716de65959ac590d3121a5183126566ddb4be8c20dcfdb2fc210c81269cfa3e68cc3313db6433e009316cf62fbb5ff7fad38e24eacbe3c268f4e96b163d300112f63596d293c2c0e820a23594ef71d4005575111eb504583d6dcb0477e7e9233520966107c02d107d80982317c298b201b9c63e10b902dec7ff00cb903f87323f7cb13a39163ca2c2fcf78c51efdae627705b8d9ebad6d9b7ae334411c8708313ca2bb799fd20e1931f6564c46d98ec6f6e350c7a5d074a91a4345341ef2540862e6c6d7584d831625c63a3bf3acbb80bff0641e17f0cf3370b1cf59ceb60b71085f0b969c234b0dc8b04a507413cc8460bb17b7315374c3aa625389fe2d78e557dbd876aa39082da397c810877d634c3380a8e80dbc1170100ba9d952875ecd77997cbe136bc808a5f5297ca79f9d0add4c45488d6047b21fe01fd3fdb5356584f60ae53f0f141ba35940b61c669f09b638748ef532b29c6b2c5ea354f4943cd5f0ecce6fc9a20000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000024590573b27cc1050838f95f8308242c87179a1d7375b9ff26ab79151fecda5b20d22c0d03e153fd7e4fb75186186e26f060c5d1fdd535a47fc698629f5bbca6281ed7f6d9be9e4955732445bfbc9227aa2375e918999c87054c198f4114421c2e40dd9aba04bc173957a3bf06a9d680a909710bc7e4bc5676c0b9f4c8e50c9c0fabac329aabb062f2aac061163d74eebf81712dfeeff0b4b591f59a98aea1ef22acb597c5c3117abfb2ebb940fe35dc8e421bf078271ec0ca82d01e9554d6ba07dbaa9dbb95e3df11333689f6df9f7afbb2e39d054e037d04ea08644bbc6d1f1620678b97fae978bfaa643e16364114bb0825d284bd3b47fd1339f41cb39f1019934503d73a4727ac861cb627615b23b3e737605c9f5c784de2280696bcdfeb283a94e0db2440405251593afbc0b5ea5ffdf560a935b27d663969c8e48156ea0a497da67d13ec98938a0a7f67caeee3f3dfda416a927db199e7da2de540e9640ba211bdad77d259f8a3486049e492ca4f5a26fefac9d768ab2326706a39c35e1e27484742b17526ea5afa8a466ab6ea70f3c2d33df005c5b0374bb33e7df3a02711022b748971d60cff31cd4297412a01293a9baf70aff845979acd80907d6623b3771a3a3410fdc3a2851a1aaeaa0e5dd99a3f2df0c2fdc71243ea6cacceda2632fb9d366cabbac8f10409331f9a0554bb837c84b6e0de0766f2ef94c567bc07f454eafa2ed5310fc8331fc80f28b38f972d403726729dd374a5af3c46ee1f2981f771a1ea64b76c4653048d32b14a98a8bf8c573b56cfc7f24da284cd2dff2cd99c91b14e95d22d1dd72bec32522068740c1decec9a9b7dfa88f23295a2441914abad013b713fd79f67f56619c5f3dcd6cb02a7a91f90366a181ec16ae9c919f9f9e58a603e212a34db5ec64140c802d01d3bbf5453b48dadddf333be1a8f06ec31700329f7f95402c75e56f02e2f7decc6197530850894c5fe91215930dc1d5f4d408d011eb9bf655f93d30c70b10d34b2c501b875bfbf2cb7c1302b1ea30e0412089708fc3ab34a9e9801161a02683caa58fa73f671af2ee5f55dab61300f5b1979e17b127a154b74efefac1fc3010c25842471d6029174dc93006492570c8abeed324494b79def203805d6f13267affef03cc8760be8127311c9163bdc200cb9d61e8ac20fa78532976747b680305eeb8120e91ddde0488dfbc66509050d7611988e34ae8d89a9dba67aa7a385b166558fb8140480e54b84c6deea24f015485b22e98061ed97a111231a6f40a50a35b1f958549c57b9453e1db9d2ca92241b3711ab3962d8656c899e4be5608630560b5d138d22df2b56c1aafe6cca1d208948f8dddb773ae835846d1c9bbbf5e9a814088ee92fb3d0a02fa5a6af7a531dd5f8abe0d42dbb36707db46e0f9eb5bb4f45c068aaa1c2fc7d1dadd037bc3c15b11be2bd3c6ebf949b0b300bb17a1819989a5305a4b0b5ed8c1c58b9b51cc1280d9a2889479fbc341389ccdd6dd89a6d9ca7803f83c0719b1f599fdfa9c9ce13872230151983154b29a6e828f45b0440dbb5e8cee3ca33085e5f15a239ca292fcae89820436b9508d2d20219ec397c668a297ad6c7fb66150e54a162ddf2140c19c816935c53f79c24c8f35d5ac9ffbf28961ae644f9807b54d3ca6635feb00a1c2bc1e196b84918d8ebf4a92ec2c50fa5c2c1d9fe5a8e3d8c42d792142d4b14d218b411c54ad1d329dd8fe713820a8ad725e83fd55e514a76d90a3c90991907c878ec993c77f7a02ea808fd4ab30c4700b1602b23ec5a17387192ad7235632e4a976c67c69309a8d27f0edc787492695001b48ec2503fc6f50d49636a05be160a78c1a73423823ccdbb2fac5a0acbd83740029a6d26e4da6745a92f6b89f4016d311c0a58414bb801f6e5276e33aff8e9b4cc79c1f3a483d26fb5717c00b22801bf3c4d36f0f9a7e371618256d9c727ff0e3d544958dd798dbc009a3ddee9',
            commit=5297742383160219776806182884581707766356804159929071365223500484103409457402,
            domain='oxor.io',
            pubkeyHash=b"#LxA\x85\xe6\x91\xfb\xef\xdc'\xca\xb2\xcfgl\xaa\x00;\\\x8a2\xf0\xd4R6n\xe6\x13\x99\xf9\x86",
            is2048sig=True,
        ),
    ]

    txn_data = TxnData(
        to='d4af3d17efd18df0d6a84b8111b9cd71a039e4a4',
        value=0,
        data=b"0x28b5e32b",
        operation=TxnOperation.call,
        nonce=41,   # not used
        deadline=1735057548,
    )

    samm_address = '0x5d2141a87c2ae3515333df2aac4dae34725d475d'
    success, txn_receipt = await blockchain.execute_txn(
        samm_address=samm_address,
        txn_data=txn_data,
        proof_structs=proofs,
    )
    assert success == TxnStatus.success

    params = {
        'to': '0xD4aF3d17efd18DF0D6a84b8111b9Cd71A039E4a4',
        'value': 0,
        'data': '0x28b5e32b',
        'operation': 0,
        'nonce': 0,
        'deadline': 1735057548,
    }
    msg_hash: bytes = await blockchain.get_message_hash(samm_address, **params)
    # print('MSG HASH', base64.b64encode(msg_hash).decode())
    assert base64.b64encode(msg_hash).decode() == 'tZ25sD8y506IPhtXSPosJUQW3vmUTxE4o2kgZgpSzjw='


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
    test_parse_body_html_email()
    test_tree_generation()
    # TODO: pass DKIM verification in tests, because DKIM signature has expiration period
    # loop.run_until_complete(test_parse_member_initial_message())
    # loop.run_until_complete(test_parse_member_approval_message())
    loop.run_until_complete(test_dkmi_extraction_1024())
    loop.run_until_complete(test_dkmi_extraction_2048())
    loop.run_until_complete(test_padded_emails())
    loop.run_until_complete(test_msg_hash_convert())
    loop.run_until_complete(test_sequence_generation_1024())
    loop.run_until_complete(test_sequence_generation_2048())
    loop.run_until_complete(test_prover_1024())
    loop.run_until_complete(test_prover_2048())
    loop.run_until_complete(test_execution_txn_failed())
    # TODO: mock tx mining in blockchain for tests
    # loop.run_until_complete(test_blockchain_execution_txn())
    # loop.run_until_complete(test_blockchain_execution_txn2())
    loop.run_until_complete(test_get_msg_hash())

    print("end tests")
