from dash import Dash, html, dcc
from dash.dependencies import Input, Output
from Freenove_DHT import DHT
import RPi.GPIO as GPIO
import time
import dash_daq as daq
import atexit
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
from email.header import decode_header

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

dht = DHT(17)
LED1 = 12
FAN_PIN_INPUT = 13
FAN_PIN_INPUT2 = 19
FAN_PIN_ENABLE = 26
GPIO.setup(FAN_PIN_INPUT,GPIO.OUT)
GPIO.setup(FAN_PIN_INPUT2,GPIO.OUT)
GPIO.setup(FAN_PIN_ENABLE,GPIO.OUT)
GPIO.setup(LED1, GPIO.OUT, initial=GPIO.LOW)

app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.H1('IoT Dashboard', style={'textAlign': 'center'}),
    ]),
    html.Div([
        html.Div([
            html.Img(id='light_img', src=app.get_asset_url('lightOff.png'), height=200, width=200, n_clicks=0),
            html.Button('Turn On Light', id='on_button', n_clicks=0, style={'border': 'none', 'marginTop': '30px'})
        ], style={'float': 'left', 'display': 'inline-block'}),
        
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
    
    dcc.Interval(id='interval-component', interval=5000, n_intervals=0)
])

state = False

@app.callback(
    [Output('light_img', 'src'), Output('on_button', 'children')],
    [Input('light_img', 'n_clicks'), Input('on_button', 'n_clicks')]
)
def toggle_light(n_clicks, on_clicks):
    global state
    if on_clicks % 2 == 1:
        GPIO.output(LED1, GPIO.HIGH)
        state = True
        return app.get_asset_url('lightOn.png'), 'Turn Off Light'
    else:
        if n_clicks % 2 == 0:
            GPIO.output(LED1, GPIO.LOW)
            state = False
            return app.get_asset_url('lightOff.png'), 'Turn On Light'
        else:
            GPIO.output(LED1, GPIO.HIGH)
            state = True
            return app.get_asset_url('lightOn.png'), 'Turn Off Light'




@app.callback(
    [Output('temp_gauge', 'value'), Output('humi_gauge', 'value'), Output('fan_image', 'src'), Output('fan_status', 'children'), Output('temp_value', 'children'), Output('humi_value', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_gauges(n):
    chk = dht.readDHT11()
    if chk is dht.DHTLIB_OK:
        temp = dht.temperature
        humi = dht.humidity
        
        if temp > 20:
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
    GPIO.cleanup()

atexit.register(cleanup)

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)