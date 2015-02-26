import flask
from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.orm import model_form
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeSerializer, BadSignature
from datetime import datetime
from flask_bootstrap import Bootstrap
from flask import request
from flask.ext.mail import Mail
from flask.ext.mail import Message

app = flask.Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/dan/University/Burda/mood_monitoring/main.db'
app.config['SECRET_KEY'] = 'test'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_USERNAME'] = 'cargodummy@gmail.com'
app.config['MAIL_PASSWORD'] = '253270514'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['DEBUG'] = True

db = SQLAlchemy(app)

admin = Admin(app)

mail = Mail(app)

Bootstrap(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)

    def __init__(self, username="", email=""):
        self.username = username
        self.email = email
        
    def __repr__(self):
        return '<User %r>' % self.username

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_question = db.Column(db.Text)
    quiz_date = db.Column(db.DateTime)

    def __init__(self, quiz_date=None):
        if quiz_date is None:
            quiz_date = datetime.utcnow()
        self.quiz_date = quiz_date
    
    def __repr__(self):
        return '<Quiz %r>' % self.quiz_date

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reply_text = db.Column(db.Text)
    reply_date = db.Column(db.DateTime)
    reply_mark = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    
    def __init__(self, user_id, reply_text="", reply_mark=1, reply_date=None):
        
        self.user_id = user_id
        self.reply_text = reply_text
        self.reply_mark = reply_mark
        if reply_date is None:
            reply_date = datetime.utcnow()
        
        self.reply_date = reply_date

    def __repr__(self):
        return '<Reply %r>' % self.id

MAIL_TEMPLATE = "Hello, {user_name}. Please, leave your reply to the following quiz via link {link}."

def get_secure_reply_url(quiz_model, user_model):
    quiz_id = quiz_model.id
    user_id = user_model.id
    secret_key = app.config['SECRET_KEY']
    serializer = URLSafeSerializer(secret_key)
    secure_user_id = serializer.dumps(user_id)
    return flask.url_for('quiz_reply_page', quiz_id=quiz_id, secure_user_id=secure_user_id, _external=True)

def send_emails_to_all_users(form, quiz_model, is_created):
    
    if not is_created:
        return
    
    template = "Hello, {username}"
    
    quiz_question = quiz_model.quiz_question
    users = User.query.all()
    
    with mail.connect() as conn:
        for user in users:
            user_reply_secure_url = get_secure_reply_url(quiz_model, user)
            body = MAIL_TEMPLATE.format(user_name=user.username, link=user_reply_secure_url)
            msg = Message(sender="cargodummy@gmail.com",
                            recipients=[user.email],
                            body=body,
                            subject=("Vibometer quiz: " + quiz_question))
            conn.send(msg)

Reply_form = model_form(Reply, Form)

Quiz_model_controller = ModelView(Quiz, db.session)
Quiz_model_controller.after_model_change = send_emails_to_all_users


admin.add_view(ModelView(User, db.session))
admin.add_view(Quiz_model_controller)
admin.add_view(ModelView(Reply, db.session))

@app.route("/")
def index():
    
    msg = Message("Hello",
                  sender="cargodummy@gmail.com",
                  recipients=["cargodummy@gmail.com"])
    
    mail.send(msg)
    
    return 'the mail is sent'

@app.route("/get_auth_token/<quiz_id>/<user_id>")
def get_auth_token(quiz_id, user_id):
    secret_key = app.config['SECRET_KEY']
    serializer = URLSafeSerializer(secret_key)
    secure_user_id = serializer.dumps(user_id)
    return flask.url_for('quiz_reply_page', quiz_id=quiz_id, secure_user_id=secure_user_id, _external=True)

@app.route('/quiz_reply/<quiz_id>/<secure_user_id>', methods=['GET', 'POST'])
def quiz_reply_page(quiz_id, secure_user_id):
    secret_key = app.config['SECRET_KEY']
    serializer = URLSafeSerializer(secret_key)
    
    try:
        user_id = serializer.loads(secure_user_id)
    except BadSignature:
        abort(404)

    user = User.query.get_or_404(user_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        reply_text = request.form.get("reply_text")
        reply_mark = request.form.get("reply_mark")
        new_reply = Reply(user.id, reply_text, reply_mark)
        db.session.add(new_reply)
        db.session.commit()
        return 'success'
    
    reply_form = Reply_form()
    
    return flask.render_template('quiz_reply.html', user=user, quiz=quiz, secure_user_id=secure_user_id, reply_form=reply_form)

if __name__ == "__main__":
    app.run(debug=True)
    
