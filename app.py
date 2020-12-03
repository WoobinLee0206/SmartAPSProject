from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, jsonify
from flask.helpers import send_from_directory
# from data import Articles
import pymysql
from passlib.hash import pbkdf2_sha256
from functools import wraps
import json
import paho.mqtt.client as mqtt
import os
import plotly
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

# temperature = []
# humidity = []
static_folder = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "assets")

db = pymysql.connect(host='localhost', port=3306,
                     user='root', passwd='1234', db='project')


app = Flask(__name__, static_folder=static_folder)
app.debug = True
app.static_folder = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "assets")

# print(app.static_folder)
# print(app.static_url_path)

# app.static_url_path = '/assets'

# print(app.static_url_path)


# app.static_folder
# app.static_url_path


def on_connect_2(client, userdata, flags, rc):
    # print("Connect with result code" + str(rc) )
    client.subscribe('humidity')


def on_message_2(client, userdata, msg):
    # temperature.append(float(msg.payload))
    # cursor = db.cursor()
    # sql =  '''
    #     INSERT INTO arduino(humidity)
    #     VALUES (%s);
    #     '''
    # cursor.execute(sql, (float(msg.payload)))
    # db.commit()
    # db.close()
    print(float(msg.payload))


def on_connect_1(client, userdata, flags, rc):
    # print("Connect with result code" + str(rc) )
    client.subscribe('temperature')


def on_message_1(client, userdata, msg):
    # temperature.append(float(msg.payload))
    # cursor = db.cursor()
    # sql =  '''
    #     INSERT INTO arduino(temperature)
    #     VALUES (%s);
    #     '''
    # cursor.execute(sql, (float(msg.payload)))
    # db.commit()
    # db.close()
    print(float(msg.payload))


