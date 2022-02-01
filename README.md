[![MIT License](https://badgen.net/github/license/lumbric/green-pass-generator)](https://choosealicense.com/licenses/mit/)


Green Pass Generator
====================

Generates a beautiful credit card sized PDF file which contains your green pass, to prove your
Covid-19 immune status.

Install requirements:

    apt install inkscape
    pip install pyzbar base45 cryptography==2.8 cose cbor2 qrcode pillow


Then run the script, passing a picture which contains the QR code of your vaccination certificate:

    python green-pass-generator.py -i INPUT_IMAGE_WITH_QR_CODE


Note that this is a very early version. It might work or it might not work. Some caveats include:
no support for special characters in the name, no security checks (do not use with untrusted QR
codes), no proper handling of recovery certificates, ...
