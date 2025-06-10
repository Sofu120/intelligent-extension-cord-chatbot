import pickle
from io import BytesIO
import sqlite3, traceback
from datetime import datetime
import matplotlib.pyplot as plt


import requests
import statistics
from flask import Flask, abort, request, jsonify

from linebot import WebhookHandler, LineBotApi
from linebot.models import (    RichMenu, RichMenuArea, RichMenuBounds,\
                                MessageEvent, TextMessage, TextSendMessage,\
                                TemplateSendMessage, ButtonsTemplate, MessageAction, ImageSendMessage   )

from botton_and_sql import socket_status_menu, analysis_of_recent_status_for_plotting, identify_the_target_socket
from interact_with_PI import checking_the_sockets, saving_the_data, dis_or_connect_the_socket#, get_ngrok_url



app = Flask(__name__)
MY_NGROK_link = ""
RASPBERRY_PI_link = ''


line_bot_api = LineBotApi('')
handler = WebhookHandler('')




# THE ENTRANCE FOR LINEBOT TO SERVER
@app.route("/callback", methods=['POST'])
def callback():

    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
   
    except Exception as e:
        print("=== Exception occurred ===")
        print(traceback.format_exc())
        return "Error", 400

    return 'OK'

# IF THE MSEEAGE FROM USER IS TYPE OF "TEXT",
# THEN THE LINEBOT WILL REACH THIS HANDLER TO FOLLOW THE DEALING LOGIC.
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print(f'\n\n\n=========event.source.user_id========== {event.source.user_id} \n\n\n========================')
    user_input = event.message.text
    
    if user_input == '查閱插座接通狀態':
        
        status = checking_the_sockets( RASPBERRY_PI_link )
        
        if 'ERROR' in status:
            reply = f"無法取得插座狀態。\n錯誤原因：{status['ERROR']}"
        else:
            print(status)
            socket_status_menu(status)
            message = socket_status_menu(status)
            line_bot_api.reply_message(event.reply_token, message)

    elif '近期狀態' in user_input:
        
        
        if ' A 插座近期狀態' in user_input:
            avg, std, fig_name = analysis_of_recent_status_for_plotting("A_socket_report")
            socket_name = 'A'

        elif ' B 插座近期狀態' in user_input:
            avg, std, fig_name = analysis_of_recent_status_for_plotting("B_socket_report")
            socket_name = 'B'

        elif ' C 插座近期狀態' in user_input:
            avg, std, fig_name = analysis_of_recent_status_for_plotting("C_socket_report")
            socket_name = 'C'
        
        else:
            print("Invaild situation! Try again!")


        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        print(f'===============fig_name================\n\n\n{fig_name}\n\n\n================================')

        line_bot_api.reply_message(
            
            event.reply_token,
            ImageSendMessage(
                                preview_image_url    = MY_NGROK_link + '/static/' + fig_name,
                                original_content_url = MY_NGROK_link + '/static/' + fig_name
                            )
        )

        line_bot_api.push_message(
                
                event.source.user_id,
                TemplateSendMessage(
                   
                    alt_text='近期狀態資訊',
                    template=ButtonsTemplate(
                        
                        title='統計資訊',
                        text=f'平均電流：{avg} 安培\n標準差：{std} 安培',
                        actions=[
                            MessageAction(label='斷開該插座', text=f'斷開插座 {socket_name}'),
                            MessageAction(label='了解，感謝您的協助！', text='已收到！')
                        ]
                    )
                )
            )

    elif '斷開' in user_input and "已斷開" not in user_input:
        target_socket = identify_the_target_socket(user_input)
        reply = dis_or_connect_the_socket(target_socket, RASPBERRY_PI_link, 0)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f'已斷開插座{target_socket}')
        )

    elif '接通' in user_input and "已接通" not in user_input:
        target_socket = identify_the_target_socket(user_input)
        reply = dis_or_connect_the_socket(target_socket, RASPBERRY_PI_link, 1)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f'已接通插座{target_socket}')
        )

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=user_input)
        )
            





# THIS ROUTER IS FOR PASPBERRY PI TO POST DATA TO THE SERVER,
# AND THE SERVER WILL SAVE THE CURRENT DATA IN THE CORRESPONDING TABLE. 
@app.route('/receive_data', methods=['POST'])
def receive_data():
    
    data = request.get_json()
    print(f"=============== current =================\n\n\n{data}\n\n\n================================")



    current           = data.get("current")
    time_stamp        = data.get("time_stamp")
    socket_name       = data.get("socket_name")
    current_std       = data.get("current_std")
    current_max       = data.get("current_max")
    current_min       = data.get("current_min")
    rate_of_change    = data.get("rate_of_change")

    if socket_name == 'A':
        saving_the_data("A_socket_report", current, current_std, current_max, current_min, rate_of_change, time_stamp)
        
    elif socket_name == 'B':
        saving_the_data("B_socket_report", current, current_std, current_max, current_min, rate_of_change, time_stamp)

    elif socket_name == 'C':
        saving_the_data("C_socket_report", current, current_std, current_max, current_min, rate_of_change, time_stamp)

    else:
        return jsonify({'status': 'invalid socket name'}), 400


    with open('current_model.pkl', 'rb') as f:
        
        model = pickle.load(f)
        input_data = [[current, current_std, current_max, current_min, rate_of_change]]
        prediction = model.predict(input_data)

        # 0: SAFE
        # 1: DANGEROUS

        if prediction == 1:
        
            reply = dis_or_connect_the_socket(socket_name, RASPBERRY_PI_link, 0)
            
            line_bot_api.push_message(
                
                to='', 
                messages=TemplateSendMessage(
                    
                    alt_text='電流異常警告',
                    template=ButtonsTemplate(
                        
                        title='警告：電流異常',
                        text=f'該插座目前電流為 {current:.2f} 安培，已超出正常範圍，系統將執行斷電保護。',
                        actions=[
                            
                            MessageAction(
                                label='重新接通插座',  
                                text='重新接通插座 ' + f'{socket_name}'),
                            
                            MessageAction(
                                label='了解，保持斷電',
                                text='保持斷電')
                            
                        ]
                    )
                )
            )
        
    return jsonify({'status': 'success'}), 200