def is_logged_in(f):
    @wraps(f)
    def _wraper(*args, **kwargs):
        if 'is_logged' in session:
            # if session['is_logged']:
            return f(*args, **kwargs)
        else:
            flash('UnAuthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return _wraper


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        id = request.form.get('username')
        pw = request.form.get('password')
        # print([id , pw])

        sql = 'SELECT * FROM users WHERE username = %s'
        cursor = db.cursor()
        cursor.execute(sql, [id])
        users = cursor.fetchone()
        # print(users)

        if users == None:
            return redirect(url_for('login'))
        else:
            if pbkdf2_sha256.verify(pw, users[4]):
                session['is_logged'] = True
                session['username'] = users[2]
                # print(session)
                return redirect('/')
            else:
                return redirect(url_for('login'))

        # return "Success"
    else:
        return render_template('login.html')


def is_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['username'] == 'ADMIN':
            return redirect('/admin')
        else:
            return f(*args, **kwargs)
    return wrap


def is_admined(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['username'] != "ADMIN":
            return redirect('/')

        else:
            return f(*args, **kwargs)
    return wrap


@app.route('/admin', methods=['GET', 'POST'])
@is_logged_in
@is_admined
def admin():
    cursor = db.cursor()
    sql = 'SELECT * FROM users;'
    cursor.execute(sql)
    admin_user = cursor.fetchall()
    return render_template('admin.html', data=admin_user)


@app.route('/user/<string:id>', methods=['GET', 'POST'])
@is_logged_in
@is_admined
def change_level(id):
    if request.method == 'POST':
        cursor = db.cursor()
        sql = 'UPDATE `users` SET `auth` = %s WHERE `id` = %s;'
        auth = request.form['auth']
        cursor.execute(sql, [auth, id])
        return redirect('/')
    else:
        cursor = db.cursor()
        sql = "SELECT * FROM users WHERE id = %s"
        cursor.execute(sql, [id])
        user = cursor.fetchone()
        return render_template('change_level.html', users=user)


@app.route('/')
@is_logged_in
@is_admin
def home():

    cursor = db.cursor()
    sql = """
        SELECT EQP_ID, PRODUCT_ID, START_TIME, END_TIME
        FROM result_file
        ORDER BY EQP_ID, START_TIME;
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()
    # print(data_list)
    df = pd.DataFrame(data_list, columns=[
                      "EQP_ID", "PRODUCT_ID", "START_TIME", "END_TIME"])

    # df.coulmns = ["EQP_ID", , "PRODUCT_ID""START_TIME", "END_TIME"]
    timeline_view = px.timeline(
        df, x_start='START_TIME', x_end='END_TIME', y='EQP_ID', color='PRODUCT_ID', title='aa')
    timeline_view.update_layout(title={
        'text': "제품별 설비 가동률",
        'xanchor': 'center',
        'y': 0.9,
        'x': 0.5,
        'yanchor': 'top'})
    graph_json = json.dumps(timeline_view, cls=plotly.utils.PlotlyJSONEncoder)

    eqp_id = request.args.get('eqp_id')
    # print(request.args.get('eqp_id'))
    cursor = db.cursor()
    sql = """
        SELECT EQP_ID
        FROM equipment
    """
    cursor.execute(sql)
    eqp_list = cursor.fetchall()

    sql = """
    SELECT EQP_ID, TARGET_DATE, BUSY
    FROM load_stat
    """
    if (eqp_id, ) in eqp_list:
        sql += """
        WHERE EQP_ID='%s'
        """ % eqp_id

    cursor.execute(sql)
    data_list = cursor.fetchall()
    df = pd.DataFrame(data_list, columns=[
                      "EQP_ID", "TARGET_DATE", "BUSY"])

    # df.coulmns = ["EQP_ID", , "PRODUCT_ID""START_TIME", "END_TIME"]

    # line_graph = px.line(
    #     df, x='TARGET_DATE', y=['SETUP', 'BUSY', 'IDLE'])

    figure = go.Figure()

    figure.update_layout(title={
        'text': "설비별 가동현황 (Line Chart)",
        'xanchor': 'center',
        'y': 0.9,
        'x': 0.5,
        'yanchor': 'top'})
    if (eqp_id, ) in eqp_list:
        figure.add_trace(
            go.Line(x=df['TARGET_DATE'], y=df['BUSY'],
                    name=mode)
        )
    else:
        # all인경우.
        eqp_id = 'all'
        for eqp in eqp_list:
            eqp_per_df = df[df['EQP_ID'] == eqp[0]]
            figure.add_trace(
                go.Line(x=eqp_per_df['TARGET_DATE'],
                        y=eqp_per_df['BUSY'], name=eqp[0], legendgroup=eqp[0])
            )

    graph_line_json = json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)

    cursor = db.cursor()
    sql = """
        SELECT * 
        FROM demand 
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()

    return render_template('home.html', graph_json=graph_json, graph_line_json=graph_line_json, data_list=data_list)


@app.route('/about')
@is_logged_in
def about():
    # print("Success")
    # return "TEST"
    return render_template('about.html')


def is_logged_out(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'is_logged' in session:
            return redirect(url_for('home'))
        else:
            return f(*args, **kwargs)

    return wrap


@app.route('/register', methods=['GET', 'POST'])
@is_logged_out
def register():
    if request.method == 'POST':
        # data = request.body.get('author')
        name = request.form.get('name')
        email = request.form.get('email')
        password = pbkdf2_sha256.hash(request.form.get('password'))
        re_password = request.form.get('re_password')
        username = request.form.get('username')
        # name = form.name.data

        cursor = db.cursor()
        sql = 'SELECT username FROM users WHERE username = %s'
        cursor.execute(sql, [username])
        username_one = cursor.fetchone()
        if username_one:
            return redirect(url_for('register'))

        else:
            if(pbkdf2_sha256.verify(re_password, password)):
                # print(pbkdf2_sha256.verify(re_password, password))
                sql = '''
                    INSERT INTO users (name, email, username, password) 
                    VALUES (%s ,%s, %s, %s)
                '''
                cursor.execute(sql, (name, email, username, password))
                db.commit()
                # cursor = db.cursor()
                # cursor.execute('SELECT * FROM users;')
                # users = cursor.fetchall()

                return redirect(url_for('login'))
            else:
                return redirect(url_for('register'))
        db.close()
    else:
        return render_template('register.html')


@app.route('/articles')
@is_logged_in
def articles():
    # articles = Articles()
    # print(len(articles))
    cursor = db.cursor()
    sql = 'SELECT * FROM topic;'
    cursor.execute(sql)
    data = cursor.fetchall()
    # print(data)
    return render_template('articles.html', articles=data)


@app.route('/article/<string:id>')
@is_logged_in
def article(id):
    # print(type(id))
    # articles= Articles()[id-1]
    cursor = db.cursor()
    sql = 'SELECT * FROM topic WHERE id = %s;'
    cursor.execute(sql, [id])
    topic = cursor.fetchone()
    # print(topic)
    return render_template('article.html', data=topic)


@app.route('/add_articles', methods=['GET', 'POST'])
@is_logged_in
def add_articles():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        author = request.form['author']
        cursor = db.cursor()
        sql = ''' 
        INSERT INTO topic (title, body, author) 
                VALUES (%s, %s, %s)
        '''
        cursor.execute(sql, (title, body, author))
        db.commit()
        return redirect('/articles')
    else:
        return render_template('add_articles.html')
    db.close()


@app.route('/article/<string:id>/edit_article', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    if request.method == "POST":
        title = request.form['title']
        body = request.form['body']
        author = request.form['author']
        cursor = db.cursor()
        sql = ''' 
        UPDATE `topic` SET `title` = %s, `body` = %s, `author` = %s WHERE `id` = %s;
        '''
        cursor.execute(sql, (title, body, author, id))
        db.commit()
        # print(title)
        return redirect(url_for('articles'))
    else:
        # print(id)
        cursor = db.cursor()
        sql = 'SELECT * FROM topic WHERE id = %s;'
        cursor.execute(sql, [id])
        topic = cursor.fetchone()
        return render_template('edit_article.html', data=topic)
    db.close()


@app.route('/delete/<string:id>', methods=['POST'])
@is_logged_in
def delete(id):
    cursor = db.cursor()
    sql = 'DELETE FROM topic WHERE id = %s;'
    cursor.execute(sql, [id])
    db.commit()
    return redirect(url_for('articles'))


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    return redirect(url_for('login'))


# @app.route('/graph', methods=['GET', 'POST'])
# @is_logged_in
# def graph():
#     cursor = db.cursor()
#     sql = 'SELECT humidity, register_date FROM arduino ORDER BY register_date DESC limit 30;'
#     cursor.execute(sql)
#     db.commit()
#     data_all = cursor.fetchall()
#     # print(data_all)
#     data_temperature = []
#     data_register_date = []

#     for i, j in reversed(data_all):
#         data_temperature.append(i)
#         data_register_date.append(str(j.date()))

#     # print(data_register_date)

#     return render_template('graph.html', data1=data_temperature, data2=data_register_date)

    # for i in data_all:
    #     # print(i)
    #     # data_temperature.append(int(i[1]))
    #     print(len(data_temperature))
    #     print(data_all)
    #     if len(data_temperature) > 9:
    #         del data_temperature[0]

    #         data_temperature.append(int(data_all[len(data_all)-1][1]))
    #         # print(data_all[len(data_all)-1][1])
    #         # print(len(data_temperature))
    #         # data_temperature.append(int(i[1]))

    #     else:
    #         data_temperature.append(int(i[1]))

    #     # data_register_date.append(str(j.time()))

    # print(data_temperature)


@app.route('/test')
def test():
    cursor = db.cursor()
    sql = 'SELECT temperature, register_date FROM temperature;'
    cursor.execute(sql)
    data_all = cursor.fetchall()
    data_temperature = []
    data_register_date = []
    for i, j in data_all:
        data_temperature.append(int(i))
        data_register_date.append(str(j))

    return render_template('test.html', data=[data_temperature, data_register_date])


@app.route('/demand')
@is_logged_in
def demand():
    cursor = db.cursor()
    sql = """
        SELECT * 
        FROM demand 
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()
    return render_template('demand.html', data_list=data_list)


@app.route('/demand_edit', methods=['PUT'])
def demand_edit():
    data = json.loads(request.data)
    print(data)
    cursor = db.cursor()
    sql = """
        update demand 
        set PRODUCT_ID=%s, CUSTOMER_ID=%s, DUE_DATE=%s, DEMAND_QTY=%s
        where DEMAND_ID=%s
    """
    cursor.execute(sql, (data['productId'], data['customerId'],
                         data['dueDate'], data['demandQty'], data['demandId']))
    cursor.close()
    db.commit()
    return jsonify({
        "status": 'okay'
    })


@app.route('/equipment')
@is_logged_in
def equipment():
    cursor = db.cursor()
    sql = """
        SELECT * 
        FROM equipment 
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()
    return render_template('equipment.html', data_list=data_list)


@app.route('/product')
@is_logged_in
def product():
    cursor = db.cursor()
    sql = """
        SELECT * 
        FROM product 
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()
    return render_template('product.html', data_list=data_list)


@app.route('/step_route')
@is_logged_in
def step_route():
    cursor = db.cursor()
    sql = """
        SELECT * 
        FROM step_route 
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()
    return render_template('step_route.html', data_list=data_list)


@app.route('/eqp_arrange')
@is_logged_in
def eqp_arrange():
    cursor = db.cursor()
    sql = """
        SELECT * 
        FROM eqp_arrange 
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()
    return render_template('eqp_arrange.html', data_list=data_list)


@app.route('/setup_time')
@is_logged_in
def setup_time():
    cursor = db.cursor()
    sql = """
        SELECT * 
        FROM setup_time 
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()
    return render_template('setup_time.html', data_list=data_list)


@app.route('/interval')
def interval():
    return render_template('interval.html')


@app.route('/gantt_chart')
@is_logged_in
def gantt_chart():

    cursor = db.cursor()
    sql = """
        SELECT EQP_ID, PRODUCT_ID, START_TIME, END_TIME
        FROM result_file
        ORDER BY EQP_ID, START_TIME;
    """
    cursor.execute(sql)
    data_list = cursor.fetchall()
    # print(data_list)
    df = pd.DataFrame(data_list, columns=[
                      "EQP_ID", "PRODUCT_ID", "START_TIME", "END_TIME"])

    # df.coulmns = ["EQP_ID", , "PRODUCT_ID""START_TIME", "END_TIME"]
    timeline_view = px.timeline(
        df, x_start='START_TIME', x_end='END_TIME', y='EQP_ID', color='PRODUCT_ID', title='aa')
    timeline_view.update_layout(title={
        'text': "제품별 설비 가동률 (Gantt Chart)",
        'xanchor': 'center',
        'y': 0.9,
        'x': 0.5,
        'yanchor': 'top'})
    graph_json = json.dumps(timeline_view, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('gantt_chart.html', graph_json=graph_json)


@app.route('/EQP11')
@is_logged_in
def epq11():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, SETUP, BUSY, IDLE
        FROM load_stat
        WHERE EQP_ID = 'EQP11'
        ORDER BY TARGET_DATE;
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    # print(data_all)
    target_date = []
    setup = []
    busy = []
    idle = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        setup.append(j)
        busy.append(k)
        idle.append(l)
    print(target_date)
    return render_template('load_stat.html', target_date=target_date, setup=setup, busy=busy, idle=idle)


@app.route('/EQP12')
@is_logged_in
def eqp12():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, SETUP, BUSY, IDLE
        FROM load_stat
        WHERE EQP_ID = 'EQP12'
        ORDER BY TARGET_DATE;
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    print(data_all)
    target_date = []
    setup = []
    busy = []
    idle = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        setup.append(j)
        busy.append(k)
        idle.append(l)
    print(target_date)
    return render_template('load_stat.html', target_date=target_date, setup=setup, busy=busy, idle=idle)


@app.route('/EQP13')
@is_logged_in
def eqp13():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, SETUP, BUSY, IDLE
        FROM load_stat
        WHERE EQP_ID = 'EQP13'
        ORDER BY TARGET_DATE;
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    # print(data_all)
    target_date = []
    setup = []
    busy = []
    idle = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        setup.append(j)
        busy.append(k)
        idle.append(l)
    print(target_date)
    return render_template('load_stat.html', target_date=target_date, setup=setup, busy=busy, idle=idle)


@app.route('/EQP21')
@is_logged_in
def eqp21():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, SETUP, BUSY, IDLE
        FROM load_stat
        WHERE EQP_ID = 'EQP21'
        ORDER BY TARGET_DATE;
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    # print(data_all)
    target_date = []
    setup = []
    busy = []
    idle = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        setup.append(j)
        busy.append(k)
        idle.append(l)
    print(target_date)
    return render_template('load_stat.html', target_date=target_date, setup=setup, busy=busy, idle=idle)


@app.route('/EQP22')
@is_logged_in
def eqp22():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, SETUP, BUSY, IDLE
        FROM load_stat
        WHERE EQP_ID = 'EQP22'
        ORDER BY TARGET_DATE;
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    # print(data_all)
    target_date = []
    setup = []
    busy = []
    idle = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        setup.append(j)
        busy.append(k)
        idle.append(l)
    print(target_date)
    return render_template('load_stat.html', target_date=target_date, setup=setup, busy=busy, idle=idle)


@app.route('/EQP31')
@is_logged_in
def eqp31():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, SETUP, BUSY, IDLE
        FROM load_stat
        WHERE EQP_ID = 'EQP31'
        ORDER BY TARGET_DATE;
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    # print(data_all)
    target_date = []
    setup = []
    busy = []
    idle = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        setup.append(j)
        busy.append(k)
        idle.append(l)
    print(target_date)
    return render_template('load_stat.html', target_date=target_date, setup=setup, busy=busy, idle=idle)


@app.route('/EQP32')
@is_logged_in
def eqp32():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, SETUP, BUSY, IDLE
        FROM load_stat
        WHERE EQP_ID = 'EQP32'
        ORDER BY TARGET_DATE;
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    # print(data_all)
    target_date = []
    setup = []
    busy = []
    idle = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        setup.append(j)
        busy.append(k)
        idle.append(l)
    print(target_date)
    return render_template('load_stat.html', target_date=target_date, setup=setup, busy=busy, idle=idle)


@app.route('/EQP33')
@is_logged_in
def eqp33():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, SETUP, BUSY, IDLE
        FROM load_stat
        WHERE EQP_ID = 'EQP33'
        ORDER BY TARGET_DATE;
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    # print(data_all)
    target_date = []
    setup = []
    busy = []
    idle = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        setup.append(j)
        busy.append(k)
        idle.append(l)
    print(target_date)
    return render_template('load_stat.html', target_date=target_date, setup=setup, busy=busy, idle=idle)


@app.route('/graph', methods=['GET', 'POST'])
@is_logged_in
def graph():
    eqp_id = request.args.get('eqp_id')
    # print(request.args.get('eqp_id'))
    cursor = db.cursor()
    sql = """
        SELECT EQP_ID
        FROM equipment
    """
    cursor.execute(sql)
    eqp_list = cursor.fetchall()

    sql = """
    SELECT EQP_ID, TARGET_DATE, BUSY
    FROM load_stat
    """
    if (eqp_id, ) in eqp_list:
        sql += """
        WHERE EQP_ID='%s'
        """ % eqp_id

    cursor.execute(sql)
    data_list = cursor.fetchall()
    df = pd.DataFrame(data_list, columns=[
                      "EQP_ID", "TARGET_DATE", "BUSY"])

    # df.coulmns = ["EQP_ID", , "PRODUCT_ID""START_TIME", "END_TIME"]

    # line_graph = px.line(
    #     df, x='TARGET_DATE', y=['SETUP', 'BUSY', 'IDLE'])

    figure = go.Figure()

    figure.update_layout(title={
        'text': "설비별 가동 현황 (Line Chart)",
        'xanchor': 'center',
        'y': 0.9,
        'x': 0.5,
        'yanchor': 'top'})
    if (eqp_id, ) in eqp_list:
        figure.add_trace(
            go.Line(x=df['TARGET_DATE'], y=df['BUSY'])
        )
    else:
        # all인경우.
        eqp_id = 'all'
        for eqp in eqp_list:
            eqp_per_df = df[df['EQP_ID'] == eqp[0]]
            figure.add_trace(
                go.Line(x=eqp_per_df['TARGET_DATE'],
                        y=eqp_per_df['BUSY'], name=eqp[0], legendgroup=eqp[0])
            )

    graph_json = json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('line_graph.html', graph_json=graph_json, eqp_list=eqp_list, active_eqp_id=eqp_id)


@app.route('/step_wip', methods=['GET', 'POST'])
@is_logged_in
def step_wip():
    cursor = db.cursor()
    sql = """
        SELECT TARGET_DATE, PRESS, PAINT, FINISH
        FROM step_wip
    """
    cursor.execute(sql)
    data_all = cursor.fetchall()
    # print(data_all)
    target_date = []
    press = []
    paint = []
    finish = []
    for i, j, k, l in data_all:
        target_date.append(str(i))
        press.append(j)
        paint.append(k)
        finish.append(l)
    print(press)
    return render_template('step_wip.html', target_date=target_date, press=press, paint=paint, finish=finish)


if __name__ == '__main__':

    app.secret_key = 'secretkey123456789'
    app.run(host='0.0.0.0', port='8000')
