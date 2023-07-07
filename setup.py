from utils import *
import py_ecc.bn128 as b
from curve import ec_lincomb, G1Point, G2Point
from compiler.program import CommonPreprocessedInput
from verifier import VerificationKey
from dataclasses import dataclass
from poly import Polynomial, Basis

@dataclass
class Setup(object):
    #   ([1]₁, [x]₁, ..., [x^{d-1}]₁)
    # = ( G,    xG,  ...,  x^{d-1}G ), where G is a generator of G_1
    powers_of_x: list[G1Point]
    # [x]₂ = xH, where H is a generator of G_2
    X2: G2Point

    @classmethod
    def generate_srs(cls):
        print("Start to generate structured reference string")
        powers = 4096
        tau = 21831381940315734285607113342023901060522397560371972897001948545212302161822

        powers_of_x = [0] * powers
        powers_of_x[0] = b.G1

        for i in range(powers):
            if i > 0:
                powers_of_x[i] = b.multiply(powers_of_x[i - 1], tau)

        assert b.is_on_curve(powers_of_x[1], b.b)
        print("Generated G1 side, X^1 point: {}".format(powers_of_x[1]))

        X2 = b.multiply(b.G2, tau)
        assert b.is_on_curve(X2, b.b2)
        print("Generated G2 side, X^1 point: {}".format(X2))

        assert b.pairing(b.G2, powers_of_x[1]) == b.pairing(X2, b.G1)
        print("X^1 points checked consistent")

        return cls(powers_of_x, X2)

    # Encodes the KZG commitment that evaluates to the given values in the group
    def commit(self, values: Polynomial) -> G1Point:
        if (values.basis == Basis.LAGRANGE):
            # inverse FFT from Lagrange basis to monomial basis
            coeffs = values.ifft().values
        elif (values.basis == Basis.MONOMIAL):
            coeffs = values.values
        if len(coeffs) > len(self.powers_of_x):
            raise Exception("Not enough powers in setup")
        return ec_lincomb([(s, x) for s, x in zip(self.powers_of_x, coeffs)])

    # Generate the verification key for this program with the given setup
    def verification_key(self, pk: CommonPreprocessedInput) -> VerificationKey:
        return VerificationKey(
            pk.group_order,
            self.commit(pk.QM),
            self.commit(pk.QL),
            self.commit(pk.QR),
            self.commit(pk.QO),
            self.commit(pk.QC),
            self.commit(pk.S1),
            self.commit(pk.S2),
            self.commit(pk.S3),
            self.X2,
            Scalar.root_of_unity(pk.group_order),
        )