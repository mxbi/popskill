#gunicorn --certfile certs/fullchain.pem --keyfile certs/privkey.pem --bind 0.0.0.0:7355 app:app
gunicorn --bind unix:/tmp/popskill-api.sock --umask 777 app:app