# THIS ROUTER IS FOR RASPBERRY PI TO POST ERATHQUACK ALERT TO THE SERVER,
# AND THE SERVER WILL RUN A RISK PRIDICTION MODEL TO DETERMINE WHETHER CUT OFF ALL SOCKETS.
@app.route('/earthquake_alert', methods=['POST'])
def receive_earthquake_alert():

    data = request.get_json()
    print(f"=============== earthquake =================\n\n\n{data}\n\n\n================================")

    if not data :
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    input_data = [[ 
                        data.get('acc_mean_x'), data.get('acc_mean_y'), data.get('acc_mean_z'), 
                        data.get('acc_std_x'), data.get('acc_std_y'), data.get('acc_std_z'),
                        data.get('acc_max_x'), data.get('acc_max_y'), data.get('acc_max_z'),
                        data.get('acc_min_x'), data.get('acc_min_y'), data.get('acc_min_z'),
                        data.get('gyro_mean_x'), data.get('gyro_mean_y'), data.get('gyro_mean_z'),
                        data.get('gyro_std_x'), data.get('gyro_std_y'), data.get('gyro_std_z'),
                        data.get('total_acc_mean'), data.get('total_acc_std'), data.get('total_acc_max'),                        
                 ]]


    with open('earthquake_model.pkl', 'rb') as f:
        
        model = pickle.load(f)    
        prediction = model.predict(input_data)
        print(f"=============== earthquake_model =================\n\n\n{prediction}\n\n\n================ prediction ================")

        # 0: SAFE
        # 1: DANGEROUS

        if prediction == 1:
        
            reply1 = dis_or_connect_the_socket('A', RASPBERRY_PI_link, 0)
            reply2 = dis_or_connect_the_socket('B', RASPBERRY_PI_link, 0)
            reply3 = dis_or_connect_the_socket('C', RASPBERRY_PI_link, 0)

            line_bot_api.push_message(
                
                to='', 
                messages=TemplateSendMessage(
                    
                    alt_text='地震致災警告',
                    template=ButtonsTemplate(
                        
                        title='警告：地震侵襲致電路異常',
                        text='為預防高風險危害，\n已強制斷開所有插座。',
                        actions=[
                            MessageAction(
                                label='了解，保持斷電',  
                                text='注意安全'
                            )
                        ]
                    )
                )
            )


        else:

            line_bot_api.push_message(
                    
                    to='',  
                    messages=TemplateSendMessage(
                        
                        alt_text='非致災性地震提醒',
                        template=ButtonsTemplate(
                            
                            title='提醒：雖有地震侵襲，\n惟本系統判斷危害尚可容忍。',
                            text='本系統將維持既有插座通電狀態。',
                            
                            actions=[
                                MessageAction(
                                    label='點擊「查閱插座接通狀態」以檢視電路',
                                    text='小心用電'
                                )
                            ]
                        )
                    )
                )


    '''
            TO DO:
            1. TURN OFF ALL SOCKETS AFTER RECEIVING THE ALERT.(PI DO IT AUTOMATICALLY.)
               ---> PI WILL SEND ME: {'id':~, "timestamp": "2025-06-06 12:13:14", 'current_value': ~, 
                                      'accel_x':~, 'accel_y':~, 'accel_z':~, 'gyro_x':~, 'gyro_y':~, 'gyro_z':~, 
                                      'earthquake_detected':~, 'anomaly_detected':~}

            2. PLUG THE 21 FEATURES INTO THE PREDICTION MODEL.
            3. INFORM THE USER VIA LINEBOT:

                3-1: RISK IS OKEY: JUST REMIND THE USER THAT AN EARTHQUACK JUST HAPPEN,
                                   AND THEN TURN ON THE SOCKETS BACK TO THE ORIGINAL STATE VIA MY FLASK.
    
                                   ---> dis_or_connect_the_socket(socket_name, PI_url, mode):
                                        # mode == 1 : CONNECT
                                        # mode == 0 : DISCONNECT


                3-2: RISK IS HUGE: WHILE SHOWING THE INFORMATION OF THE EARTHQUACK, 
                                   TELL THE USER ALL THE SOCKETS ALL CUT OFF IN CASE.
                                   
                                   IF THE USER WANT TO REBOOT THE SOCKET(S),
                                   JUST ASK THE USER START FROM THE RICH MENU. 
    '''

    return jsonify({'status': 'success'}), 200



if __name__ == '__main__':
    app.run(debug=True)