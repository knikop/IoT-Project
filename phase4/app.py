from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash_daq as daq
import RPi.GPIO as GPIO
import time
from time import sleep

import smtplib
from Freenove_DHT import DHT
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email 
from email.header import decode_header
import atexit
import subprocess

import paho.mqtt.client as mqtt
import threading
import sqlite3

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

LED1 = 21
GPIO.setup(LED1, GPIO.OUT, initial=GPIO.LOW)
client = mqtt.Client()
client.connect("172.20.10.2")

dht = DHT(17)

FAN_PIN_INPUT = 27
FAN_PIN_INPUT2 = 18
FAN_PIN_ENABLE = 22
GPIO.setup(FAN_PIN_INPUT,GPIO.OUT)
GPIO.setup(FAN_PIN_INPUT2,GPIO.OUT)
GPIO.setup(FAN_PIN_ENABLE,GPIO.OUT)

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

user_profile_modal = dbc.Modal(
    [
        dbc.ModalHeader('User Profile', style={'background-color': '#D9D9D6', 'color': 'black'}),
        dbc.ModalBody(id='user-profile-content', style={'padding': '30px'}),
    ],
    id='user-profile-modal',
    size='lg',
    style={'background-color': 'rgba(128, 128, 128, 0.5)'}
)

navlink_username = dbc.NavLink(
    id="navlink_username",
    disabled=True,
    style={"color": "white", "cursor": "default"}
)

navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.NavItem(navlink_username),
            dbc.NavbarBrand(
                "IoT Dashboard",
                className="mx-auto",
                style={
                    "color": "white",
                    "display": "flex",
                    "justify-content": "center",
                    "align-items": "center",
                    "position": "absolute",
                    "left": "50%",
                    "transform": "translateX(-50%)"
                },
            ),
            dbc.NavItem(
                dbc.NavLink(
                    "",
                    id="open-user-profile-button",
                    className="text-white user-profile-button",
                    style={"cursor": "pointer"}
                ),
                className="ml-auto"
            )
        ],
        fluid=True,
        style={
            "background-color": "rgb(0, 51, 102)",
            "color": "white",
            "height": "70px"  
        },
    ),
    color="rgb(0, 51, 102)",
    dark=True,
)


app.layout = html.Div([
    navbar,
    html.Div([
        html.Div([
            html.H3('Light Intensity', style={'color': 'white'}),
            html.Img(id='light_img', src=app.get_asset_url('lightOff.png'), height=150, width=150, n_clicks=0, style={'margin' : '20px', 'background-color': 'transparent'}),
            html.Div(id='light_intensity_text', style={'color': 'white'})
        ], style={
            'padding': '20px',
            'background-color': 'rgb(0, 51, 102)',
            'border-radius': '10px',
            'display': 'flex',
            'flex-direction': 'column',
            'align-items': 'center',
            'justify-content': 'center',
            'width' : '250px',
            'margin': '100 auto 60px auto'
        }),
        html.Div([
            html.H3('Temperature and Humidity'),
            daq.Gauge(
                id='temp_gauge',
                color={
                    'gradient': True,
                    'ranges': {
                        'green': [0, 20],
                        'yellow': [20, 25],
                        'red': [25, 50]
                    }
                },
                max=50
            ), 
            html.P(id='temp_value', style={'textAlign': 'center'}),
            daq.Gauge(
                id='humi_gauge',
                color={
                    'gradient': True,
                    'ranges': {
                        'green': [0, 40],
                        'yellow': [40, 60],
                        'red': [60, 100]
                    }
                },
                max=100
            ),
            html.P(id='humi_value', style={'textAlign': 'center'})
        ], style={'padding': '15px',
                   'background-color': 'rgba(169, 169, 169,0.7)',
                   'border-radius': '10px',
                   'flex': '1',
                   'width': '250px',
                   'margin': '0px 150px 0px 150px'}
                )
        ,html.Div([
                html.H3('Fan', style={'color': 'white'}),
                html.Img(id='fan_image', src=app.get_asset_url('fanOff.png'), height=150, width=150, style={'margin' : '20px', 'background-color': 'transparent'}),
                html.Div(id='fan_status', style={'color': 'white'})
            ], style={
                'padding': '20px',
                'background-color': 'rgb(0, 51, 102)',
                'border-radius': '10px',
                'display': 'flex',
                'flex-direction': 'column',
                'align-items': 'center',
                'justify-content': 'center',
                'width' : '250px',
                'margin': '100 auto 60px auto'
            }),
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'margin': '100px', 'margin-top' : '100px'}),
    user_profile_modal,
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0)
], style={'width': '100%', 'textAlign': 'center'})


