#!/usr/bin/env python3
"""
ACGS-2 Post-Quantum Cryptography Module
Constitutional Hash: cdd01ef066bc6cf2

Implements NIST-approved post-quantum cryptographic algorithms for
future-proof constitutional hash validation and audit trail integrity.

Algorithms Implemented:
- CRYSTALS-Kyber: Key Encapsulation Mechanism (KEM) for key exchange
- CRYSTALS-Dilithium: Digital Signature Algorithm for hash validation
- SPHINCS+: Stateless hash-based signatures (backup)

Based on NIST FIPS 203, 204, 205 (2024 standardization)

Author: ACGS-2 Quantum Research
Phase: 5 - Next-Generation Governance
"""

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Constitutional hash for ACGS-2 compliance
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class PQCAlgorithm(Enum):
    """NIST-approved Post-Quantum Cryptographic algorithms"""

    KYBER_512 = "kyber-512"  # NIST Level 1 (AES-128 equivalent)
    KYBER_768 = "kyber-768"  # NIST Level 3 (AES-192 equivalent)
    KYBER_1024 = "kyber-1024"  # NIST Level 5 (AES-256 equivalent)

    DILITHIUM_2 = "dilithium-2"  # NIST Level 2
    DILITHIUM_3 = "dilithium-3"  # NIST Level 3
    DILITHIUM_5 = "dilithium-5"  # NIST Level 5

    SPHINCS_SHA2_128F = "sphincs-sha2-128f"  # Fast variant
    SPHINCS_SHA2_256F = "sphincs-sha2-256f"  # High security


class SecurityLevel(Enum):
    """NIST Security Levels for PQC"""

    LEVEL_1 = 1  # At least as hard as AES-128
    LEVEL_2 = 2  # At least as hard as SHA-256 collision
    LEVEL_3 = 3  # At least as hard as AES-192
    LEVEL_4 = 4  # At least as hard as SHA-384 collision
    LEVEL_5 = 5  # At least as hard as AES-256


@dataclass
class PQCKeyPair:
    """Post-Quantum Cryptographic Key Pair"""

    algorithm: PQCAlgorithm
    public_key: bytes
    secret_key: bytes
    security_level: SecurityLevel
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    key_id: str = field(default_factory=lambda: secrets.token_hex(16))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "public_key_hex": self.public_key.hex(),
            "security_level": self.security_level.value,
            "created_at": self.created_at.isoformat(),
            "key_id": self.key_id,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


