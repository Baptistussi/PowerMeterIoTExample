BROKER = "broker.hivemq.com"            
PORT = 1883                           
KEEP_ALIVE = 60

TOPICS = {
    'devices_lobby'     :   'IoTPM/d2s/lobby',
    'device_feedback'   :   'IoTPM/d2s/{device_id}/feedback',
    'device_data'       :   'IoTPM/d2s/{device_id}/data',
    'server_control'    :   'IoTPM/s2d/{device_id}/control',
    'server_feedback'   :   'IoTPM/s2d/{device_id}/feedback'
}