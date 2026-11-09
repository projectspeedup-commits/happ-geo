#!/usr/bin/env python3
"""Lightweight geoip.dat / geosite.dat for a Happ "Russia direct, rest via proxy" profile.

Takes the full Loyalsoldier/v2ray-rules-dat files and keeps only the categories the profile
references. Entries are copied byte for byte, so the format stays exactly as Xray expects.
Exits with code 1 if any required category is missing — a missing category makes Xray fail to start.

Usage: build_geo.py <full geoip.dat> <full geosite.dat> <output dir>
"""
import os
import sys

GEOIP = ['ru', 'private']
GEOSITE = ['category-ru', 'google', 'youtube', 'openai', 'anthropic', 'category-ai-!cn',
           'deepseek', 'private', 'yandex', 'mailru', 'vk']


def varint(buf, i):
    result = shift = 0
    while True:
        byte = buf[i]
        i += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if byte < 0x80:
            return result, i


def encode_varint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def entries(buf):
    """Top-level list: repeated message entry = 1. Yields (code, raw entry bytes)."""
    i = 0
    while i < len(buf):
        key, i = varint(buf, i)
        if key != 0x0A:
            raise ValueError('unexpected field in top-level list')
        length, i = varint(buf, i)
        raw = buf[i:i + length]
        i += length
        j = 0
        code = None
        while j < len(raw):
            k, j = varint(raw, j)
            if k & 7 != 2:
                raise ValueError('unexpected wire type')
            n, j = varint(raw, j)
            if k >> 3 == 1:
                code = raw[j:j + n].decode('utf-8').lower()
                break
            j += n
        yield code, raw


def build(src, dst, wanted):
    with open(src, 'rb') as handle:
        data = handle.read()
    kept, found = bytearray(), set()
    for code, raw in entries(data):
        if code in wanted and code not in found:
            kept += b'\x0a' + encode_varint(len(raw)) + raw
            found.add(code)
    missing = [c for c in wanted if c not in found]
    if missing:
        raise SystemExit('missing categories in %s: %s' % (src, ', '.join(missing)))
    tmp = dst + '.tmp'
    with open(tmp, 'wb') as handle:
        handle.write(kept)
    os.replace(tmp, dst)
    print('%s: %d categories, %.1f KB' % (os.path.basename(dst), len(found), len(kept) / 1024))


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    geoip, geosite, out = sys.argv[1:]
    os.makedirs(out, exist_ok=True)
    build(geoip, os.path.join(out, 'geoip.dat'), GEOIP)
    build(geosite, os.path.join(out, 'geosite.dat'), GEOSITE)


if __name__ == '__main__':
    main()
