#!/usr/bin/env pybricks-micropython

'''
LEGO® MINDSTORMS® EV3 Communication
-----------------------------------

This program requires LEGO® EV3 MicroPython v2.0.
Download: https://education.lego.com/en-us/support/mindstorms-ev3/python-for-ev3
'''

from pybricks.messaging import BluetoothMailboxServer, BluetoothMailboxClient, TextMailbox
from threading import Thread

msgs = {
    'READY': False,
    'STOP': False,
    'SLOW': False,
    'GO': False,
    'RELEASE_GRIP': False,
    'READY_TO_DROP': False,
}


class Communication:
    def __init__(self, id_receiver, id_sender, connection):
        input_mailbox = id_sender + '_to_' + id_receiver
        output_mailbox = id_receiver + '_to_' + id_sender

        self.data_in = TextMailbox(input_mailbox, connection)
        self.data_out = TextMailbox(output_mailbox, connection)

        self.msgs_in = msgs.copy()
        self.msgs_out = msgs.copy()

        self.made_bt_connection = False

    def send(self, msg):
        if msg in self.msgs_out:
            print('msg_out: ', msg, ' = True')
            self.msgs_out[msg] = True
        else:
            print('msg_out_not_valid: ', msg)

    def receive(self, msg, default_bool=True):
        if not self.made_bt_connection:
            return default_bool
        else:
            if msg in self.msgs_in:
                if self.msgs_in.get(msg):
                    print('msg_in: ', msg, ' = True')
                    self.msgs_in[msg] = False
                    return True
                else:
                    return False
            else:
                print('msg_in_not_valid: ', msg)

    def receive_msgs(self):
        while True:
            self.data_in.wait()
            msg = self.data_in.read()
            if msg in self.msgs_in:
                print('receive: ', msg)
                self.msgs_in[msg] = True
            else:
                print('error_receive', msg)

    def send_msgs(self):
        while True:
            for msg in self.msgs_out.keys():
                if self.msgs_out[msg]:
                    print('send: ', msg)
                    self.data_out.send(msg)
                    self.msgs_out[msg] = False
                wait(500)

    def run(self):
        self.made_bt_connection = True
        t1 = Thread(target=self.receive_msgs)
        t2 = Thread(target=self.send_msgs)
        t1.start()
        t2.start()


class Client_Comm(Communication):
    def __init__(self, id_client, id_server):
        self.client = BluetoothMailboxClient()
        super().__init__(id_client, id_server, self.client)

    def connect(self, server):
        print('establishing connection...')
        self.client.connect(server)
        print('connected!')
        super().run()


class Server_Comm(Communication):
    def __init__(self, id_server, id_client):
        self.server = BluetoothMailboxServer()
        super().__init__(id_server, id_client, self.server)

    def wait_for_connection(self):
        print('waiting for connection...')
        self.server.wait_for_connection()
        print('connected!')
        super().run()
