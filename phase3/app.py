from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import dash_daq as daq
import RPi.GPIO as GPIO
import time

import smtplib
from Freenove_DHT import DHT
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
from email.header import decode_header
import atexit

import paho.mqtt.client as mqtt
import threading

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

LED1 = 21
GPIO.setup(LED1, GPIO.OUT, initial=GPIO.LOW)
client = mqtt.Client()
client.connect("172.20.10.8")

dht = DHT(17)

FAN_PIN_INPUT = 13
FAN_PIN_INPUT2 = 19
FAN_PIN_ENABLE = 26
GPIO.setup(FAN_PIN_INPUT,GPIO.OUT)
GPIO.setup(FAN_PIN_INPUT2,GPIO.OUT)
GPIO.setup(FAN_PIN_ENABLE,GPIO.OUT)

app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.H1('IoT Dashboard', style={'textAlign': 'center'}),
    ]),
    html.Div([
        html.Div([
            html.Img(id='light_img', src=app.get_asset_url('lightOff.png'), height=200, width=200, n_clicks=0),
            html.Div(id='light_intensity_text')
        ], style={'float': 'left', 'display': 'inline-block'}),
        html.Div(id='email_sent_message', style={'textAlign': 'left'}),
        html.Div([
            html.Img(id='fan_image', src=app.get_asset_url('fanOff.png'), height=200, width=200),
            html.P(id='fan_status')
        ], style={'float': 'right', 'display': 'inline-block', 'marginTop': '20px'})
    ], style={'width': '100%', 'textAlign': 'center'}),
    
    html.Div([
        html.Div([
            daq.Gauge(
                id='temp_gauge',
                label='Temperature',
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
        ], style={'flex': '1'}),
        
        html.Div([
            daq.Gauge(
                id='humi_gauge',
                label='Humidity',
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
        ], style={'flex': '1'}),
    ], style={'display': 'flex', 'justifyContent': 'center', 'marginTop': '50px'}),
    
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0)
])


def mqtt_loop():
    client.loop_forever()
    
light_intensity = 1023

client.subscribe("room/lightIntensity")

mqtt_thread = threading.Thread(target=mqtt_loop)
mqtt_thread.start()


@app.callback(
    [Output('light_img', 'src'), Output('light_intensity_text', 'children'), Output('email_sent_message', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_light_intensity(n):
    global light_intensity
    global email_sent
    client.on_message = get_intensity
    email_message = html.P('Email sent successfully', style={'color': 'green'})
    if light_intensity < 400:
        current_time = time.strftime('%H:%M:%S')
        send_email('Light Alert', f'The light turned ON at {current_time}')
        GPIO.output(LED1, GPIO.HIGH)
        return app.get_asset_url('lightOn.png'), 'Light ON ({})'.format(light_intensity), email_message
    else:
        if email_sent == True:
            GPIO.output(LED1, GPIO.LOW)
            return app.get_asset_url('lightOff.png'), 'Light OFF ({})'.format(light_intensity), email_message
        else:
            GPIO.output(LED1, GPIO.LOW)
            return app.get_asset_url('lightOff.png'), 'Light OFF ({})'.format(light_intensity), ""
def get_intensity(client, userdata, msg):
    global light_intensity
    if msg.topic == "room/lightIntensity":
        light_intensity = int(msg.payload.decode())
        
client.on_message = get_intensity

fan_status = 'OFF'
@app.callback(
    [Output('temp_gauge', 'value'), Output('humi_gauge', 'value'), Output('fan_image', 'src'), Output('fan_status', 'children'), Output('temp_value', 'children'), Output('humi_value', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_gauges(n):
    global fan_status
    
    try:
        chk = dht.readDHT11()
        if chk is dht.DHTLIB_OK:
            temp = dht.temperature
            humi = dht.humidity
        else:
            temp, humi = None, None
    except:
        temp, humi = None, None
    
    if temp is not None and humi is not None:
        chk = dht.readDHT11()
        if chk is dht.DHTLIB_OK:
            temp = dht.temperature
            humi = dht.humidity
            
            if temp > 23 and fan_status != 'ON':
                send_email('Temperature Alert', f'The current temperature is {temp}°C. Would you like to turn on the fan?')
                response = check_incoming_emails()
                if response:
                    fan_status = 'ON'
                    fan_image = 'fanOn.png'
                    GPIO.output(FAN_PIN_ENABLE,GPIO.HIGH)
                    GPIO.output(FAN_PIN_INPUT2,GPIO.LOW)
                    GPIO.output(FAN_PIN_INPUT,GPIO.HIGH)
                else:
                    fan_status = 'OFF'
                    fan_image = 'fanOff.png'
                
                return temp, humi, app.get_asset_url(fan_image), f'Fan is {fan_status}', f'Temperature: {temp}°C', f'Humidity: {humi}%'
            elif(fan_status == 'ON'):
                return temp, humi, app.get_asset_url('fanOn.png'), 'Fan is ON', f'Temperature: {temp}°C', f'Humidity: {humi}%'
            return temp, humi, app.get_asset_url('fanOff.png'), 'Fan is OFF', f'Temperature: {temp}°C', f'Humidity: {humi}%'
        
    else:
        return 0, 0, app.get_asset_url('fanOff.png'), 'Fan is OFF', 'Temperature: Error', 'Humidity: Error'


gmail_user = 'juliend.bede@gmail.com'
gmail_password = 'flqbgxsdzsrobmeo'
email_sent = False 

def send_email(subject, message):
    global email_sent  
    if not email_sent: 
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
        email_sent = True     
        

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

atexit.register(cleanup)

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)