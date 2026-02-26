from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

users = {}

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            room TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_message(username, room, message, timestamp):
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, room, message, timestamp) VALUES (?, ?, ?, ?)",
              (username, room, message, timestamp))
    conn.commit()
    conn.close()

# ---------------- ROUTE ----------------
@app.route('/')
def index():
    return render_template('index.html')

# ---------------- SOCKET EVENTS ----------------
@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room = data['room']

    join_room(room)
    users[request.sid] = {'username': username, 'room': room}

    emit('message', {
        'user': 'System',
        'msg': f'{username} joined {room}',
        'time': datetime.now().strftime('%H:%M'),
        'private': False
    }, room=room)

    update_users(room)

@socketio.on('send_message')
def handle_message(data):
    username = data['username']
    room = data['room']
    msg = data['msg']
    timestamp = datetime.now().strftime('%H:%M')

    save_message(username, room, msg, timestamp)

    emit('message', {
        'user': username,
        'msg': msg,
        'time': timestamp,
        'private': False
    }, room=room)

@socketio.on('private_message')
def handle_private(data):
    timestamp = datetime.now().strftime('%H:%M')

    emit('message', {
        'user': data['from'],
        'msg': f"(Private) {data['msg']}",
        'time': timestamp,
        'private': True
    }, room=data['to_sid'])

@socketio.on('typing')
def handle_typing(data):
    emit('typing', data['username'], room=data['room'], include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        user = users[request.sid]
        room = user['room']
        username = user['username']

        leave_room(room)
        del users[request.sid]

        emit('message', {
            'user': 'System',
            'msg': f'{username} left the chat',
            'time': datetime.now().strftime('%H:%M'),
            'private': False
        }, room=room)

        update_users(room)

def update_users(room):
    room_users = [u['username'] for u in users.values() if u['room'] == room]
    emit('user_list', room_users, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)