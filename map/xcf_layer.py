# -*- coding: utf-8 -*-
"""Minimal XCF reader - enough to pull one layer's alpha mask out of map/locations.xcf.

GIMP does not have to be installed or running. Only what this project needs is implemented:
XCF v>=11 (64-bit offsets), 8-bit precision, RLE or zlib tiles, and the alpha channel of a
single layer placed at its canvas offsets.

  python map/xcf_layer.py <file.xcf>                 list the layers
  python map/xcf_layer.py <file.xcf> <name> <out.png>  export that layer's alpha as a mask
"""
import struct, sys, zlib
import numpy as np

TILE = 64


class Reader:
    def __init__(self, buf):
        self.b = buf
        self.p = 0

    def u32(self):
        v = struct.unpack_from(">I", self.b, self.p)[0]
        self.p += 4
        return v

    def i32(self):
        v = struct.unpack_from(">i", self.b, self.p)[0]
        self.p += 4
        return v

    def ptr(self):
        if self.version >= 11:
            v = struct.unpack_from(">Q", self.b, self.p)[0]
            self.p += 8
        else:
            v = self.u32()
        return v

    def string(self):
        n = self.u32()
        if n == 0:
            return ""
        s = self.b[self.p:self.p + n - 1].decode("utf-8", "replace")
        self.p += n
        return s


def props(r):
    """read a property list, returning {type: (offset, length)}"""
    out = {}
    while True:
        t = r.u32()
        ln = r.u32()
        if t == 0:
            return out
        out[t] = (r.p, ln)
        r.p += ln


def load(path):
    b = open(path, "rb").read()
    if b[:9] != b"gimp xcf ":
        sys.exit("not an XCF file")
    ver = b[9:13]
    version = 0 if ver == b"file" else int(ver[1:])
    r = Reader(b)
    r.version = version
    r.p = 14
    width, height, base = r.u32(), r.u32(), r.u32()
    if version >= 4:
        precision = r.u32()
    else:
        precision = 100
    ip = props(r)
    compression = b[ip[17][0]] if 17 in ip else 0     # PROP_COMPRESSION
    layers = []
    while True:
        off = r.ptr()
        if off == 0:
            break
        layers.append(off)
    return b, r, version, width, height, precision, compression, layers


def layer_info(b, version, off):
    r = Reader(b)
    r.version = version
    r.p = off
    lw, lh, lt = r.u32(), r.u32(), r.u32()
    name = r.string()
    pr = props(r)
    ox = oy = 0
    if 15 in pr:                                       # PROP_OFFSETS
        ox, oy = struct.unpack_from(">ii", b, pr[15][0])
    visible = struct.unpack_from(">I", b, pr[8][0])[0] if 8 in pr else 1
    opacity = struct.unpack_from(">I", b, pr[6][0])[0] if 6 in pr else 255
    hier = r.ptr()
    return dict(name=name, w=lw, h=lh, type=lt, ox=ox, oy=oy,
                visible=visible, opacity=opacity, hierarchy=hier)


def rle_plane(b, p, count):
    """XCF per-channel RLE, as in GIMP's xcf_load_tile_rle"""
    out = bytearray()
    while len(out) < count:
        n = b[p]; p += 1
        if n >= 128:
            length = 256 - n
            if length == 128:
                length = (b[p] << 8) + b[p + 1]; p += 2
            out += b[p:p + length]; p += length
        else:
            length = n + 1
            if length == 128:
                length = (b[p] << 8) + b[p + 1]; p += 2
            out += bytes([b[p]]) * length; p += 1
    return bytes(out[:count]), p


def alpha_mask(path, want):
    b, r, version, W, H, precision, compression, layer_offsets = load(path)
    if precision not in (100, 150):                    # 8-bit linear / non-linear
        sys.exit("only 8-bit XCFs are supported (precision=%d)" % precision)
    infos = [layer_info(b, version, o) for o in layer_offsets]
    match = [i for i in infos if i["name"] == want]
    if not match:
        sys.exit("no layer named %r - have: %s" % (want, ", ".join(i["name"] for i in infos)))
    L = match[0]

    rr = Reader(b); rr.version = version; rr.p = L["hierarchy"]
    hw, hh, bpp = rr.u32(), rr.u32(), rr.u32()
    level_off = rr.ptr()                               # level 0 is full resolution
    if bpp not in (2, 4):
        sys.exit("layer has no alpha channel (bpp=%d)" % bpp)

    rr.p = level_off
    lw, lh = rr.u32(), rr.u32()
    tiles = []
    while True:
        t = rr.ptr()
        if t == 0:
            break
        tiles.append(t)

    out = np.zeros((lh, lw), dtype=np.uint8)
    ntx = (lw + TILE - 1) // TILE
    for i, toff in enumerate(tiles):
        ty, tx = divmod(i, ntx)
        x0, y0 = tx * TILE, ty * TILE
        tw, th = min(TILE, lw - x0), min(TILE, lh - y0)
        n = tw * th
        if compression == 1:
            p = toff
            planes = []
            for _ in range(bpp):
                pl, p = rle_plane(b, p, n)
                planes.append(pl)
            a = planes[bpp - 1]
        elif compression == 2:
            end = tiles[i + 1] if i + 1 < len(tiles) else len(b)
            raw = zlib.decompress(b[toff:end])
            a = raw[(bpp - 1) * n: bpp * n]
        elif compression == 0:
            raw = b[toff: toff + n * bpp]
            a = raw[(bpp - 1) * n: bpp * n]
        else:
            sys.exit("unknown compression %d" % compression)
        out[y0:y0 + th, x0:x0 + tw] = np.frombuffer(a, dtype=np.uint8).reshape(th, tw)

    canvas = np.zeros((H, W), dtype=np.uint8)
    ox, oy = L["ox"], L["oy"]
    sx0, sy0 = max(0, -ox), max(0, -oy)
    dx0, dy0 = max(0, ox), max(0, oy)
    cw = min(lw - sx0, W - dx0)
    ch = min(lh - sy0, H - dy0)
    if cw > 0 and ch > 0:
        canvas[dy0:dy0 + ch, dx0:dx0 + cw] = out[sy0:sy0 + ch, sx0:sx0 + cw]
    return canvas, L, (W, H)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        b, r, version, W, H, precision, compression, offs = load(sys.argv[1])
        print("XCF v%d  %dx%d  precision=%d  compression=%s  layers=%d"
              % (version, W, H, precision,
                 {0: "none", 1: "RLE", 2: "zlib"}.get(compression, compression), len(offs)))
        for o in offs:
            i = layer_info(b, version, o)
            print("   %-40s %5dx%-5d at (%d,%d)  visible=%d opacity=%d"
                  % (i["name"], i["w"], i["h"], i["ox"], i["oy"], i["visible"], i["opacity"]))
    elif len(sys.argv) == 4:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        mask, L, (W, H) = alpha_mask(sys.argv[1], sys.argv[2])
        rgba = np.zeros((H, W, 4), dtype=np.uint8)
        rgba[:, :, 0] = 220
        rgba[:, :, 1] = 40
        rgba[:, :, 2] = 40
        rgba[:, :, 3] = mask
        Image.fromarray(rgba).save(sys.argv[3])
        print("layer %r -> %s   painted pixels (alpha>=128): %d"
              % (L["name"], sys.argv[3], int((mask >= 128).sum())))
    else:
        sys.exit(__doc__)
