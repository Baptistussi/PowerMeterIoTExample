BROKER = "broker.hivemq.com"            
PORT = 1883                           
KEEP_ALIVE = 60

TOPICS = {
    'devices_lobby'     :   'IoTPM/d2s/lobby',
    'device_data'       :   'IoTPM/d2s/data/{device_id}',
    'device_feedback'   :   'IoTPM/d2s/feedback/{device_id}',
    'server_control'    :   'IoTPM/s2d/control/{device_id}',
    #'server_feedback'   :   'IoTPM/s2d/feedback/{device_id}'
}