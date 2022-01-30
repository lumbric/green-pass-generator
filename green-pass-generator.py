import sys
import zlib
import base45
import cbor2
import subprocess
import qrcode.image.svg

from PIL import Image
from pyzbar.pyzbar import decode
from pyzbar.pyzbar import ZBarSymbol
from cose.messages import CoseMessage


def scan_certificate(fname):
    # # # using qrtools:
    # import qrtools
    # qr_code = qrtools.QR()
    # success = qr_code.decode(fname)
    # if not success:
    #     raise RuntimeError("Could not decode QR code")

    # return qr_code.data

    # # # using pyzbar:
    qr_codes = decode(Image.open(fname), symbols=[ZBarSymbol.QRCODE])
    success = len(qr_codes) == 1
    if not success:
        raise RuntimeError("Could not decode QR code")

    return qr_codes[0].data.decode()


def generate_certificate(certificate_encoded):
    # error correction rate of ‘Q’ (around 25%) is RECOMMENDED
    # https://github.com/ehn-dcc-development/hcert-spec/blob/main/hcert_spec.md#422-qr-2d-barcode
    error_correction = qrcode.ERROR_CORRECT_Q

    image = qrcode.make(
        certificate_encoded,
        error_correction=error_correction,
        image_factory=qrcode.image.svg.SvgFragmentImage,
    )
    return image


def parse_certificate(certificate_encoded):
    if not certificate_encoded.startswith("HC1"):
        raise ValueError(f"invalid certificate format: {certificate_encoded}")

    payload = certificate_encoded[4:]

    decoded = base45.b45decode(payload)
    decompressed = zlib.decompress(decoded)

    # decode COSE message (no signature verification done)
    # FIXME add (optional?) verification of certificate
    cose = CoseMessage.decode(decompressed)

    out = cbor2.loads(cose.payload)

    return out


def generate_green_pass(fname):
    with open("template.svg", "r") as f:
        green_pass_svg = f.read()

    certificate_encoded = scan_certificate(fname)

    certificate = parse_certificate(certificate_encoded)

    # FIXME check if this does actually work for all certificates
    replacements = {
        "FIRST_NAME": certificate[-260][1]["nam"]["gn"],
        "LAST_NAME": certificate[-260][1]["nam"]["fn"],
        "DATE_OF_BIRTH": certificate[-260][1]["dob"],
        "DATE_OF_VACCINATION": certificate[-260][1]["v"][0]["dt"],
        "QR_CODE": str(generate_certificate(certificate_encoded).to_string()),
    }

    # FIXME check for possible security issues
    for pattern, substitute in replacements.items():
        green_pass_svg = green_pass_svg.replace(pattern, substitute)

    with open("out.svg", "w") as f:
        f.write(green_pass_svg)

    subprocess.run(["inkscape", "--export-pdf", "out.pdf", "out.svg"], check=True)


if __name__ == "__main__":
    fname = sys.argv[1]
    generate_green_pass(fname=fname)
