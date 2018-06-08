"Module for generating, checking, and interpreting BIP39 mnemonics"

import hashlib
import os
from util import convertbits

class WordList(tuple):
    """
    A tuple word list with a compact repr. Useable as a full language word-list
    tuple but doesn't spam the screen when printed in documentation. This must
    be loaded from a text file.
    """

    def __new__(cls, fn):
        """
        Create a WordList from a text file. This is a tuple of each word in the
        file
        """
        fullpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), fn)
        with open(fullpath, "r") as fd:
            tpl = fd.read().split()
        self = super().__new__(cls, tpl)
        self.filename = fn
        return self

    def __repr__(self):
        return '<%s word list>' % self.filename

WORDLIST_ENGLISH = WordList('english.txt')

class Mnemonic(tuple):
    """
    A BIP39 Mnemonic: a tuple of 3N spoken-language words for carrying seed
    entropy for generating deterministic wallets. The word sequence itself
    encodes a checksum for error detection. to_seed() provides the main
    mechanism to extract entropy bytes, optionally encrypted with password,
    from a Mnemonic.

    Mnemonics can be created directly from any tuple of strings, single strings
    of whitespace delimited words, or generated randomly using system entropy
    sources.
    """

    __slots__ = ()

    def __new__(cls, *args):
        """
        Create A new Mnemonic. If no args are given, randomly generate Mnemonic
        from system entropy.
        """
        if not args:
            entropy = os.urandom(20)
            return cls.from_entropy(entropy)
        else:
            if isinstance(args[0], int):
                entropy = os.urandom(args[0])
                return cls.from_entropy(entropy)
            return super().__new__(cls, *args)

    def __str__(self):
        return ' '.join(self)

    def to_seed(self, password=b''):
        'Return entropy bytes, optionally encrypted with a bytes password'
        mnemonic_bytes = str(self).encode()
        return hashlib.pbkdf2_hmac(hash_name='sha512',
                                   password=mnemonic_bytes,
                                   salt=b'mnemonic' + password,
                                   iterations=2048)

    def _bin_string(self, wl=WORDLIST_ENGLISH):
        'return str of binary representation'
        return ''.join(bin(wl.index(x))[2:].zfill(11) for x in self)

    @classmethod
    def from_string(cls, string):
        'Create Mnemonic from space delimited string'
        return cls(string.split(' '))

    @classmethod
    def from_entropy(cls, ent, wl=WORDLIST_ENGLISH):
        """
        Create a Mnemonic from entropy bytes using given wordlist (default
        English)
        """

        ENT = len(ent) * 8
        assert len(ent) % 4 == 0 and len(ent) >= 16 and len(ent) <= 32,\
            'entropy length must be integer multiple of 32 between 128-256'

        hash_ = hashlib.sha256(ent).digest()
        chk = convertbits(hash_, 8, 1)[:ENT // 32]
        entbits = convertbits(ent, 8, 1)
        full = entbits + chk
        l = convertbits(full, 1, 11)
        return cls(wl[x] for x in l)

    def check(self, wl=WORDLIST_ENGLISH):
        """
        Check if a Mnemonic instance is valid. Returns true iff the Mnemonic
        instance passes checksum verification.
        """
        if len(self) % 3 > 0:
            return False
        l = [wl.index(x) for x in self]
        fullbits = convertbits(l, 11, 1)
        ENT = 32 * len(fullbits) // 33
        plbits, csbits = fullbits[:ENT], fullbits[ENT:]
        plbytes = bytes(convertbits(plbits, 1, 8))
        hash_ = hashlib.sha256(plbytes).digest()
        return convertbits(hash_, 8, 1)[:len(csbits)] == csbits
