from linebot import WebhookHandler, LineBotApi
from linebot.models import (    RichMenu, RichMenuArea, RichMenuBounds,\
                                MessageEvent, TextMessage, TextSendMessage,\
                                TemplateSendMessage, ButtonsTemplate, MessageAction, ImageSendMessage   )

import sqlite3
import statistics
from datetime import datetime
import matplotlib.pyplot as plt


def socket_status_menu(status):

    return TemplateSendMessage(

        alt_text = "通電狀態回傳：",
        
        template=ButtonsTemplate(
            title= "插座狀態",
            text = "請選擇要查詢的插座",
            
            actions = [
                        MessageAction(
                            label=f"A 插座為： {status['A_socket']}", 
                            text="列印 A 插座近期狀態" if status['A_socket'] == 'ON' else "接通A插座（請確保已經有插座連通於上）"),
                        
                        MessageAction(
                            label=f"B 插座為： {status['B_socket']}", 
                            text="列印 B 插座近期狀態" if status['B_socket'] == 'ON' else "接通B插座（請確保已經有插座連通於上）"),
                        
                        MessageAction(
                            label=f"C 插座為： {status['C_socket']}", 
                            text="列印 C 插座近期狀態" if status['C_socket'] == 'ON' else "接通C插座（請確保已經有插座連通於上）")
                      ] 
        )
    )

    
def analysis_of_recent_status_for_plotting(table_name):

    conn = sqlite3.connect("", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute(f'''
        SELECT time_stamp, current 
        FROM {table_name} 
        ORDER BY time_stamp DESC 
        LIMIT 20
    ''')
    
    rows = cursor.fetchall()
    
    if not rows:
        print("資料表中無資料。")
        return
    
    rows = list(reversed(rows))  # MAKE IT ASCEND
    
    currents   = [float(row[1]) for row in rows]
    timestamps = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in rows]

    avg = round(statistics.mean(currents), 2)
    std = round(statistics.stdev(currents), 2)

    plt.figure(figsize=(10, 4))
    plt.plot(timestamps, currents, marker='o', linestyle='-', color='blue')
    plt.xlabel("Time")
    plt.ylabel("Current (A)")
    plt.title("Line Chart of the Latest 20 Current Values:")

    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    timestamp_str = timestamps[0].strftime("%Y%m%d_%H%M%S")
    fig_path = f''
    
    plt.savefig(fig_path)
    plt.close()

    print(f"圖表已儲存：{fig_path}")
    print(f"平均電流：{avg} 安培, 標準差：{std} 安培")

    conn.close()

    return avg, std, f'recent_current_plot_{timestamp_str}.png'


def identify_the_target_socket(user_input):

        if 'A' in user_input:
                return 'A'
        elif 'B' in user_input:
                return 'B'
        elif 'C' in user_input:
                return 'C'
        else:
            return "Invaild situation! Try again!"


