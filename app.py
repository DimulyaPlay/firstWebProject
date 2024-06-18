from converter import create_app
from converter.Utils import config
import ssl

# C:\\Users\\CourtUser\\Desktop\\release\\firstWebProject\\venv\\Scripts\\pyinstaller.exe --onedir --contents-directory "." --add-data "C:\\Users\\CourtUser\\Desktop\\release\\firstWebProject\\converter;converter"   C:\\Users\\CourtUser\\Desktop\\release\\firstWebProject\\app.py
# openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key_unencrypted.pem -out cert.pem

app = create_app(config)

if __name__ == '__main__':
    if config['server_secure'] == 'https':
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain('cert.pem', 'key_unencrypted.pem')
        app.run(host=config['server_ip'], port=config['server_port'], debug=True,  ssl_context=context, use_reloader=False)
    else:
        app.run(host=config['server_ip'], port=config['server_port'], debug=True, use_reloader=False)
