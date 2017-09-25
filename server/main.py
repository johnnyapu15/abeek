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
q_002 = "INSERT INTO PAYMENTS (USER_ID, TIME_VALUE, GETTING, PRICE, BUS_ID) " + \
        "VALUES (%s, NOW(), %s, %s, %s)" 


# 
app = Flask(__name__)
app.config.from_object(__name__)
io = SocketIO(app)
clients = dict()


def connect_db():
    return pymysql.connect(host=HOST, user=USERNAME, password=PASSWORD, db=DBNAME, charset='utf8')
#@app.before_request
#def before_request():
#    g.db = connect_db()

#@app.teardown_request
#def teardown_request(exception):
#    g.db.close()

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
        if (request.form['bus_id']) != None:
            session['bus_id'] = request.form['bus_id']
            #print("posting bus id... " + session['bus_id'].encode('utf-8'))
            return render_template('bus-client.html')

@io.on('connect')
def connected():
    #before_request()
    print('New session is started')


@io.on('bus-connect')
def bus_connect():
    #before_request()
    tmpb = session['bus_id'].encode('utf-8')
    if not (tmpb is None):
        if (tmpb != ""):
            if clients.get(tmpb) == None:
                clients[tmpb] = 0
            join_room(tmpb)
            io.emit('init', tmpb, room=tmpb)
            io.emit('num', clients[tmpb], room=tmpb)
            io.emit('update', clients, room='buslist')
            print("%s bus-module connected." % (tmpb + ' - ' + request.sid))
        else:
            flash("Can't blank for bus number.")



@io.on('disconnect')
def disconnected():
#    before_request()
    print ("%s bus-module disconnected" % (request.sid))

@io.on('bus-disconnect')
def bus_disconnect():
#    before_request()
    del clients[(session['bus_id']).encode('utf-8')]
    io.emit('update',clients, room='buslist')
    return render_template('testmain.html')


###버스의 비콘 정보를 받은 후 결제할 지를 결정하는 페이지
@app.route('/paying', methods=['post','get'])
def isPaying():
    if request.method == 'GET':
        flash('Using POST method to add data.')
        return render_template('testmain.html')
    elif request.method == 'POST':
        if clients.get(request.form['bus_id'].encode('utf-8')) != None:
            session['user_id'] = request.form['user_id']
            session['price'] = request.form['price']
            session[request.form['getting']] = True
            session['bus_id'] = request.form['bus_id'].encode('utf-8')
            if request.form['getting'] == '1':
                session['getting'] = 1
            elif request.form['getting'] == '0':
                session['getting'] = 0
                return redirect(url_for('add'))
        else:
            flash('There is no bus %s.' % request.form['bus_id'])
            return render_template('testmain.html')
    return render_template('main.html')

###버스 모듈(파이)에 메세징
@app.route('/bus', methods=['get'])
def busRead():
    if request.method == 'GET':
        bid = request.args.get('bus_id')
        if clients.get(bid) != None:
            return str(clients[bid])
        else:
            return 'Nope.'

@app.route('/addDirect', methods=['GET', 'POST'])
def addDirect():
    g.db = connect_db()
    cur = g.db.cursor()
    print(2222)
    if request.method == 'GET':
        req = request.args
    elif request.method == 'POST':
        req = request.args
    if str(req.get('getting')) == '1':
        io.emit('get_on', str(req['user_id']), room=(req['bus_id'].encode('utf-8')))
        flash('Getting-On data was successfully saved.')
        clients[(req['bus_id'])] += 1
    elif str(req.get('getting')) == '0':
        io.emit('get_off', str(req['user_id']), room=(req['bus_id'].encode('utf-8')))
        flash('Getting-Off data was successfully saved.')
        clients[(req['bus_id'])] -= 1
    io.emit('num', clients[(req['bus_id'].encode('utf-8'))], room=(req['bus_id']))
    io.emit('update',clients, room='buslist')
    cur.execute(q_002, \
                [req['user_id'], req['getting'], req['price'], req['bus_id']])
    g.db.commit()
    g.db.close()
    return redirect(url_for('complete'))



@app.route('/add', methods=['GET', 'POST'])
def add():
    if (session.get('getting') == None):
        abort(401)
    g.db = connect_db()
    cur = g.db.cursor()
    

    if session.get('getting') == 1:
        io.emit('get_on', str(session['user_id']), room=session['bus_id'])
        flash('Getting-On data was successfully saved.')
        clients[session['bus_id']] += 1
    elif session.get('getting') == 0:
        io.emit('get_off', str(session['user_id']), room=session['bus_id'])
        flash('Getting-Off data was successfully saved.')
        clients[session['bus_id']] -= 1
    io.emit('num', clients[session['bus_id']], room=session['bus_id'])
    io.emit('update',clients, room='buslist')
    cur.execute(q_002, \
                [session['user_id'], session['getting'], session['price'], session['bus_id']])
    g.db.commit()
    g.db.close()
    return redirect(url_for('complete'))


@app.route('/complete')
###결제 완료(승차, 하차) / 결과 테이블을 보여줌
def complete():
    return redirect(url_for('show_t'))

@app.route('/show_t')
def show_t():
    g.db = connect_db()
    cur = g.db.cursor()
    cur.execute(q_001)
    T = [dict(user_id = row[0], timevalue=row[1], getting=row[2], price=row[3], bus_id=row[4]) for row in cur.fetchall()]
    cur.close()
    g.db.close()
    return render_template('show_t.html', entries = T)

@io.on('busListUpdate')
@app.route('/show_bt', methods=['GET','POST'])
def show_bt():
    T = list()
    for i in clients.keys():
        T.append(dict(bus_id=i, num=clients[i]))
    return render_template('bus-list.html', entries = T)

@io.on('busListJoin')
def join_bt():
    #before_request()
    join_room('buslist')
    io.emit('update',clients, room='buslist')

if __name__ == '__main__':
    io.run(app, host="0.0.0.0")