from converter import create_app

app = create_app()

if __name__ == '__main__':
    # Загрузка сертификата и ключа
    # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # context.load_cert_chain('cert.pem', 'key_unencrypted.pem')
    # app.run(debug=True,  ssl_context=context)
    app.run(host='0.0.0.0', port=5000, debug=True)
