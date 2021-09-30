#!/usr/bin/env pybricks-micropython

'''
LEGO® MINDSTORMS® EV3 Conveyor Belt
-----------------------------------

This program requires LEGO® EV3 MicroPython v2.0.
Download: https://education.lego.com/en-us/support/mindstorms-ev3/python-for-ev3

Building instructions can be found at:
link
'''

from pybricks.hubs import EV3Brick
from pybricks.nxtdevices import ColorSensor
from pybricks.ev3devices import Motor, TouchSensor, UltrasonicSensor
from pybricks.parameters import Port, Stop, Direction, Button, Color
from pybricks.tools import wait, StopWatch, DataLog
from pybricks.media.ev3dev import SoundFile, ImageFile
from communication import Server_Comm


# Parameters - Belt
BELT_MAX_SPEED = 500
BELT_MAX_ACC = 350

BELT_SPEED = 230
BELT_SLOW_SPEED = 50
BELT_LENGTH = 845
DISTANCE_ITEMS = 2000

# Parameters - Sorters
SORTER_SPEED = 500
SORTER_DISTANCE = [350, 800, 1000]  # Relative to sensor
SORTER_OPEN = 80
SORTER_CLOSE = 5

# Initialize the EV3 brick.
ev3_conveyor = EV3Brick()

# Initialize the motors that drive the conveyor belt and eject the items.
belt_motor = Motor(Port.A, Direction.COUNTERCLOCKWISE)
belt_motor.control.limits(speed=BELT_MAX_SPEED, acceleration=BELT_MAX_ACC)

sorting_motor_1 = Motor(Port.B, Direction.COUNTERCLOCKWISE)
sorting_motor_2 = Motor(Port.C, Direction.CLOCKWISE)
SORTING_MOTORS = [sorting_motor_1, sorting_motor_2]

# Initialize the Color Sensor.
# It is used to detect the color of the items and determine the position
# of the item relative to the position of the conveyor belt.
color_sensor = ColorSensor(Port.S4)

# The colored items are either green, red or yellow.
POSSIBLE_COLORS = [Color.GREEN, Color.RED, Color.YELLOW]
# Color.BLACK, Color.BLUE, Color.WHITE
measurements = [0 for x in POSSIBLE_COLORS]

item_list = []
item_detected = False
last_pos = 0

# Establish BT Connection
SERVER_ID = 'cvr'
CLIENT_ID = 'arm'

server = Server_Comm(SERVER_ID, CLIENT_ID)


class Item:
    def __init__(self, color, pos):
        self.color = color
        self.pos = pos


def pos_belt():
    return belt_motor.angle()


def move_sorter(number, speed, pos):
    SORTING_MOTORS[number].run_target(speed, pos, wait=True)


def color_detection():
    global measurements, item_detected
    color_detected = color_sensor.color()
    for i in range(len(POSSIBLE_COLORS)):
        if color_detected == POSSIBLE_COLORS[i]:
            measurements[i] = measurements[i] + 1
            wait(50)
            item_detected = True

    if color_detected not in POSSIBLE_COLORS and item_detected:
        j = measurements.index(max(measurements))
        measurements = [0 for x in POSSIBLE_COLORS]
        item_list.append(Item(POSSIBLE_COLORS[j], pos_belt()))
        wait(50)
        item_detected = False


def sorting_item():
    for i in range(len(item_list)-1, -1, -1):
        if check_item(item_list[i].color, item_list[i].pos):
            print(item_list[i].color)
            item_list.remove(item_list[i])


def check_item(item_color, item_pos):
    if item_color == Color.GREEN and item_pos + SORTER_DISTANCE[0] < pos_belt():
        move_sorter(0, SORTER_SPEED, SORTER_OPEN)
        return True

    elif item_color == Color.YELLOW and item_pos + SORTER_DISTANCE[1] < pos_belt():
        move_sorter(1, SORTER_SPEED, SORTER_OPEN)
        return True

    elif item_color == Color.RED and item_pos + SORTER_DISTANCE[2] < pos_belt():
        return True

    else:
        for i in range(len(SORTING_MOTORS)):
            move_sorter(i, SORTER_SPEED, SORTER_CLOSE)
        return False


def conveyor_init():
    # ev3_conveyor.light.off()
    belt_motor.reset_angle(0)

    for sorting_motor in SORTING_MOTORS:
        sorting_motor.run_time(SORTER_SPEED, 500)
        sorting_motor.run_until_stalled(-SORTER_SPEED,
                                        then=Stop.COAST, duty_limit=20)
        sorting_motor.run_angle(SORTER_SPEED, 10, then=Stop.HOLD, wait=True)
        sorting_motor.reset_angle(0)
    # ev3_conveyor.light.on(Color.GREEN)

    while not server.receive('READY'):
        pass
    server.send('READY')
    ev3_conveyor.speaker.beep()


def move_belt():
    global last_pos
    if server.receive('GO', Button.UP in ev3_conveyor.buttons.pressed()):
        belt_motor.run(BELT_SPEED)
        # ev3_conveyor.light.on(Color.GREEN)

    elif server.receive('SLOW', Button.DOWN in ev3_conveyor.buttons.pressed()):
        belt_motor.run(BELT_SLOW_SPEED)
        # ev3_conveyor.light.on(Color.YELLOW)

    elif server.receive('STOP', False):
        belt_motor.brake()
        # ev3_conveyor.light.on(Color.RED)
        # while not server.receive('GO'):
        #    pass

    if belt_motor.stalled():
        belt_motor.brake()
        # ev3_conveyor.light.on(Color.RED)
        server.send('STOP')
        wait(2000)
        server.send('GO')
        belt_motor.run(BELT_SPEED)
        # ev3_conveyor.light.on(Color.GREEN)

    if last_pos + DISTANCE_ITEMS < pos_belt():
        ev3_conveyor.speaker.beep()

        if server.receive('READY_TO_DROP'):
            server.send('RELEASE_GRIP')
            last_pos = pos_belt()

        else:
            belt_motor.brake()
            # ev3_conveyor.light.on(Color.YELLOW)
            while not server.receive('READY_TO_DROP'):
                pass
            server.send('RELEASE_GRIP')
            last_pos = pos_belt()
            # belt_motor.run(BELT_SPEED)
            # ev3_conveyor.light.on(Color.GREEN)


server.wait_for_connection()
conveyor_init()
while True:
    move_belt()
    color_detection()
    sorting_item()
