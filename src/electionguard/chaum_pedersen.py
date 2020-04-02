from typing import NamedTuple

from .elgamal import ElGamalCiphertext
from .group import (
    ElementModQ,
    ElementModP,
    g_pow_p,
    mult_p,
    pow_p,
    valid_residue,
    in_bounds_q,
    a_minus_b_q,
    a_plus_bc_q,
    add_q,
    negate_q,
    int_to_q,
    ZERO_MOD_Q,
)
from .hash import hash_elems
from .logs import log_warning
from .nonces import Nonces


class DisjunctiveChaumPedersenProof(NamedTuple):
    a0: ElementModP
    b0: ElementModP
    a1: ElementModP
    b1: ElementModP
    c0: ElementModQ
    c1: ElementModQ
    v0: ElementModQ
    v1: ElementModQ


class ConstantChaumPedersenProof(NamedTuple):
    a: ElementModP
    b: ElementModP
    c: ElementModQ
    v: ElementModQ
    constant: int


def make_disjunctive_chaum_pedersen(
    message: ElGamalCiphertext,
    r: ElementModQ,
    k: ElementModP,
    seed: ElementModQ,
    plaintext: int,
) -> DisjunctiveChaumPedersenProof:
    """
    Produce a "disjunctive" proof that an encryption of a given plaintext is either an encrypted zero or one.
    This is just a front-end helper for `make_disjunctive_chaum_pedersen_zero` and
    `make_disjunctive_chaum_pedersen_one`.

    :param message: An ElGamal ciphertext
    :param r: The nonce used creating the ElGamal ciphertext
    :param k: The ElGamal public key for the election
    :param seed: Used to generate other random values here
    :param plaintext: Zero or one
    """

    assert (
        0 <= plaintext <= 1
    ), "make_disjunctive_chaum_pedersen only supports plaintexts of 0 or 1"
    if plaintext == 0:
        return make_disjunctive_chaum_pedersen_zero(message, r, k, seed)
    else:
        return make_disjunctive_chaum_pedersen_one(message, r, k, seed)


def make_disjunctive_chaum_pedersen_zero(
    message: ElGamalCiphertext, r: ElementModQ, k: ElementModP, seed: ElementModQ
) -> DisjunctiveChaumPedersenProof:
    """
    Produces a "disjunctive" proof that an encryption of zero is either an encrypted zero or one.

    :param message: An ElGamal ciphertext
    :param r: The nonce used creating the ElGamal ciphertext
    :param k: The ElGamal public key for the election
    :param seed: Used to generate other random values here
    """
    (alpha, beta) = message

    # We need to pick three random numbers in Q.
    c1, v1, u0 = Nonces(seed, "disjoint-chaum-pedersen-proof")[0:3]

    # And now, the NIZK computation
    a0 = g_pow_p(u0)
    b0 = pow_p(k, u0)
    q_minus_c1 = negate_q(c1)
    a1 = mult_p(g_pow_p(v1), pow_p(alpha, q_minus_c1))
    b1 = mult_p(pow_p(k, v1), g_pow_p(c1), pow_p(beta, q_minus_c1))
    c = hash_elems(alpha, beta, a0, b0, a1, b1)
    c0 = a_minus_b_q(c, c1)
    v0 = a_plus_bc_q(u0, c0, r)

    return DisjunctiveChaumPedersenProof(a0, b0, a1, b1, c0, c1, v0, v1)


def make_disjunctive_chaum_pedersen_one(
    message: ElGamalCiphertext, r: ElementModQ, k: ElementModP, seed: ElementModQ
) -> DisjunctiveChaumPedersenProof:
    """
    Produces a "disjunctive" proof that an encryption of one is either an encrypted zero or one.

    :param message: An ElGamal ciphertext
    :param r: The nonce used creating the ElGamal ciphertext
    :param k: The ElGamal public key for the election
    :param seed: Used to generate other random values here
    """
    (alpha, beta) = message

    # We need to pick three random numbers in Q.
    c0, v0, u1 = Nonces(seed, "disjoint-chaum-pedersen-proof")[0:3]

    # And now, the NIZK computation
    q_minus_c0 = negate_q(c0)
    a0 = mult_p(g_pow_p(v0), pow_p(alpha, q_minus_c0))
    b0 = mult_p(pow_p(k, v0), pow_p(beta, q_minus_c0))
    a1 = g_pow_p(u1)
    b1 = pow_p(k, u1)
    c = hash_elems(alpha, beta, a0, b0, a1, b1)
    c1 = a_minus_b_q(c, c0)
    v1 = a_plus_bc_q(u1, c1, r)

    return DisjunctiveChaumPedersenProof(a0, b0, a1, b1, c0, c1, v0, v1)


def make_constant_chaum_pedersen(
    message: ElGamalCiphertext,
    constant: int,
    r: ElementModQ,
    k: ElementModP,
    seed: ElementModQ,
) -> ConstantChaumPedersenProof:
    """
    Produces a proof that a given encryption corresponds to a specific total value.

    :param message: An ElGamal ciphertext
    :param constant: The plaintext constant value used to make the ElGamal ciphertext
    :param r: The aggregate nonce used creating the ElGamal ciphertext
    :param k: The ElGamal public key for the election
    :param seed: Used to generate other random values here
    """
    (alpha, beta) = message

    # We need to pick three random numbers in Q.
    u = Nonces(seed, "constant-chaum-pedersen-proof")[0]
    a = g_pow_p(u)
    b = pow_p(k, u)
    c = hash_elems(alpha, beta, a, b)
    v = a_plus_bc_q(u, c, r)

    return ConstantChaumPedersenProof(a, b, c, v, constant)


