#!/usr/bin/env python3
"""
ACGS-2 Certificate Management and Validation
============================================

Manages SSL/TLS certificates and implements certificate pinning for secure connections.

Features:
- Certificate validation for external services
- Certificate pinning implementation
- Certificate expiry monitoring
- Automated certificate rotation

Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
import ssl
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import ExtensionOID

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CertificateManager:
    """Manages SSL/TLS certificates and pinning for ACGS-2 services."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else Path("config/certificates.json")
        self.cert_cache: Dict[str, Dict] = {}
        self.pin_store: Dict[str, str] = {}  # domain -> pin

    async def validate_certificate(self, domain: str, port: int = 443) -> Dict[str, any]:
        """
        Validate SSL certificate for a domain.

        Returns certificate information and validation status.
        """
        try:
            # Create SSL context with certificate validation
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Connect and get certificate
            reader, writer = await asyncio.open_connection(
                domain, port, ssl=ssl_context
            )

            # Get certificate from connection
            cert = writer.get_extra_info('ssl_object').getpeercert(binary_form=True)
            if cert:
                cert_obj = x509.load_der_x509_certificate(cert, default_backend())
                cert_info = self._parse_certificate(cert_obj, domain)

                writer.close()
                await writer.wait_closed()

                return {
                    'valid': True,
                    'domain': domain,
                    'certificate': cert_info,
                    'errors': []
                }
            else:
                return {
                    'valid': False,
                    'domain': domain,
                    'certificate': None,
                    'errors': ['No certificate received']
                }

        except ssl.SSLError as e:
            return {
                'valid': False,
                'domain': domain,
                'certificate': None,
                'errors': [f'SSL Error: {str(e)}']
            }
        except Exception as e:
            return {
                'valid': False,
                'domain': domain,
                'certificate': None,
                'errors': [f'Connection Error: {str(e)}']
            }

    def _parse_certificate(self, cert: x509.Certificate, domain: str) -> Dict[str, any]:
        """Parse X.509 certificate and extract relevant information."""
        # Subject
        subject = cert.subject
        subject_cn = subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
        subject_cn = subject_cn[0].value if subject_cn else "Unknown"

        # Issuer
        issuer = cert.issuer
        issuer_cn = issuer.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
        issuer_cn = issuer_cn[0].value if issuer_cn else "Unknown"

        # Validity
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
        days_until_expiry = (not_after - datetime.now(not_after.tzinfo)).days

        # Subject Alternative Names
        san_extension = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        san_names = san_extension.value.get_values_for_type(x509.DNSName) if san_extension else []

        # Generate certificate pin (SPKI fingerprint)
        public_key = cert.public_key()
        public_key_der = public_key.public_key_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        pin = hashlib.sha256(public_key_der).hexdigest()

        return {
            'subject_common_name': subject_cn,
            'issuer_common_name': issuer_cn,
            'not_before': not_before.isoformat(),
            'not_after': not_after.isoformat(),
            'days_until_expiry': days_until_expiry,
            'subject_alt_names': san_names,
            'serial_number': str(cert.serial_number),
            'signature_algorithm': cert.signature_algorithm_oid._name,
            'pin_sha256': pin,
            'is_expired': datetime.now(not_after.tzinfo) > not_after,
            'is_self_signed': subject_cn == issuer_cn
        }

    def pin_certificate(self, domain: str, expected_pin: str) -> bool:
        """
        Pin a certificate for a domain.

        Returns True if pinning succeeds, False otherwise.
        """
        self.pin_store[domain] = expected_pin
        logger.info(f"Certificate pinned for {domain}: {expected_pin[:16]}...")
        return True

    async def validate_pinned_connection(self, domain: str, port: int = 443) -> Tuple[bool, str]:
        """
        Validate connection against pinned certificate.

        Returns (is_valid, message)
        """
        if domain not in self.pin_store:
            return False, f"No certificate pin configured for {domain}"

        expected_pin = self.pin_store[domain]

        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            reader, writer = await asyncio.open_connection(
                domain, port, ssl=ssl_context
            )

            cert = writer.get_extra_info('ssl_object').getpeercert(binary_form=True)
            if cert:
                cert_obj = x509.load_der_x509_certificate(cert, default_backend())

                # Calculate actual pin
                public_key = cert_obj.public_key()
                public_key_der = public_key.public_key_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                actual_pin = hashlib.sha256(public_key_der).hexdigest()

                writer.close()
                await writer.wait_closed()

                if actual_pin == expected_pin:
                    return True, f"Certificate pin validated for {domain}"
                else:
                    return False, f"Certificate pin mismatch for {domain}. Expected: {expected_pin[:16]}..., Actual: {actual_pin[:16]}..."

            return False, f"No certificate received from {domain}"

        except Exception as e:
            return False, f"Certificate validation failed for {domain}: {str(e)}"

    async def check_certificate_expiry(self, domains: List[str], warning_days: int = 30) -> Dict[str, List[str]]:
        """
        Check certificate expiry for multiple domains.

        Returns dict mapping domains to list of warnings/issues.
        """
        results = {}

        for domain in domains:
            try:
                cert_result = await self.validate_certificate(domain)

                if not cert_result['valid']:
                    results[domain] = cert_result['errors']
                    continue

                cert_info = cert_result['certificate']
                warnings = []

                if cert_info['is_expired']:
                    warnings.append("CERTIFICATE HAS EXPIRED")
                elif cert_info['days_until_expiry'] <= warning_days:
                    warnings.append(f"Certificate expires in {cert_info['days_until_expiry']} days")

                if cert_info['is_self_signed']:
                    warnings.append("Certificate is self-signed")

                if not any(domain in san or domain == cert_info['subject_common_name']
                          for san in cert_info['subject_alt_names']):
                    warnings.append(f"Domain {domain} not in certificate subject or SAN")

                results[domain] = warnings

            except Exception as e:
                results[domain] = [f"Error checking certificate: {str(e)}"]

        return results

    def load_certificate_pins(self, pin_config: Dict[str, str]) -> None:
        """Load certificate pins from configuration."""
        self.pin_store.update(pin_config)
        logger.info(f"Loaded {len(pin_config)} certificate pins")

    def save_certificate_pins(self, output_path: Optional[str] = None) -> None:
        """Save current certificate pins to file."""
        output_path = output_path or self.config_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump({
                'certificate_pins': self.pin_store,
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }, f, indent=2)

        logger.info(f"Saved certificate pins to {output_path}")


