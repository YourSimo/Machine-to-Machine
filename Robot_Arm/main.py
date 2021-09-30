#!/usr/bin/env pybricks-micropython

'''
LEGO® MINDSTORMS® EV3 Robot Arm 
-------------------------------

This program requires LEGO® EV3 MicroPython v2.0.
Download: https://education.lego.com/en-us/support/mindstorms-ev3/python-for-ev3

Building instructions can be found at:
link https://rebrickable.com/mocs/MOC-88944/YourSimo/robot-arm/
'''

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, TouchSensor, ColorSensor
from pybricks.parameters import Port, Stop, Direction, Button, Color
from pybricks.tools import wait, StopWatch, DataLog
from pybricks.media.ev3dev import SoundFile, ImageFile

from communication import Client_Comm

# define maximum motor speed and acceleration
SWING_SPEED = 200
MAX_SPEED = 200
MAX_ACC = 200

# Define the three destinations for picking up and moving the item.
LEFT = 180
MIDDLE = 90
RIGHT = 0

RAISE = 0
HIGH = -25
LOW = -55

LIFT_SPEED = 100

GRIPPER_SPEED = 200
GRIPPER_OPEN = -90
TOLL = 2

brick_size = 0
wrong_item = False


# Establish BT Connection
CLIENT_ID = 'arm'
SERVER_ID = 'cvr'

SERVER = 'ev3-conveyor'

client = Client_Comm(CLIENT_ID, SERVER_ID)

# Initialize the EV3 Brick
ev3_arm = EV3Brick()

# Configure the gripper motor on Port A with default settings.
gripper_motor = Motor(Port.A)

# Configure the elbow motor.
# It has an 8-teeth and a 40-teeth gear connected to it.
# We would like positive speed values to make the arm go upward.
# This corresponds to counterclockwise rotation of the motor.
elbow_motor = Motor(Port.B, Direction.COUNTERCLOCKWISE, [8, 40])

# Configure the motor that rotates the base.
# It has a 12-teeth and a 36-teeth gear connected to it.
# We would like positive speed values to make the arm go away from the Touch Sensor.
# This corresponds to counterclockwise rotation of the motor.
base_motor = Motor(Port.C, Direction.COUNTERCLOCKWISE, [12, 36])

# Limit the elbow and base accelerations.
# This results in very smooth motion. Like an industrial robot.
elbow_motor.control.limits(speed=MAX_SPEED, acceleration=MAX_ACC)
base_motor.control.limits(speed=MAX_SPEED, acceleration=MAX_ACC)

# Set up the Touch Sensor.
# It acts as an end-switch in the base of the robot arm.
# It defines the starting point of the base.
base_sensor = TouchSensor(Port.S4)

# Set up the Color Sensor.
# This sensor detects when the elbow is in the starting position.
# This is when the sensor sees the white beam up close.
elbow_sensor = ColorSensor(Port.S1)


class Item:
    def __init__(self, brick_size):
        self.brick_size = brick_size


def rotate_to(speed, pos):
    base_motor.run_target(speed, pos)


def lift_to(speed, pos):
    elbow_motor.run_target(speed, pos)


def gripper_open():
    gripper_motor.run_target(GRIPPER_SPEED, GRIPPER_OPEN)


def gripper_close():
    return abs(gripper_motor.run_until_stalled(
        GRIPPER_SPEED, then=Stop.HOLD, duty_limit=50))


def measure_item():
    while not Button.CENTER in ev3_arm.buttons.pressed():
        pass
    lift_to(LIFT_SPEED, LOW)
    global brick_size
    brick_size = gripper_close()
    print(brick_size)
    wait(500)
    gripper_open()
    lift_to(LIFT_SPEED, RAISE)


def arm_init(pos):
    # Initialize the elbow. First make it go down for one second.
    # Then make it go upwards slowly (15 degrees per second) until
    # the Color Sensor detects the white beam. Then reset the motor
    # angle to make this the zero point. Finally, hold the motor
    # in place so it does not move.
    elbow_motor.run_time(-30, 1000)
    elbow_motor.run(30)
    while elbow_sensor.reflection() < 32:
        wait(10)
    elbow_motor.reset_angle(0)
    elbow_motor.hold()

    # Initialize the base. First rotate it until the Touch Sensor
    # in the base is pressed. Reset the motor angle to make this
    # the zero point. Then hold the motor in place so it does not move.
    base_motor.run(-40)
    while not base_sensor.pressed():
        wait(10)
    base_motor.hold()
    wait(500)
    base_motor.run_angle(30, 15, then=Stop.HOLD, wait=True)
    base_motor.reset_angle(0)
    rotate_to(40, pos)

    # Initialize the gripper. First rotate the motor until it stalls.
    # Stalling means that it cannot move any further. This position
    # corresponds to the closed position. Then rotate the motor
    # by 90 degrees such that the gripper is open.
    gripper_close()
    gripper_motor.reset_angle(0)
    gripper_open()

    measure_item()

    ev3_arm.speaker.beep()
    client.send('READY')


def arm_pick(pos):
    # This function makes the robot base rotate to the indicated position.
    # There it lowers the elbow, closes the gripper, and raises the elbow to pick up the object.

    # Rotate to the pick-up position.
    rotate_to(SWING_SPEED, pos)
    # Lower the arm.
    lift_to(LIFT_SPEED, LOW)

    # Close the gripper to grab the brick.

    try_again = True
    m = 0
    global wrong_item
    wrong_item = False
    while try_again:
        try_again = False
        for i in range(3):
            m = gripper_close()
            print(m)
            if m < brick_size - TOLL:
                ev3_arm.speaker.beep()
                gripper_open()
            elif m > brick_size + TOLL:
                wrong_item = True
                client.send('SLOW')
                break
            else:
                break

            if i == 2:
                client.send('STOP')
                lift_to(LIFT_SPEED, RAISE)
                while not Button.CENTER in ev3_arm.buttons.pressed():
                    pass
                lift_to(LIFT_SPEED, LOW)
                try_again = True

    # Raise the arm to lift the wheel stack.
    lift_to(LIFT_SPEED, RAISE)


def arm_release(pos):
    # This function makes the robot base rotate to the indicated position.
    # There it lowers the elbow, opens the gripper to release the object.
    # Then it raises its arm again.

    # Rotate to the drop-off position.
    rotate_to(SWING_SPEED, pos)
    # Lower the arm to put the item on the conveyor.
    lift_to(LIFT_SPEED, HIGH)

    client.send('READY_TO_DROP')
    wait(500)
    client.send('GO')
    # Open the gripper to release the item.
    while not client.receive('RELEASE_GRIP'):
        wait(100)
    gripper_open()
    # Raise the arm.
    lift_to(LIFT_SPEED, RAISE)


def arm_drop(pos):
    rotate_to(SWING_SPEED, pos)
    lift_to(LIFT_SPEED, LOW)
    gripper_open()
    lift_to(LIFT_SPEED, RAISE)


client.connect(SERVER)
arm_init(MIDDLE)

while not client.receive('READY'):
    pass

client.send('GO')

while True:
    if client.receive('STOP', Button.UP in ev3_arm.buttons.pressed()):
        while not client.receive('GO', Button.DOWN in ev3_arm.buttons.pressed()):
            pass
    arm_pick(MIDDLE)
    if wrong_item:
        arm_drop(RIGHT)
    else:
        arm_release(LEFT)
