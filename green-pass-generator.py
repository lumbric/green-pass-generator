import zlib
import base45
import cbor2
import string
import argparse
import subprocess
import qrcode.image.svg

from PIL import Image
from pprint import pprint
from pathlib import Path
from pyzbar.pyzbar import decode
from pyzbar.pyzbar import ZBarSymbol
from cose.messages import CoseMessage


# this is the width of the QR code in the template, if the generated QR code is larger or smaller
# it needs to be scaled
QR_CODE_DEFAULT_WIDTH = 89


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


def generate_green_pass(input_fname, output_fname, output_dir):
    print(f"Generating green pass for {input_fname}...")

    with open("template.svg", "r") as f:
        green_pass_svg = f.read()

    certificate_encoded = scan_certificate(fname=input_fname)

    certificate = parse_certificate(certificate_encoded)

    pprint(certificate)

    qr_code_svg = generate_certificate(certificate_encoded)

    # not really checked if this is the right way to go, but it seems to work
    qr_scaling_factor = QR_CODE_DEFAULT_WIDTH / qr_code_svg.width

    print("QR Code width:", qr_code_svg.width)
    print("QR Code size:",  qr_code_svg.pixel_size / qr_code_svg.box_size)

    # FIXME check if this does actually work for all certificates
    name = certificate[-260][1]["nam"]
    vaccinations = certificate[-260][1]["v"]
    assert len(vaccinations) == 1, "unexpected number of vaccination entries" # not supported yet
    vaccination = certificate[-260][1]["v"][0]
    replacements = {
        "FIRST_NAME": name["gn"],
        "LAST_NAME": name["fn"],
        "DATE_OF_BIRTH": certificate[-260][1]["dob"],
        "DATE_OF_VACCINATION": vaccination["dt"],
        "NO_OF_DOSES": str(vaccination["sd"]),
        "DOSE_NUMBER": str(vaccination["dn"]),
        "QR_CODE": qr_code_svg.to_string().decode(),
        "QR_SCALING_FACTOR": f"scale({qr_scaling_factor} {qr_scaling_factor})",
    }

    # FIXME check for possible security issues
    for pattern, substitute in replacements.items():
        green_pass_svg = green_pass_svg.replace(pattern, substitute)

    if output_fname is None:
        def filter_name(name):
            return ''.join(char for char in name.lower() if char in string.ascii_lowercase)

        first_name = filter_name(name['gnt'])
        last_name = filter_name(name['fnt'])

        output_fname = f"greenpass-{first_name}-{last_name}"

    output_path = Path(output_dir) / output_fname
    output_path_svg = f"{output_path}.svg"
    output_path_pdf = f"{output_path}.pdf"

    with open(output_path_svg, "w") as f:
        f.write(green_pass_svg)

    subprocess.run(["inkscape", "--export-pdf", output_path_pdf, output_path_svg], check=True)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generates a beautiful credit card sized PDF file which contains your green "
            "pass, to prove your Covid-19 immun status."
        )
    )

    parser.add_argument(
        "-i", "--input", required=True, help="Image file name containing a certificate as QR Code"
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output file name, extension '.pdf' and '.svg' will be appended. If not provided, "
            "file name will be generated using the name in the certificate."
        ),
    )
    parser.add_argument("-O", "--output-dir", default=".", help="Output files are stored here.")
    args = parser.parse_args()

    generate_green_pass(
        input_fname=args.input,
        output_fname=args.output,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
