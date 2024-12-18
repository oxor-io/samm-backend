from email.message import Message


def parse_body(msg: Message) -> str:
    if msg.is_multipart():
        # TODO: check initial_eml
        # return '\n'.join(_parse_part_body(part) for part in msg.walk())
        for part in msg.walk():
            body = _parse_part_body(part)
            if body:
                return body
    else:
        return _parse_part_body(msg)


def _parse_part_body(part: Message) -> str:
    content_type = part.get_content_type()
    disposition = str(part.get('Content-Disposition'))
    charset = part.get_content_charset() or 'utf-8'

    # if content_type in ('text/plain', 'text/html') and 'attachment' not in (disposition or ''):
    if content_type == 'text/plain' and 'attachment' not in (disposition or ''):
        payload = part.get_payload(decode=True)
        return payload.decode(charset, errors='replace')

    if content_type == 'text/plain' or content_type == 'text/html':
        payload = part.get_payload(decode=True)
        return payload.decode(charset, errors='replace')

    return ''
