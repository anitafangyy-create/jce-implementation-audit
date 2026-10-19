# BIP-0360 reference vectors (vendored)

`p2mr_construction.json` is an unmodified copy of the P2MR construction test
vectors published with BIP-0360.

- Source: https://github.com/bitcoin/bips/blob/master/bip-0360/ref-impl/common/tests/data/p2mr_construction.json
- BIP text: https://github.com/bitcoin/bips/blob/master/bip-0360.mediawiki
- Last commit touching the vector file: `3e3e4347e277` (2026-06-29)
- Retrieved: 2026-10-19
- SHA-256: `cd02da0b3c5bcbea98ed4d3141ebaf71344ee5acc8eb543841b7d2ed853251c7`
- Size: 15,971 bytes; 9 vectors (7 positive, 2 negative)

Scope: these vectors cover the **P2MR envelope** — script tree to Merkle root,
`scriptPubKey = OP_2 OP_PUSHBYTES_32 <root>`, Bech32m (BIP-350) addresses with
witness version 2, and control blocks of `1 + 32m` bytes. They do not contain
post-quantum signature vectors and say nothing about the signature scheme that
a future leaf script might verify.

`tests/test_bip360_vectors.py` checks the vectors and the envelope rules used
by this repository. The trees in this repository commit leaves with `UMT-LEAF`
rather than BIP-341 `TapLeaf`, so their roots are not expected to equal any
vector root.