rfid_tag = ""

@app.callback(
    Output('user-profile-modal', 'is_open'),
    Input('open-user-profile-button', 'n_clicks'),
    State('user-profile-modal', 'is_open')
)
def toggle_user_profile_modal(open_clicks, is_open):
    if open_clicks:
        return not is_open
    return is_open

@app.callback(
    Output('user-profile-content', 'children'),
    Input('user-profile-modal', 'is_open')
)
def display_user_profile_modal(is_open):
    global rfid_tag
    global light_intensity
    
    client.on_message = handle_messages
    if is_open:
        conn = sqlite3.connect('phase4.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        
        for row in rows:
            if row[1] == rfid_tag:
                name = row[2]
                temp_threshold = row[3]
                humidity_threshold = row[4]
                light_intensity_threshold = row[5]
                
                return html.Div([
                    html.H5('Name: {}'.format(name)),
                    html.H6('RFID Tag: {}'.format(rfid_tag)),
                    html.H6('Temperature Threshold: {}'.format(temp_threshold)),
                    html.H6('Humidity Threshold: {}'.format(humidity_threshold)),
                    html.H6('Light Intensity Threshold: {}'.format(light_intensity_threshold))
                ])
            elif rfid_tag == "":
                return html.Div('No one logged in')
        return html.Div([
                    html.H6('RFID Tag: {}'.format(rfid_tag)),
                    dbc.Input(id="name-input", placeholder="Enter your name", type="text", style= {"margin-top" : "5%"}),
                    dbc.Alert("Name cannot be empty.", color="danger", id="empty-alert", is_open=False, style={"margin-top": "1%"}),
                    dbc.Alert("Saved successfully!", color="success", id="success-alert", is_open=False, style={"margin-top": "1%"}),
                    dbc.Button("Save", id="save-button", className="mr-2", n_clicks=0, style= {"margin-top" : "5%", "margin-left" : "90%"}),
               ])


@app.callback(
    [Output('name-input', 'value'), Output('empty-alert', 'is_open'), Output('success-alert', 'is_open')],
    Input('save-button', 'n_clicks'),
    State('name-input', 'value')
)
def save_new_user(n_clicks, name):
    global rfid_tag
    global light_intensity
    global temp
    global humi
    if n_clicks > 0 and name is None:
        return name, True, False
    
    if n_clicks > 0 and name:
        conn = sqlite3.connect('phase4.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (rfid_tag, name, temp_threshold, humidity_threshold, light_threshold) VALUES (?, ?, ?, ?, ?)", (rfid_tag, name, temp, humi, light_intensity))
        conn.commit()
        return "", False, True
    
    return name, False, False

def mqtt_loop():
    client.loop_forever()
    
light_intensity = 1023


client.subscribe("room/lightIntensity")
client.subscribe("room/tagID")

mqtt_thread = threading.Thread(target=mqtt_loop)
mqtt_thread.start()

@app.callback(
    [Output('light_img', 'src'), Output('light_intensity_text', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_light_intensity(n):
    global light_intensity
    global email_sent_light
    client.on_message = handle_messages
    if light_intensity < 100:
        current_time = time.strftime('%H:%M:%S')
        send_email('Light Alert', f'The light turned ON at {current_time}', "light")
        GPIO.output(LED1, GPIO.HIGH)
        return app.get_asset_url('lightOn.png'), 'Light ON ({})'.format(light_intensity)
    else:
        if email_sent_light == True:
            GPIO.output(LED1, GPIO.LOW)
            return app.get_asset_url('lightOffss.png'), 'Light OFF ({})'.format(light_intensity)
        else:
            GPIO.output(LED1, GPIO.LOW)
            return app.get_asset_url('lightOffss.png'), 'Light OFF ({})'.format(light_intensity)
        
def handle_messages(client, userdata, message):
    global rfid_tag
    global light_intensity
    global temp
    global humi
    
    topic = message.topic
    payload = message.payload.decode()

    if topic == "room/tagID":
        if rfid_tag != payload:
            rfid_tag = payload
            conn = sqlite3.connect('phase4.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE rfid_tag=?", (rfid_tag,))
            row = cursor.fetchone()
            if row:
                name = row[2]
                temp_threshold = row[3]
                humidity_threshold = row[4]
                light_intensity_threshold = row[5]
                current_temp = temp
                current_humidity = humi
                current_light_intensity = light_intensity
                cursor.execute("UPDATE users SET temp_threshold=?, humidity_threshold=?, light_threshold=? WHERE rfid_tag=?", (current_temp, current_humidity, current_light_intensity, rfid_tag))
                conn.commit()
                
                current_time = time.strftime('%H:%M:%S')
                send_email('User Alert', f'The {name} logged in at {current_time}', "user")
                
    if topic == "room/lightIntensity":
        light_intensity = int(payload)


@app.callback(
    Output('navlink_username', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_navlink_username(n):
    if rfid_tag == "":
        return "Scan Rfid tag to log in"

    conn = sqlite3.connect('phase4.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    for row in rows:
        if row[1] == rfid_tag:
            return f"Welcome {row[2]}"
    return "Please create an account by clicking on register"

@app.callback(
    Output('open-user-profile-button', 'children'),
    Input('interval-component', 'n_intervals'),
    State('navlink_username', 'children')
)
def update_user_profile_button(n, navlink_username):
    if rfid_tag == "":
        return ""
    elif navlink_username == "Please create an account by clicking on register":
        return "Register"
    else:
        return "User Profile"

client.on_message = handle_messages

fan_status = 'OFF'
temp = 0
humi = 0

@app.callback(
    [Output('temp_gauge', 'value'), Output('humi_gauge', 'value'), Output('fan_image', 'src'), Output('fan_status', 'children'), Output('temp_value', 'children'), Output('humi_value', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_gauges(n):
    global fan_status
    global email_sent_fan
    global temp
    global humi
    chk = dht.readDHT11()
    if chk is dht.DHTLIB_OK:
        temp = dht.temperature
        humi = dht.humidity
            
        if temp > 24.4 and fan_status != 'ON':
            send_email('Temperature Alert', f'The current temperature is {temp}°C. Would you like to turn on the fan?', "fan")
            response = check_incoming_emails()
            if response:
                fan_status = 'ON'
                fan_image = 'fanOns.png'
                GPIO.output(FAN_PIN_ENABLE,GPIO.HIGH)
                GPIO.output(FAN_PIN_INPUT2,GPIO.LOW)
                GPIO.output(FAN_PIN_INPUT,GPIO.HIGH)
                sleep(5)
                GPIO.output(FAN_PIN_ENABLE,GPIO.LOW)
            
            return temp, humi, app.get_asset_url(fan_image), f'Fan is {fan_status}', f'Temperature: {temp}°C', f'Humidity: {humi}%'
        elif(fan_status == 'ON'):
            return temp, humi, app.get_asset_url('fanOns.png'), 'Fan is ON', f'Temperature: {temp}°C', f'Humidity: {humi}%'
        return temp, humi, app.get_asset_url('fanOffs.png'), 'Fan is OFF', f'Temperature: {temp}°C', f'Humidity: {humi}%'
    
gmail_user = 'juliend.bede@gmail.com'
gmail_password = 'flqbgxsdzsrobmeo'
email_sent_fan = False 
email_sent_light = False

def send_email(subject, message, checker):
    global email_sent_fan
    global email_sent_light
    
    if email_sent_fan == False and checker == "fan": 
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = 'julien.bernardo@bell.net'
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        email_sent_fan = True
    
    if email_sent_light == False and checker == "light": 
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = 'julien.bernardo@bell.net'
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        email_sent_light = True
    
    if checker == "user": 
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = 'julien.bernardo@bell.net'
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        

def check_incoming_emails():
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(gmail_user, gmail_password)
    imap.select("inbox")
    status, messages = imap.search(None, f'(UNSEEN FROM "julien.bernardo@bell.net")')

    if not messages[0]:
        return []
    
    messages = messages[0].split(b' ')
    messages = [int(x) for x in messages]
    messages.reverse()

    for message_id in messages:
        _, msg = imap.fetch(str(message_id), "(RFC822)")

        for response in msg:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])

                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                sender = msg["From"]
                body = ""
                
                if msg.is_multipart():
                    # loop through each part and extract the text
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))

                        # ignore any attachments
                        if "attachment" not in content_disposition:
                            # check for plain text or html content type
                            if "text/plain" in content_type:
                                body = part.get_payload(decode=True).decode()
                                break
                            elif "text/html" in content_type:
                                body = part.get_payload(decode=True).decode()
                                break
                else:
                    body = msg.get_payload(decode=True).decode()

                if "yes" in body.lower():
                    return True
    imap.close()
    imap.logout()
    
    return False

def cleanup():
    GPIO.output(FAN_PIN_ENABLE, GPIO.LOW)
    GPIO.output(LED1, GPIO.LOW)
    GPIO.cleanup()
    subprocess.call(["sudo", "fuser", "-k", "8085/tcp"])
    print("Cleanup function executed")

atexit.register(cleanup)

try:
    app.run_server(debug=True, host='127.0.0.1', port=8085)
except Exception as e:
    print(f"Exception occurred: {e}")
finally:
    cleanup()