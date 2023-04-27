from dash import Dash, html
from dash.dependencies import Input, Output
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
LED1 = 17
GPIO.setup(LED1, GPIO.OUT, initial=GPIO.LOW)

app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.Img(id='light_img', src=app.get_asset_url('lightOff.png'), height=100, width=100, n_clicks=0)
        ]),
    html.Button('Turn On Light', id='on_button', n_clicks=0)
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

if __name__ == '__main__':
    app.run_server(debug=True)