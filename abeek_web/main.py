import cx_Oracle
from flask import *

#configuration
DEBUG = True
SECRET_KEY = 'dev key'
#DB conf
HOST = "13.124.155.182"
USERNAME = "team"
PASSWORD = "team"
DBNAME = "abeek"


#SQL QUERY
q_001 = "SELECT * FROM PAYMENTS"

#PAYMENT에 결제 내역을 저장. 유저아이디와 승하차 정보 필요.
q_002 = "INSERT INTO PAYMENTS (USER_ID, TIME_VALUE, GETTING, PRICE) " + \
        "VALUES (:1, SYSDATE, :2, :3)" 


# 
app = Flask(__name__)
app.config.from_object(__name__)


def connect_db():
    dsn = cx_Oracle.makedsn(HOST, 1521, "XE")
    return cx_Oracle.connect(USERNAME, PASSWORD, dsn)

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

###버스의 비콘 정보를 받은 후 결제할 지를 결정하는 페이지
######앱에서 세션을 채우고 페이지에 들어갈 때는 바로 해도 되겠지만
######우선 이 페이지는 세션을 채우기 위한 페이지로.
@app.route('/')
def testmain():
    err = None
    session = None
    if request.method == 'POST':
        session['user_id'] = request.form['user_id']
        session['price'] = request.form['price']
        session[request.form['getting']] = True
        if request.form['getting'] == 'get_on':
            session['getting'] = 1
        elif request.form['getting'] == 'get_off':
            session['getting'] = 0
        return redirect(url_for('isPaying'))
    return render_template('testmain.html', error = err)

###버스의 비콘 정보를 받은 후 결제할 지를 결정하는 페이지
@app.route('/paying', methods=['post'])
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
    return render_template('main.html')


@app.route('/add_on', methods=['GET', 'POST'])
def add_on():
    if not session.get('get_on'):
        abort(401)
    cur = g.db.cursor()
    cur.execute(q_002, \
                 [session['user_id'], session['getting'], session['price']])
    g.db.commit()
    flash('Getting-On data was successfully saved.')
    return redirect(url_for('complete'))

@app.route('/add_off', methods =['GET', 'POST'])
def add_off():
    if not session.get('get_off'):
        abort(401)
    cur = g.db.cursor()
    cur.execute(q_002, \
                 [session['user_id'], session['getting'], session['price']])
    g.db.commit()
    flash('Getting-Off data was successfully saved.')
    return redirect(url_for('complete'))

@app.route('/complete')
###결제 완료(승차, 하차)
def complete():
    return redirect(url_for('show_t'))

@app.route('/show_t')
def show_t():
    cur = g.db.cursor()
    cur.execute(q_001)
    T = [dict(user_id = row[0], timevalue=row[1], getting=row[2], price=row[3]) for row in cur.fetchall()]
    return render_template('show_t.html', entries = T)



@app.route('/login', methods=['GET', 'POST'])
def login():
    err = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            err = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            err = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in!')
            return redirect(url_for('show_t1'))
    return render_template('login.html', error = err)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out!')
    return redirect(url_for('show_t1'))

if __name__ == '__main__':
    app.run(host='0.0.0.0')