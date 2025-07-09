from flask import render_template, current_app
from flask_mail import Message
from mentoria import mail
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    """Função genérica para enviar e-mails."""
    app = current_app._get_current_object()
    msg = Message(subject,
                  sender=f"Plataforma SUPER+ <{app.config['MAIL_USERNAME']}>",
                  recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    # Envia o e-mail numa thread separada para não bloquear a aplicação
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
