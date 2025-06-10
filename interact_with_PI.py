import sqlite3
import requests

def checking_the_sockets(pi_link):
        
        try:
            response = requests.post(pi_link+'/check_sockets', timeout = 3)
            
            if response.status_code == 200:
                return response.json()           
            else:
                return {"ERROR": f"status_code: {response.status_code}"}
        
        except requests.exceptions.RequestException as e:
             return {'ERROR': f"EXCEPTION: {e}"}
            
        '''
            請回傳資料型態為: sockets = {"A_socket":"ON", "B_socket":"OFF", "C_socket":"ON"}
        '''

def saving_the_data(table_name, current, current_std, current_max, current_min, rate_of_change, time_stamp):

        '''
            RASPBERRY PI 需要每 5 秒就回傳有接通得插座的電流狀態，(我這裡伺服器的router為/receive_data)，
            Server 會將這些資訊存入到相對應的 table 裡面
        '''
        conn = sqlite3.connect("C:\\Hello Alex\\VScode\\Codes\\python\\Flask\\current_state_report.db")
        cursor = conn.cursor()

        sql = f"INSERT INTO {table_name} (current, current_std, current_max, current_min, rate_of_change, time_stamp) VALUES (?, ?, ?, ?, ?, ?)"
        cursor.execute(sql, (current, current_std, current_max, current_min, rate_of_change, time_stamp))
        conn.commit()
        conn.close()


def dis_or_connect_the_socket(socket_name, PI_url, mode):
    
    # mode == 1 : CONNECT
    # mode == 0 : DISCONNECT

    payload = {'target': socket_name, 'mode': mode} 

    try:
        response = requests.post(PI_url+"/switch", json=payload, timeout=5)
        return response.json()
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

