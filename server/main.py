#-*- coding:utf-8 -*-

import pymysql
from flask import *
from flask_socketio import *

#configuration
DEBUG = True
SECRET_KEY = 'dev key'
#DB conf
HOST = "localhost"
USERNAME = "abeek"
PASSWORD = "abeek"
DBNAME = "abeek"


#SQL QUERY
q_001 = "SELECT user_id, time_value, getting, price, bus_id FROM PAYMENTS"

#PAYMENT에 결제 내역을 저장. 유저아이디와 승하차 정보 필요.
q_002 = "INSERT INTO PAYMENTS (USER_ID, TIME_VALUE, GETTING, PRICE) " + \
        "VALUES (%s, NOW(), %s, %s)" 


# 
app = Flask(__name__)
app.config.from_object(__name__)
io = SocketIO(app, host="0.0.0.0", threaded=True)
clients = dict()

def connect_db():
    return pymysql.connect(host=HOST, user=USERNAME, password=PASSWORD, db=DBNAME, charset='utf8')
@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

###버스의 비콘 정보를 받은 후 결제할 지를 결정하는 페이지
######앱에서 세션을 채우고 페이지에 들어갈 때는 바로 해도 되겠지만
######우선 이 페이지는 세션을 채우기 위한 페이지로.
# + 버스 전용 탭
@app.route('/')
def testmain():
    err = None
    session = None
    if request.method == 'POST':
        session['user_id'] = request.form['user_id']
        session['price'] = request.form['price']
        session[request.form['getting']] = True
        session['bus_id'] = request.form['bus_id']
        if request.form['getting'] == 'get_on':
            session['getting'] = 1
        elif request.form['getting'] == 'get_off':
            session['getting'] = 0
        return redirect(url_for('isPaying'))
    return render_template('testmain.html', error = err)

###버스 전용 페이지
@app.route('/bus', methods=['post'])
def busMain():
    if request.method == 'POST':
        session['bus_id'] = request.form['bus_id']
        print("posting bus id... " + session['bus_id'])
    return render_template('bus-client.html')

@io.on('connect')
def connected():
    before_request()
    tmpb = session['bus_id']
    if not (tmpb is None):
        print("%s bus-module connected." % (tmpb))
        clients[tmpb] = request.sid
        print(clients[tmpb] + "d여기")
        io.emit('init', tmpb, room=clients[session['bus_id']])
        io.emit('num', room=clients[session['bus_id']])
        io.emit('message', tmpb, room=clients[session['bus_id']])
        print("완료 " + clients[tmpb])


@io.on('disconnect')
def disconnected():
    print ("%s disconnected" % (request.sid))
    del clients[session['bus_id']]


###버스의 비콘 정보를 받은 후 결제할 지를 결정하는 페이지
@app.route('/paying', methods=['post','get'])
def isPaying():
    if request.method == 'POST':
        session['user_id'] = request.form['user_id']
        session['price'] = request.form['price']
        session[request.form['getting']] = True
        if request.form['getting'] == 'get_on':
            session['getting'] = 1
        elif request.form['getting'] == 'get_off':
            session['getting'] = 0
    return render_template('main.html')


@app.route('/add', methods=['GET', 'POST'])
def add():
    if not (session.get('get_on') | session.get('get_off')):
        abort(401)
    cur = g.db.cursor()
    

    if session.get('getting') == 1:
        io.emit('get_on', str(session['user_id']), room=clients[session['bus_id']])
        flash('Getting-On data was successfully saved.')
    elif session.get('getting') == 0:
        io.emit('get_off', str(session['user_id']), room=clients[session['bus_id']])
        flash('Getting-Off data was successfully saved.')
    io.emit('num')
    cur.execute(q_002, \
                [session['user_id'], session['getting'], session['price']])
    g.db.commit()
    
    return redirect(url_for('complete'))


@app.route('/complete')
###결제 완료(승차, 하차) / 결과 테이블을 보여줌
def complete():
    return redirect(url_for('show_t'))

@app.route('/show_t')
def show_t():
    cur = g.db.cursor()
    cur.execute(q_001)
    T = [dict(user_id = row[0], timevalue=row[1], getting=row[2], price=row[3], bus_id=row[4]) for row in cur.fetchall()]
    return render_template('show_t.html', entries = T)

if __name__ == '__main__':
    io.run(app)