async def main():
    """Main entry point for certificate management."""
    import argparse

    parser = argparse.ArgumentParser(description='ACGS-2 Certificate Management')
    parser.add_argument('--check-expiry', nargs='*', help='Check certificate expiry for domains')
    parser.add_argument('--validate-cert', help='Validate certificate for a domain')
    parser.add_argument('--pin-cert', nargs=2, metavar=('DOMAIN', 'PIN'), help='Pin certificate for domain')
    parser.add_argument('--validate-pin', help='Validate pinned certificate for domain')
    parser.add_argument('--config', default='config/certificates.json', help='Certificate config file')

    args = parser.parse_args()

    manager = CertificateManager(args.config)

    if args.check_expiry:
        domains = args.check_expiry if args.check_expiry else [
            'mcp.neon.tech', 'huggingface.co', 'registry-1234567890.amazonaws.com'
        ]

        print(f"🔍 Checking certificate expiry for {len(domains)} domains...")
        results = await manager.check_certificate_expiry(domains)

        for domain, issues in results.items():
            if issues:
                print(f"⚠️  {domain}:")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print(f"✅ {domain}: Certificate OK")

    elif args.validate_cert:
        print(f"🔍 Validating certificate for {args.validate_cert}...")
        result = await manager.validate_certificate(args.validate_cert)

        if result['valid']:
            cert_info = result['certificate']
            print("✅ Certificate Valid"            print(f"   Subject: {cert_info['subject_common_name']}")
            print(f"   Issuer: {cert_info['issuer_common_name']}")
            print(f"   Expires: {cert_info['not_after']} ({cert_info['days_until_expiry']} days)")
            print(f"   PIN SHA256: {cert_info['pin_sha256']}")
        else:
            print("❌ Certificate Invalid"            for error in result['errors']:
                print(f"   - {error}")

    elif args.pin_cert:
        domain, pin = args.pin_cert
        manager.pin_certificate(domain, pin)
        manager.save_certificate_pins()
        print(f"📌 Certificate pinned for {domain}")

    elif args.validate_pin:
        valid, message = await manager.validate_pinned_connection(args.validate_pin)
        if valid:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
