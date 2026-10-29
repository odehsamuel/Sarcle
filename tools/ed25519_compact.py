"""Compact self-contained RFC 8032 Ed25519 implementation.

Zero external dependencies - standard library only (hashlib).
Used for deterministic generation and cross-validation of test vectors.
"""

import hashlib

q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493


def inv(x):
    return pow(x, q - 2, q)


d = -121665 * inv(121666) % q
I = pow(2, (q - 1) // 4, q)


def xrecover(y):
    xx = (y * y - 1) * inv(d * y * y + 1) % q
    x = pow(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x


By = 4 * inv(5) % q
Bx = xrecover(By)
B = (Bx, By)


def edwards_add(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * inv(1 + d * x1 * x2 * y1 * y2) % q
    y3 = (y1 * y2 + x1 * x2) * inv(1 - d * x1 * x2 * y1 * y2) % q
    return (x3, y3)


def scalarmult(P, e):
    if e == 0:
        return (0, 1)
    Q = scalarmult(P, e // 2)
    Q = edwards_add(Q, Q)
    if e & 1:
        Q = edwards_add(Q, P)
    return Q


def encodeint(y):
    return y.to_bytes(32, "little")


def encodepoint(P):
    x, y = P
    bits = [(y >> i) & 1 for i in range(255)] + [x & 1]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(32))


def decodeint(b):
    return int.from_bytes(b, "little")


def decodepoint(b):
    y = sum(2**i * ((b[i // 8] >> (i % 8)) & 1) for i in range(255))
    x = xrecover(y)
    if x & 1 != ((b[31] >> 7) & 1):
        x = q - x
    P = (x, y)
    return P


def H(m):
    return hashlib.sha512(m).digest()


def clamp_scalar(h):
    a = bytearray(h[:32])
    a[0] &= 248
    a[31] &= 127
    a[31] |= 64
    return decodeint(bytes(a))


def publickey(sk):
    h = H(sk)
    a = clamp_scalar(h)
    A = scalarmult(B, a)
    return encodepoint(A)


def signature(m, sk, pk=None):
    if pk is None:
        pk = publickey(sk)
    h = H(sk)
    a = clamp_scalar(h)
    prefix = h[32:64]
    r = decodeint(H(prefix + m)) % l
    R = scalarmult(B, r)
    R_bytes = encodepoint(R)
    k = decodeint(H(R_bytes + pk + m)) % l
    S = (r + k * a) % l
    return R_bytes + encodeint(S)


def checkvalid(s, m, pk):
    if len(s) != 64 or len(pk) != 32:
        return False
    R_bytes = s[:32]
    S_bytes = s[32:]
    S = decodeint(S_bytes)
    if S >= l:
        return False
    try:
        R = decodepoint(R_bytes)
        A = decodepoint(pk)
    except Exception:
        return False
    k = decodeint(H(R_bytes + pk + m)) % l
    SB = scalarmult(B, S)
    kA = scalarmult(A, k)
    return SB == edwards_add(R, kA)


if __name__ == "__main__":
    # Test vector 1 from RFC 8032 (sk = 0x9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60)
    sk = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
    )
    pk = publickey(sk)
    expected_pk = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    assert pk.hex() == expected_pk, f"PK mismatch: {pk.hex()} vs {expected_pk}"

    msg = b""
    sig = signature(msg, sk, pk)
    expected_sig = "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    assert sig.hex() == expected_sig, f"Sig mismatch: {sig.hex()} vs {expected_sig}"
    assert checkvalid(sig, msg, pk) is True
    print("RFC 8032 test vector verified successfully!")
