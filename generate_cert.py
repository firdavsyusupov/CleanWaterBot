from OpenSSL import crypto
from datetime import datetime, timedelta


def generate_self_signed_cert():
    # Генерация ключевой пары
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    # Создание сертификата
    cert = crypto.X509()
    # cert.get_subject().CN = "192.168.1.27"  # Используем ваш IP
    cert.get_subject().CN = "194.163.152.59"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Действителен 1 год
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)

    # Добавляем альтернативные имена (IP и localhost)
    alt_names = [
        b"DNS:localhost",
        b"IP:192.168.1.27",  # Ваш IP
        b"IP:127.0.0.1",
        b"IP:194.163.152.59"
    ]

    alt_names_ext = crypto.X509Extension(
        b"subjectAltName",
        False,
        b", ".join(alt_names)
    )
    cert.add_extensions([alt_names_ext])

    cert.sign(key, 'sha256')

    # Сохранение сертификата и ключа
    with open("cert.pem", "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    with open("key.pem", "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))


if __name__ == '__main__':
    generate_self_signed_cert()