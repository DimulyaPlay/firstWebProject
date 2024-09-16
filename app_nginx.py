from converter import create_app
from converter.Utils import config
from waitress import serve
import subprocess
from string import Template
import os
import threading

nginx_config_template = """
events {
    worker_connections 1024;
}

http {
    client_max_body_size 50M;
    server {
        listen ${app_port} ssl;
        server_name ${server_ip};

        ssl_certificate     ${ssl_certificate};
        ssl_certificate_key ${ssl_certificate_key};

        location / {
            proxy_pass http://127.0.0.1:${app_port};
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    server {
        listen 80;
        server_name ${server_name};

        location / {
            return 301 https://$host$request_uri;
        }
    }
}
"""


def generate_nginx_config(config):
    nginx_config = Template(nginx_config_template).safe_substitute(
        server_ip=config['server_ip'],
        ssl_certificate='cert.pem',
        ssl_certificate_key='key_unencrypted.pem',
        app_port=config['server_port']
    )

    with open('nginx_dynamic.conf', 'w') as f:
        f.write(nginx_config)


def start_nginx():
    subprocess.run(['nginx-1.27.1/nginx.exe', '-c', os.path.abspath('nginx_dynamic.conf')])


def start_flask():
    app = create_app(config)
    serve(app, host='127.0.0.1', port=config['server_port'], threads=12, max_request_body_size=50 * 1024 * 1024)


if __name__ == '__main__':
    generate_nginx_config(config)

    nginx_thread = threading.Thread(target=start_nginx, daemon=True)
    flask_thread = threading.Thread(target=start_flask, daemon=True)

    nginx_thread.start()
    flask_thread.start()

    nginx_thread.join()
    flask_thread.join()