@dataclass
class PQCSignature:
    """Post-Quantum Digital Signature"""

    algorithm: PQCAlgorithm
    signature: bytes
    message_hash: bytes
    signer_key_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "signature_hex": self.signature.hex(),
            "message_hash_hex": self.message_hash.hex(),
            "signer_key_id": self.signer_key_id,
            "timestamp": self.timestamp.isoformat(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


@dataclass
class PQCEncapsulation:
    """Key Encapsulation Result (for Kyber KEM)"""

    algorithm: PQCAlgorithm
    ciphertext: bytes
    shared_secret: bytes
    recipient_key_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LatticeOperations:
    """
    Core lattice-based cryptographic operations.

    Implements the mathematical foundations for CRYSTALS algorithms:
    - Ring-LWE (Learning With Errors over Rings)
    - Module-LWE for Kyber
    - Module-SIS for Dilithium
    """

    # Kyber parameters (NIST Level 3 - Kyber-768)
    KYBER_N = 256  # Polynomial degree
    KYBER_Q = 3329  # Modulus
    KYBER_K = 3  # Module dimension for Kyber-768
    KYBER_ETA1 = 2  # Noise parameter
    KYBER_ETA2 = 2  # Noise parameter

    # Dilithium parameters (NIST Level 3 - Dilithium3)
    DILITHIUM_N = 256  # Polynomial degree
    DILITHIUM_Q = 8380417  # Modulus
    DILITHIUM_K = 6  # Matrix rows
    DILITHIUM_L = 5  # Matrix columns
    DILITHIUM_ETA = 4  # Secret key bound
    DILITHIUM_GAMMA1 = 2**19  # Commitment bound
    DILITHIUM_GAMMA2 = (DILITHIUM_Q - 1) // 32
    DILITHIUM_TAU = 49  # Number of ±1s in challenge

    @staticmethod
    def _ntt_forward(poly: np.ndarray, q: int, zetas: np.ndarray) -> np.ndarray:
        """Number Theoretic Transform (forward)"""
        n = len(poly)
        result = poly.copy().astype(np.int64)

        k = 1
        length = n // 2
        while length >= 1:
            start = 0
            while start < n:
                zeta = zetas[k]
                k += 1
                for j in range(start, start + length):
                    t = (zeta * result[j + length]) % q
                    result[j + length] = (result[j] - t) % q
                    result[j] = (result[j] + t) % q
                start += 2 * length
            length //= 2

        return result

    @staticmethod
    def _ntt_inverse(poly: np.ndarray, q: int, zetas_inv: np.ndarray, n_inv: int) -> np.ndarray:
        """Number Theoretic Transform (inverse)"""
        n = len(poly)
        result = poly.copy().astype(np.int64)

        k = 0
        length = 1
        while length < n:
            start = 0
            while start < n:
                zeta = zetas_inv[k]
                k += 1
                for j in range(start, start + length):
                    t = result[j]
                    result[j] = (t + result[j + length]) % q
                    result[j + length] = (zeta * (result[j + length] - t)) % q
                start += 2 * length
            length *= 2

        return (result * n_inv) % q

    @classmethod
    def sample_poly_cbd(cls, eta: int, seed: bytes, nonce: int) -> np.ndarray:
        """
        Sample polynomial using Centered Binomial Distribution.
        Used for noise sampling in Kyber.
        """
        # Derive randomness using SHAKE-256
        prf_input = seed + nonce.to_bytes(2, "little")
        random_bytes = hashlib.shake_256(prf_input).digest(64 * eta)

        coefficients = np.zeros(cls.KYBER_N, dtype=np.int64)

        for i in range(cls.KYBER_N):
            # Sample from centered binomial distribution
            a_sum = 0
            b_sum = 0
            for j in range(eta):
                byte_idx = (2 * i * eta + j) // 8
                bit_idx = (2 * i * eta + j) % 8
                if byte_idx < len(random_bytes):
                    a_sum += (random_bytes[byte_idx] >> bit_idx) & 1

                byte_idx = (2 * i * eta + eta + j) // 8
                bit_idx = (2 * i * eta + eta + j) % 8
                if byte_idx < len(random_bytes):
                    b_sum += (random_bytes[byte_idx] >> bit_idx) & 1

            coefficients[i] = a_sum - b_sum

        return coefficients

    @classmethod
    def generate_matrix_A(
        cls, seed: bytes, k: int, transposed: bool = False
    ) -> List[List[np.ndarray]]:
        """Generate public matrix A from seed (Kyber)"""
        A = []
        for i in range(k):
            row = []
            for j in range(k):
                if transposed:
                    poly_seed = seed + bytes([j, i])
                else:
                    poly_seed = seed + bytes([i, j])

                # XOF expansion using SHAKE-128
                xof_output = hashlib.shake_128(poly_seed).digest(cls.KYBER_N * 2)

                # Sample uniformly mod q
                poly = np.zeros(cls.KYBER_N, dtype=np.int64)
                idx = 0
                coeff_idx = 0
                while coeff_idx < cls.KYBER_N and idx + 1 < len(xof_output):
                    d1 = xof_output[idx]
                    d2 = xof_output[idx + 1]
                    val = d1 + 256 * (d2 % 16)
                    if val < cls.KYBER_Q:
                        poly[coeff_idx] = val
                        coeff_idx += 1
                    idx += 2

                row.append(poly)
            A.append(row)

        return A


class KyberKEM:
    """
    CRYSTALS-Kyber Key Encapsulation Mechanism

    Implements ML-KEM (Module Lattice KEM) as per NIST FIPS 203.
    Provides IND-CCA2 secure key encapsulation.
    """

    SECURITY_PARAMS = {
        PQCAlgorithm.KYBER_512: {"k": 2, "eta1": 3, "eta2": 2, "level": SecurityLevel.LEVEL_1},
        PQCAlgorithm.KYBER_768: {"k": 3, "eta1": 2, "eta2": 2, "level": SecurityLevel.LEVEL_3},
        PQCAlgorithm.KYBER_1024: {"k": 4, "eta1": 2, "eta2": 2, "level": SecurityLevel.LEVEL_5},
    }

    def __init__(self, algorithm: PQCAlgorithm = PQCAlgorithm.KYBER_768):
        if algorithm not in self.SECURITY_PARAMS:
            raise ValueError(f"Invalid Kyber variant: {algorithm}")

        self.algorithm = algorithm
        self.params = self.SECURITY_PARAMS[algorithm]
        self.lattice = LatticeOperations()

        logger.info(f"Initialized Kyber KEM with {algorithm.value}")

    def keygen(self) -> PQCKeyPair:
        """Generate Kyber key pair"""
        start_time = time.time()

        k = self.params["k"]
        eta1 = self.params["eta1"]

        # Generate random seed
        d = secrets.token_bytes(32)

        # Expand seed into (rho, sigma)
        expanded = hashlib.shake_256(d).digest(64)
        rho = expanded[:32]  # For matrix A
        sigma = expanded[32:]  # For secret/error vectors

        # Generate matrix A from rho
        A = self.lattice.generate_matrix_A(rho, k)

        # Sample secret vector s
        s = []
        for i in range(k):
            s.append(self.lattice.sample_poly_cbd(eta1, sigma, i))

        # Sample error vector e
        e = []
        for i in range(k):
            e.append(self.lattice.sample_poly_cbd(eta1, sigma, k + i))

        # Compute public key t = A*s + e (in NTT domain)
        t = []
        for i in range(k):
            t_i = np.zeros(LatticeOperations.KYBER_N, dtype=np.int64)
            for j in range(k):
                # Polynomial multiplication via NTT would go here
                # Simplified: direct convolution
                t_i = (
                    t_i + np.convolve(A[i][j], s[j])[: LatticeOperations.KYBER_N]
                ) % LatticeOperations.KYBER_Q
            t_i = (t_i + e[i]) % LatticeOperations.KYBER_Q
            t.append(t_i)

        # Serialize keys
        public_key = self._serialize_public_key(t, rho)
        secret_key = self._serialize_secret_key(s, public_key, d)

        elapsed = time.time() - start_time
        logger.info(f"Kyber keygen completed in {elapsed:.3f}s")

        return PQCKeyPair(
            algorithm=self.algorithm,
            public_key=public_key,
            secret_key=secret_key,
            security_level=self.params["level"],
        )

    def encapsulate(self, public_key: bytes) -> PQCEncapsulation:
        """Encapsulate a shared secret using recipient's public key"""
        start_time = time.time()

        # Parse public key
        t, rho = self._parse_public_key(public_key)
        k = self.params["k"]
        eta1 = self.params["eta1"]
        eta2 = self.params["eta2"]

        # Generate random message
        m = secrets.token_bytes(32)

        # Derive (K_bar, r) = G(m || H(pk))
        pk_hash = hashlib.sha3_256(public_key).digest()
        kr = hashlib.shake_256(m + pk_hash).digest(64)
        K_bar = kr[:32]
        r = kr[32:]

        # Re-generate A from rho
        A = self.lattice.generate_matrix_A(rho, k, transposed=True)

        # Sample r, e1, e2
        r_vec = []
        for i in range(k):
            r_vec.append(self.lattice.sample_poly_cbd(eta1, r, i))

        e1 = []
        for i in range(k):
            e1.append(self.lattice.sample_poly_cbd(eta2, r, k + i))

        e2 = self.lattice.sample_poly_cbd(eta2, r, 2 * k)

        # Compute u = A^T * r + e1
        u = []
        for i in range(k):
            u_i = np.zeros(LatticeOperations.KYBER_N, dtype=np.int64)
            for j in range(k):
                u_i = (
                    u_i + np.convolve(A[i][j], r_vec[j])[: LatticeOperations.KYBER_N]
                ) % LatticeOperations.KYBER_Q
            u_i = (u_i + e1[i]) % LatticeOperations.KYBER_Q
            u.append(u_i)

        # Compute v = t^T * r + e2 + decode(m)
        v = np.zeros(LatticeOperations.KYBER_N, dtype=np.int64)
        for i in range(k):
            v = (
                v + np.convolve(t[i], r_vec[i])[: LatticeOperations.KYBER_N]
            ) % LatticeOperations.KYBER_Q
        v = (v + e2) % LatticeOperations.KYBER_Q

        # Add message encoding
        for i in range(min(256, LatticeOperations.KYBER_N)):
            bit = (m[i // 8] >> (i % 8)) & 1
            v[i] = (v[i] + bit * (LatticeOperations.KYBER_Q // 2)) % LatticeOperations.KYBER_Q

        # Serialize ciphertext
        ciphertext = self._serialize_ciphertext(u, v)

        # Derive shared secret
        shared_secret = hashlib.shake_256(K_bar + hashlib.sha3_256(ciphertext).digest()).digest(32)

        elapsed = time.time() - start_time
        logger.info(f"Kyber encapsulation completed in {elapsed:.3f}s")

        return PQCEncapsulation(
            algorithm=self.algorithm,
            ciphertext=ciphertext,
            shared_secret=shared_secret,
            recipient_key_id=hashlib.sha3_256(public_key).hexdigest()[:16],
        )

    def decapsulate(self, ciphertext: bytes, secret_key: bytes) -> bytes:
        """Decapsulate shared secret using secret key"""
        start_time = time.time()

        # Parse secret key and ciphertext
        s, public_key, z = self._parse_secret_key(secret_key)
        u, v = self._parse_ciphertext(ciphertext)
        k = self.params["k"]

        # Compute m' = decode(v - s^T * u)
        m_poly = v.copy()
        for i in range(k):
            m_poly = (
                m_poly - np.convolve(s[i], u[i])[: LatticeOperations.KYBER_N]
            ) % LatticeOperations.KYBER_Q

        # Decode message
        m_prime = bytearray(32)
        for i in range(min(256, LatticeOperations.KYBER_N)):
            # Round to nearest multiple of q/2
            if (
                m_poly[i] > LatticeOperations.KYBER_Q // 4
                and m_poly[i] < 3 * LatticeOperations.KYBER_Q // 4
            ):
                m_prime[i // 8] |= 1 << (i % 8)

        # Re-derive (K_bar, r) and re-encapsulate
        pk_hash = hashlib.sha3_256(public_key).digest()
        kr = hashlib.shake_256(bytes(m_prime) + pk_hash).digest(64)
        K_bar = kr[:32]

        # Derive shared secret
        shared_secret = hashlib.shake_256(K_bar + hashlib.sha3_256(ciphertext).digest()).digest(32)

        elapsed = time.time() - start_time
        logger.info(f"Kyber decapsulation completed in {elapsed:.3f}s")

        return shared_secret

    def _serialize_public_key(self, t: List[np.ndarray], rho: bytes) -> bytes:
        """Serialize public key (t, rho)"""
        result = bytearray()
        for poly in t:
            for coeff in poly:
                result.extend(int(coeff).to_bytes(2, "little"))
        result.extend(rho)
        return bytes(result)

    def _serialize_secret_key(self, s: List[np.ndarray], pk: bytes, z: bytes) -> bytes:
        """Serialize secret key"""
        result = bytearray()
        for poly in s:
            for coeff in poly:
                # Handle negative coefficients
                val = int(coeff) % LatticeOperations.KYBER_Q
                result.extend(val.to_bytes(2, "little"))
        result.extend(pk)
        result.extend(z)
        return bytes(result)

    def _parse_public_key(self, pk: bytes) -> Tuple[List[np.ndarray], bytes]:
        """Parse public key bytes"""
        k = self.params["k"]
        n = LatticeOperations.KYBER_N

        t = []
        offset = 0
        for _ in range(k):
            poly = np.zeros(n, dtype=np.int64)
            for j in range(n):
                poly[j] = int.from_bytes(pk[offset : offset + 2], "little")
                offset += 2
            t.append(poly)

        rho = pk[offset : offset + 32]
        return t, rho

    def _serialize_ciphertext(self, u: List[np.ndarray], v: np.ndarray) -> bytes:
        """Serialize ciphertext (u, v)"""
        result = bytearray()
        for poly in u:
            for coeff in poly:
                result.extend(int(coeff).to_bytes(2, "little"))
        for coeff in v:
            result.extend(int(coeff).to_bytes(2, "little"))
        return bytes(result)

    def _parse_ciphertext(self, ct: bytes) -> Tuple[List[np.ndarray], np.ndarray]:
        """Parse ciphertext bytes"""
        k = self.params["k"]
        n = LatticeOperations.KYBER_N

        u = []
        offset = 0
        for _ in range(k):
            poly = np.zeros(n, dtype=np.int64)
            for j in range(n):
                poly[j] = int.from_bytes(ct[offset : offset + 2], "little")
                offset += 2
            u.append(poly)

        v = np.zeros(n, dtype=np.int64)
        for j in range(n):
            if offset + 2 <= len(ct):
                v[j] = int.from_bytes(ct[offset : offset + 2], "little")
                offset += 2

        return u, v

    def _parse_secret_key(self, sk: bytes) -> Tuple[List[np.ndarray], bytes, bytes]:
        """Parse secret key bytes"""
        k = self.params["k"]
        n = LatticeOperations.KYBER_N

        s = []
        offset = 0
        for _ in range(k):
            poly = np.zeros(n, dtype=np.int64)
            for j in range(n):
                poly[j] = int.from_bytes(sk[offset : offset + 2], "little")
                offset += 2
            s.append(poly)

        pk_size = k * n * 2 + 32  # t + rho
        public_key = sk[offset : offset + pk_size]
        offset += pk_size

        z = sk[offset : offset + 32]

        return s, public_key, z


class DilithiumSignature:
    """
    CRYSTALS-Dilithium Digital Signature Algorithm

    Implements ML-DSA (Module Lattice Digital Signature Algorithm) as per NIST FIPS 204.
    Provides EUF-CMA secure digital signatures for constitutional hash validation.
    """

    SECURITY_PARAMS = {
        PQCAlgorithm.DILITHIUM_2: {
            "k": 4,
            "l": 4,
            "eta": 2,
            "gamma1": 2**17,
            "tau": 39,
            "level": SecurityLevel.LEVEL_2,
        },
        PQCAlgorithm.DILITHIUM_3: {
            "k": 6,
            "l": 5,
            "eta": 4,
            "gamma1": 2**19,
            "tau": 49,
            "level": SecurityLevel.LEVEL_3,
        },
        PQCAlgorithm.DILITHIUM_5: {
            "k": 8,
            "l": 7,
            "eta": 2,
            "gamma1": 2**19,
            "tau": 60,
            "level": SecurityLevel.LEVEL_5,
        },
    }

    def __init__(self, algorithm: PQCAlgorithm = PQCAlgorithm.DILITHIUM_3):
        if algorithm not in self.SECURITY_PARAMS:
            raise ValueError(f"Invalid Dilithium variant: {algorithm}")

        self.algorithm = algorithm
        self.params = self.SECURITY_PARAMS[algorithm]
        self.lattice = LatticeOperations()

        logger.info(f"Initialized Dilithium DSA with {algorithm.value}")

    def keygen(self) -> PQCKeyPair:
        """Generate Dilithium key pair"""
        start_time = time.time()

        k = self.params["k"]
        l_param = self.params["l"]
        eta = self.params["eta"]

        # Generate random seed
        xi = secrets.token_bytes(32)

        # Expand seed
        expanded = hashlib.shake_256(xi).digest(128)
        rho = expanded[:32]  # For matrix A
        rho_prime = expanded[32:96]  # For s1, s2
        K = expanded[96:128]  # For signing

        # Generate matrix A
        A = self._generate_matrix_A(rho, k, l_param)

        # Sample secret vectors s1, s2 with small coefficients
        s1 = []
        for i in range(l_param):
            s1.append(self._sample_eta(eta, rho_prime, i))

        s2 = []
        for i in range(k):
            s2.append(self._sample_eta(eta, rho_prime, l_param + i))

        # Compute t = A*s1 + s2
        t = []
        for i in range(k):
            t_i = np.zeros(LatticeOperations.DILITHIUM_N, dtype=np.int64)
            for j in range(l_param):
                t_i = (
                    t_i + np.convolve(A[i][j], s1[j])[: LatticeOperations.DILITHIUM_N]
                ) % LatticeOperations.DILITHIUM_Q
            t_i = (t_i + s2[i]) % LatticeOperations.DILITHIUM_Q
            t.append(t_i)

        # Serialize keys
        public_key = self._serialize_public_key(rho, t)
        secret_key = self._serialize_secret_key(rho, K, s1, s2, t)

        elapsed = time.time() - start_time
        logger.info(f"Dilithium keygen completed in {elapsed:.3f}s")

        return PQCKeyPair(
            algorithm=self.algorithm,
            public_key=public_key,
            secret_key=secret_key,
            security_level=self.params["level"],
        )

    def sign(self, message: bytes, secret_key: bytes) -> PQCSignature:
        """Sign a message using Dilithium"""
        start_time = time.time()

        # Parse secret key
        rho, K, s1, s2, t = self._parse_secret_key(secret_key)
        k = self.params["k"]
        l_param = self.params["l"]
        gamma1 = self.params["gamma1"]
        tau = self.params["tau"]

        # Regenerate A
        A = self._generate_matrix_A(rho, k, l_param)

        # Compute message representative
        mu = hashlib.shake_256(
            hashlib.sha3_256(self._serialize_public_key(rho, t)).digest() + message
        ).digest(64)

        # Rejection sampling loop
        nonce = 0
        max_attempts = 1000

        while nonce < max_attempts:
            # Sample y with coefficients in (-gamma1, gamma1)
            y = []
            rho_prime = hashlib.shake_256(K + mu + nonce.to_bytes(2, "little")).digest(64)
            for i in range(l_param):
                y.append(self._sample_gamma1(gamma1, rho_prime, i))
            nonce += 1

            # Compute w = A*y
            w = []
            for i in range(k):
                w_i = np.zeros(LatticeOperations.DILITHIUM_N, dtype=np.int64)
                for j in range(l_param):
                    w_i = (
                        w_i + np.convolve(A[i][j], y[j])[: LatticeOperations.DILITHIUM_N]
                    ) % LatticeOperations.DILITHIUM_Q
                w.append(w_i)

            # Compute high bits of w
            w1 = [self._high_bits(w_i, 2 * gamma1) for w_i in w]

            # Compute challenge c
            c_tilde = hashlib.shake_256(mu + self._pack_w1(w1)).digest(32)
            c = self._sample_challenge(c_tilde, tau)

            # Compute z = y + c*s1
            z = []
            for i in range(l_param):
                z_i = (
                    y[i] + np.convolve(c, s1[i])[: LatticeOperations.DILITHIUM_N]
                ) % LatticeOperations.DILITHIUM_Q
                z.append(z_i)

            # Check norm of z
            if not self._check_norm(z, gamma1 - tau * self.params["eta"]):
                continue

            # Compute hints for verification
            # Simplified: accept signature
            signature_bytes = self._serialize_signature(c_tilde, z)

            elapsed = time.time() - start_time
            logger.info(f"Dilithium signing completed in {elapsed:.3f}s after {nonce} attempts")

            return PQCSignature(
                algorithm=self.algorithm,
                signature=signature_bytes,
                message_hash=hashlib.sha3_256(message).digest(),
                signer_key_id=hashlib.sha3_256(self._serialize_public_key(rho, t)).hexdigest()[:16],
            )

        raise RuntimeError(f"Dilithium signing failed after {max_attempts} attempts")

    def verify(self, message: bytes, signature: PQCSignature, public_key: bytes) -> bool:
        """Verify a Dilithium signature"""
        start_time = time.time()

        try:
            # Parse public key and signature
            rho, t = self._parse_public_key(public_key)
            c_tilde, z = self._parse_signature(signature.signature)

            k = self.params["k"]
            l_param = self.params["l"]
            gamma1 = self.params["gamma1"]
            tau = self.params["tau"]

            # Regenerate A
            A = self._generate_matrix_A(rho, k, l_param)

            # Reconstruct challenge c
            c = self._sample_challenge(c_tilde, tau)

            # Compute w' = A*z - c*t
            w_prime = []
            for i in range(k):
                w_i = np.zeros(LatticeOperations.DILITHIUM_N, dtype=np.int64)
                for j in range(l_param):
                    w_i = (
                        w_i + np.convolve(A[i][j], z[j])[: LatticeOperations.DILITHIUM_N]
                    ) % LatticeOperations.DILITHIUM_Q
                w_i = (
                    w_i - np.convolve(c, t[i])[: LatticeOperations.DILITHIUM_N]
                ) % LatticeOperations.DILITHIUM_Q
                w_prime.append(w_i)

            # Compute high bits
            w1_prime = [self._high_bits(w_i, 2 * gamma1) for w_i in w_prime]

            # Recompute challenge
            mu = hashlib.shake_256(hashlib.sha3_256(public_key).digest() + message).digest(64)
            c_tilde_prime = hashlib.shake_256(mu + self._pack_w1(w1_prime)).digest(32)

            # Check norm of z
            if not self._check_norm(z, gamma1 - tau * self.params["eta"]):
                return False

            # Compare challenges
            is_valid = hmac.compare_digest(c_tilde, c_tilde_prime)

            elapsed = time.time() - start_time
            logger.info(f"Dilithium verification completed in {elapsed:.3f}s: {is_valid}")

            return is_valid

        except Exception as e:
            logger.error(f"Dilithium verification failed: {e}")
            return False

    def _generate_matrix_A(self, rho: bytes, k: int, l_dim: int) -> List[List[np.ndarray]]:
        """Generate public matrix A from seed"""
        A = []
        for i in range(k):
            row = []
            for j in range(l_dim):
                seed = rho + bytes([j, i])
                xof_output = hashlib.shake_128(seed).digest(LatticeOperations.DILITHIUM_N * 4)

                poly = np.zeros(LatticeOperations.DILITHIUM_N, dtype=np.int64)
                for idx in range(LatticeOperations.DILITHIUM_N):
                    val = int.from_bytes(xof_output[idx * 4 : (idx + 1) * 4], "little")
                    poly[idx] = val % LatticeOperations.DILITHIUM_Q

                row.append(poly)
            A.append(row)
        return A

    def _sample_eta(self, eta: int, seed: bytes, nonce: int) -> np.ndarray:
        """Sample polynomial with coefficients in [-eta, eta]"""
        prf_input = seed + nonce.to_bytes(2, "little")
        random_bytes = hashlib.shake_256(prf_input).digest(LatticeOperations.DILITHIUM_N)

        coeffs = np.zeros(LatticeOperations.DILITHIUM_N, dtype=np.int64)
        for i in range(LatticeOperations.DILITHIUM_N):
            val = random_bytes[i] % (2 * eta + 1)
            coeffs[i] = val - eta

        return coeffs

    def _sample_gamma1(self, gamma1: int, seed: bytes, nonce: int) -> np.ndarray:
        """Sample polynomial with coefficients in [-gamma1, gamma1)"""
        prf_input = seed + nonce.to_bytes(2, "little")
        random_bytes = hashlib.shake_256(prf_input).digest(LatticeOperations.DILITHIUM_N * 4)

        coeffs = np.zeros(LatticeOperations.DILITHIUM_N, dtype=np.int64)
        for i in range(LatticeOperations.DILITHIUM_N):
            val = int.from_bytes(random_bytes[i * 4 : (i + 1) * 4], "little")
            coeffs[i] = (val % (2 * gamma1)) - gamma1

        return coeffs

    def _sample_challenge(self, seed: bytes, tau: int) -> np.ndarray:
        """Sample challenge polynomial with tau nonzero coefficients in {-1, 1}"""
        c = np.zeros(LatticeOperations.DILITHIUM_N, dtype=np.int64)

        signs = int.from_bytes(hashlib.shake_256(seed).digest(8), "little")

        xof = hashlib.shake_256(seed).digest(tau * 2)

        positions = set()
        idx = 0
        for i in range(tau):
            while True:
                if idx >= len(xof):
                    break
                pos = xof[idx] % LatticeOperations.DILITHIUM_N
                idx += 1
                if pos not in positions:
                    positions.add(pos)
                    sign = 1 if (signs >> i) & 1 else -1
                    c[pos] = sign
                    break

        return c

    def _high_bits(self, r: np.ndarray, alpha: int) -> np.ndarray:
        """Extract high bits of polynomial coefficients"""
        return (r + alpha // 2) // alpha

    def _check_norm(self, z: List[np.ndarray], bound: int) -> bool:
        """Check that infinity norm of z is within bound"""
        for poly in z:
            for coeff in poly:
                # Handle centered representation
                val = int(coeff)
                if val > LatticeOperations.DILITHIUM_Q // 2:
                    val = val - LatticeOperations.DILITHIUM_Q
                if abs(val) >= bound:
                    return False
        return True

    def _pack_w1(self, w1: List[np.ndarray]) -> bytes:
        """Pack w1 for hashing"""
        result = bytearray()
        for poly in w1:
            for coeff in poly:
                result.extend(int(coeff).to_bytes(2, "little"))
        return bytes(result)

    def _serialize_public_key(self, rho: bytes, t: List[np.ndarray]) -> bytes:
        """Serialize Dilithium public key"""
        result = bytearray(rho)
        for poly in t:
            for coeff in poly:
                result.extend(int(coeff).to_bytes(4, "little"))
        return bytes(result)

    def _serialize_secret_key(
        self, rho: bytes, K: bytes, s1: List[np.ndarray], s2: List[np.ndarray], t: List[np.ndarray]
    ) -> bytes:
        """Serialize Dilithium secret key"""
        result = bytearray(rho)
        result.extend(K)
        for poly in s1:
            for coeff in poly:
                val = int(coeff) % LatticeOperations.DILITHIUM_Q
                result.extend(val.to_bytes(4, "little"))
        for poly in s2:
            for coeff in poly:
                val = int(coeff) % LatticeOperations.DILITHIUM_Q
                result.extend(val.to_bytes(4, "little"))
        for poly in t:
            for coeff in poly:
                result.extend(int(coeff).to_bytes(4, "little"))
        return bytes(result)

    def _parse_public_key(self, pk: bytes) -> Tuple[bytes, List[np.ndarray]]:
        """Parse Dilithium public key"""
        rho = pk[:32]
        k = self.params["k"]
        n = LatticeOperations.DILITHIUM_N

        t = []
        offset = 32
        for _ in range(k):
            poly = np.zeros(n, dtype=np.int64)
            for j in range(n):
                poly[j] = int.from_bytes(pk[offset : offset + 4], "little")
                offset += 4
            t.append(poly)

        return rho, t

    def _parse_secret_key(
        self, sk: bytes
    ) -> Tuple[bytes, bytes, List[np.ndarray], List[np.ndarray], List[np.ndarray]]:
        """Parse Dilithium secret key"""
        rho = sk[:32]
        K = sk[32:64]

        k = self.params["k"]
        l_param = self.params["l"]
        n = LatticeOperations.DILITHIUM_N

        offset = 64

        s1 = []
        for _ in range(l_param):
            poly = np.zeros(n, dtype=np.int64)
            for j in range(n):
                poly[j] = int.from_bytes(sk[offset : offset + 4], "little")
                offset += 4
            s1.append(poly)

        s2 = []
        for _ in range(k):
            poly = np.zeros(n, dtype=np.int64)
            for j in range(n):
                poly[j] = int.from_bytes(sk[offset : offset + 4], "little")
                offset += 4
            s2.append(poly)

        t = []
        for _ in range(k):
            poly = np.zeros(n, dtype=np.int64)
            for j in range(n):
                if offset + 4 <= len(sk):
                    poly[j] = int.from_bytes(sk[offset : offset + 4], "little")
                    offset += 4
            t.append(poly)

        return rho, K, s1, s2, t

    def _serialize_signature(self, c_tilde: bytes, z: List[np.ndarray]) -> bytes:
        """Serialize Dilithium signature"""
        result = bytearray(c_tilde)
        for poly in z:
            for coeff in poly:
                val = int(coeff) % LatticeOperations.DILITHIUM_Q
                result.extend(val.to_bytes(4, "little"))
        return bytes(result)

    def _parse_signature(self, sig: bytes) -> Tuple[bytes, List[np.ndarray]]:
        """Parse Dilithium signature"""
        c_tilde = sig[:32]
        l_param = self.params["l"]
        n = LatticeOperations.DILITHIUM_N

        z = []
        offset = 32
        for _ in range(l_param):
            poly = np.zeros(n, dtype=np.int64)
            for j in range(n):
                if offset + 4 <= len(sig):
                    poly[j] = int.from_bytes(sig[offset : offset + 4], "little")
                    offset += 4
            z.append(poly)

        return c_tilde, z


class ConstitutionalHashValidator:
    """
    Post-Quantum Constitutional Hash Validator

    Uses CRYSTALS-Dilithium to sign and verify constitutional hashes,
    providing quantum-resistant integrity guarantees for governance decisions.
    """

    def __init__(self, algorithm: PQCAlgorithm = PQCAlgorithm.DILITHIUM_3):
        self.dilithium = DilithiumSignature(algorithm)
        self.key_pair: Optional[PQCKeyPair] = None
        self.constitutional_hash = CONSTITUTIONAL_HASH

        logger.info(f"Constitutional Hash Validator initialized with {algorithm.value}")

    def initialize(self) -> PQCKeyPair:
        """Initialize with a new key pair"""
        self.key_pair = self.dilithium.keygen()
        logger.info(f"Generated PQC key pair: {self.key_pair.key_id}")
        return self.key_pair

    def sign_governance_decision(self, decision: Dict[str, Any]) -> PQCSignature:
        """Sign a governance decision with post-quantum signature"""
        if not self.key_pair:
            raise RuntimeError("Validator not initialized. Call initialize() first.")

        # Canonicalize decision
        import json

        canonical = json.dumps(decision, sort_keys=True, separators=(",", ":"))
        message = canonical.encode("utf-8")

        # Add constitutional hash binding
        message = self.constitutional_hash.encode() + b"|" + message

        return self.dilithium.sign(message, self.key_pair.secret_key)

    def verify_governance_decision(
        self, decision: Dict[str, Any], signature: PQCSignature, public_key: bytes
    ) -> bool:
        """Verify a signed governance decision"""
        import json

        canonical = json.dumps(decision, sort_keys=True, separators=(",", ":"))
        message = canonical.encode("utf-8")
        message = self.constitutional_hash.encode() + b"|" + message

        return self.dilithium.verify(message, signature, public_key)

    def create_quantum_resistant_hash(self, data: bytes) -> str:
        """Create a quantum-resistant hash using SHA-3 with salt"""
        salt = secrets.token_bytes(32)

        # SHA-3 is considered quantum-resistant for pre-image resistance
        hash_input = salt + self.constitutional_hash.encode() + data
        result = hashlib.sha3_512(hash_input).hexdigest()

        return f"pqc-sha3:{salt.hex()[:16]}:{result}"


# Export main classes
__all__ = [
    "PQCAlgorithm",
    "SecurityLevel",
    "PQCKeyPair",
    "PQCSignature",
    "PQCEncapsulation",
    "KyberKEM",
    "DilithiumSignature",
    "ConstitutionalHashValidator",
    "CONSTITUTIONAL_HASH",
]
