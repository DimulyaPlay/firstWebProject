from converter import create_app
from converter.Utils import config

# C:\\Users\\CourtUser\\Desktop\\release\\firstWebProject\\venv\\Scripts\\pyinstaller.exe --onedir --contents-directory "." --add-data "C:\\Users\\CourtUser\\Desktop\\release\\firstWebProject\\converter;converter"   C:\\Users\\CourtUser\\Desktop\\release\\firstWebProject\\app.py

app = create_app(config)

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain('cert.pem', 'key_unencrypted.pem')
    app.run(debug=True,  ssl_context=context)
    # app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