def is_valid_disjunctive_chaum_pedersen(
    message: ElGamalCiphertext, proof: DisjunctiveChaumPedersenProof, k: ElementModP
) -> bool:
    """
    Validates a "disjunctive" Chaum-Pedersen (zero or one) proof.

    :param message: The ciphertext message
    :param proof: The proof object
    :param k: The public key of the election
    :return: True if everything is consistent. False otherwise.
    """

    (alpha, beta) = message
    (a0, b0, a1, b1, c0, c1, v0, v1) = proof
    in_bounds_alpha = valid_residue(alpha)
    in_bounds_beta = valid_residue(beta)
    in_bounds_a0 = valid_residue(a0)
    in_bounds_b0 = valid_residue(b0)
    in_bounds_a1 = valid_residue(a1)
    in_bounds_b1 = valid_residue(b1)
    in_bounds_c0 = in_bounds_q(c0)
    in_bounds_c1 = in_bounds_q(c1)
    in_bounds_v0 = in_bounds_q(v0)
    in_bounds_v1 = in_bounds_q(v1)
    c = hash_elems(alpha, beta, a0, b0, a1, b1)
    consistent_c = c == add_q(c0, c1)
    consistent_gv0 = g_pow_p(v0) == mult_p(a0, pow_p(alpha, c0))
    consistent_gv1 = g_pow_p(v1) == mult_p(a1, pow_p(alpha, c1))
    consistent_kv0 = pow_p(k, v0) == mult_p(b0, pow_p(beta, c0))
    consistent_gc1kv1 = mult_p(g_pow_p(c1), pow_p(k, v1)) == mult_p(b1, pow_p(beta, c1))

    success = (
        in_bounds_alpha
        and in_bounds_beta
        and in_bounds_a0
        and in_bounds_b0
        and in_bounds_a1
        and in_bounds_b1
        and in_bounds_c0
        and in_bounds_c1
        and in_bounds_v0
        and in_bounds_v1
        and consistent_c
        and consistent_gv0
        and consistent_gv1
        and consistent_kv0
        and consistent_gc1kv1
    )

    if not success:
        log_warning(
            "found an invalid Chaum-Pedersen proof: "
            + str(
                {
                    "in_bounds_alpha": in_bounds_alpha,
                    "in_bounds_beta": in_bounds_beta,
                    "in_bounds_a0": in_bounds_a0,
                    "in_bounds_b0": in_bounds_b0,
                    "in_bounds_a1": in_bounds_a1,
                    "in_bounds_b1": in_bounds_b1,
                    "in_bounds_c0": in_bounds_c0,
                    "in_bounds_c1": in_bounds_c1,
                    "in_bounds_v0": in_bounds_v0,
                    "in_bounds_v1": in_bounds_v1,
                    "consistent_c": consistent_c,
                    "consistent_gv0": consistent_gv0,
                    "consistent_gv1": consistent_gv1,
                    "consistent_kv0": consistent_kv0,
                    "consistent_gc1kv1": consistent_gc1kv1,
                    "k": k,
                    "proof": proof,
                }
            ),
        )
    return success


def is_valid_constant_chaum_pedersen(
    message: ElGamalCiphertext, proof: ConstantChaumPedersenProof, k: ElementModP
) -> bool:
    """
    Validates a "constant" Chaum-Pedersen proof.

    :param message: The ciphertext message
    :param proof: The proof object
    :param k: The public key of the election
    :return: True if everything is consistent. False otherwise.
    """

    (alpha, beta) = message
    (a, b, c, v, constant) = proof
    in_bounds_alpha = valid_residue(alpha)
    in_bounds_beta = valid_residue(beta)
    in_bounds_a = valid_residue(a)
    in_bounds_b = valid_residue(b)
    in_bounds_c = in_bounds_q(c)
    in_bounds_v = in_bounds_q(v)
    tmp = int_to_q(constant)
    if tmp is None:
        constant_q = ZERO_MOD_Q
        in_bounds_constant = False
    else:
        constant_q = tmp
        in_bounds_constant = True
    sane_constant = 0 <= constant < 1_000_000_000
    c = hash_elems(alpha, beta, a, b)
    consistent_gv = (
        in_bounds_v
        and in_bounds_a
        and in_bounds_alpha
        and in_bounds_c
        and g_pow_p(v) == mult_p(a, pow_p(alpha, c))
    )
    consistent_kv = in_bounds_constant and mult_p(
        g_pow_p(mult_p(c, constant_q)), pow_p(k, v)
    ) == mult_p(b, pow_p(beta, c))

    success = (
        in_bounds_alpha
        and in_bounds_beta
        and in_bounds_a
        and in_bounds_b
        and in_bounds_c
        and in_bounds_v
        and in_bounds_constant
        and sane_constant
        and consistent_gv
        and consistent_kv
    )

    if not success:
        log_warning(
            "found an invalid Chaum-Pedersen proof: "
            + str(
                {
                    "in_bounds_alpha": in_bounds_alpha,
                    "in_bounds_beta": in_bounds_beta,
                    "in_bounds_a": in_bounds_a,
                    "in_bounds_b": in_bounds_b,
                    "in_bounds_c": in_bounds_c,
                    "in_bounds_v": in_bounds_v,
                    "in_bounds_constant": in_bounds_constant,
                    "sane_constant": sane_constant,
                    "consistent_gv": consistent_gv,
                    "consistent_kv": consistent_kv,
                    "k": k,
                    "proof": proof,
                }
            ),
        )
    return success
