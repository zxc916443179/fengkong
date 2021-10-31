from math import acos, pi, sin, cos
import math
from random import randint, uniform
import logging

logger = logging.getLogger()


class Random(object):
    @classmethod
    def randint(cls, a, b, size=1):
        # type : (int, int, int) -> list[int]
        ret = []
        for i in xrange(size):
            t = randint(a, b)
            if t not in ret:
                ret.append(t)
            if len(ret) == size:
                break
        return ret

    @classmethod
    def rand(cls, seed):
        seed = seed * 1103515245 + 12345
        return (seed / 65536) % 32768

    # average strike rate in the minimum range of  must hit
    @classmethod
    def arr(cls, c):
        d_p = 0.0
        d_success_p = 0.0
        d_pe = 0.0
        maxfil = int(math.ceil(1 / c))
        for i in range(maxfil):
            d_p = (min(1.0, (i + 1) * c)) * (1 - d_success_p)
            d_success_p += d_p
            d_pe += (i + 1) * d_p
        return 1.0 / d_pe

    @classmethod
    def prdC(cls, p):
        d_max = p
        d_min = 0.0
        d_mid = p
        d_last = 1.0
        while 1:
            d_mid = (d_max + d_min) / 2.0
            d_test = cls.arr(d_mid)
            if math.fabs(d_test - d_last) <= 0.0001:
                break
            if d_test > p:
                d_max = d_mid
            else:
                d_min = d_mid
            d_last = d_test
        return d_mid

    @classmethod
    def randPosition(cls, position_start, position_end, r):
        # type: (Vector3, Vector3, float) -> Vector3
        angle = Collide.rayDir(position_end, position_start)
        angle = angle + uniform(0, 180) - 90
        # r = uniform(r / 10, r / 2)
        x = sin(angle * pi / 180.0)
        z = cos(angle * pi / 180.0)
        forward = Vector3(x * r, 0, z * r)
        position = Vector3(position_end.x, position_end.y, position_end.z)
        position.add(forward)
        return position


class Collide(object):
    @classmethod
    def angleDiffer(cls, a, b, angle, distance, r):
        esc_angle = angle + math.degrees(math.atan2(r, distance ** 1 / 2))
        a_min = ((a - esc_angle) + 360) % 360
        a_max = ((a + esc_angle) + 360) % 360
        b = (b + 360) % 360
        if a_max < a_min:
            if b <= a_max or b >= a_min:
                return 1
        if a_max >= b >= a_min:
            return 1
        return 0

    @classmethod
    def angleEquals(cls, a, b, distance, r):
        distance = distance ** 0.5
        if distance <= r:
            return 1
        else:
            esc_angle = math.degrees(math.asin(r / distance))
        a_min = ((a - esc_angle) + 360) % 360
        a_max = ((a + esc_angle) + 360) % 360
        b = (b + 360) % 360
        if a_max < a_min:
            if b <= a_max or b >= a_min:
                return 1
        if a_max >= b >= a_min:
            return 1
        return 0

    @classmethod
    def rayDir(cls, begin_position, end_position):
        begin_position = Vector3(begin_position.x, 0, begin_position.z)
        end_position = Vector3(end_position.x, 0, end_position.z)
        if Vector3.Distance(begin_position, end_position) <= 0.001 ** 2:
            return -1
        x = end_position.x - begin_position.x
        z = end_position.z - begin_position.z
        cos_angle = z / math.sqrt(z * z * 1.0 + x * x * 1.0)
        dir_true = math.acos(cos_angle) / math.pi * 180
        if x < 0:
            dir_true = -dir_true
        return dir_true

    @classmethod
    def trigger(cls, position1, position2, r):
        ESP = 0.5
        if Vector3.Distance(position1, position2) <= r ** 2 + ESP:
            return 1
        return 0

    @classmethod
    def list_check(cls, maps, x, y):
        if x < 0 or x >= len(maps):
            return 0
        else:
            if y < 0 or y >= len(maps[x]):
                return 0
            return 1

    @classmethod
    def cross(cls, start_x, start_y, angle, maps, distance, ):
        rem_pos = [start_x, start_y]
        angle = 360 - ((angle - 90 + 360) % 360)
        angle = (angle + 360) % 360
        dis = 0
        if angle == 90:
            x = int(math.floor(start_x))
            y = int(math.floor(start_y))
            while dis < distance ** 2:
                y = y + 1
                dis = (y + 0.5 - start_y) ** 2
                if cls.list_check(maps, x, y) <= 0:
                    return []
                if maps[x][y] == 1:
                    return rem_pos
                rem_pos[1] = y + 0.5
            return rem_pos
        elif angle == 270:
            x = int(math.floor(start_x))
            y = int(math.ceil(start_y))
            while dis <= distance ** 2:
                y = y - 1
                dis = (y - 0.5 - start_y) ** 2
                if cls.list_check(maps, x, y) <= 0:
                    return []
                if maps[x][y] == 1:
                    return rem_pos
                rem_pos[1] = y - 0.5
            return rem_pos
        else:
            k = math.tan(math.radians(angle))
        b = start_y - k * start_x
        if k >= 0:
            if 90 >= angle >= 0:
                x_int = int(math.floor(start_x))
                y_int_max = int(math.ceil(start_y))
                x_int = x_int - 0.5

                while dis < (distance ** 2):
                    x_int = x_int + 1
                    y_int_min = y_int_max - 1
                    dis = ((k * x_int + b) - start_y) ** 2 + (x_int - start_x) ** 2
                    y_int_max = int(math.ceil(k * x_int + b))
                    for y in range(y_int_min, y_int_max):
                        if cls.list_check(maps, int(math.floor(x_int)), y) <= 0:
                            return []
                        if maps[int(math.floor(x_int))][y] == 1:
                            if y == y_int_min:
                                rem_pos[0] = x_int - 1
                                rem_pos[1] = k * (x_int - 1) + b
                            else:
                                rem_pos[1] = y - 0.5
                                rem_pos[0] = ((y - 0.5) - b) / k
                            return rem_pos
            else:
                x_int = int(math.ceil(start_x))
                y_int_min = int(math.floor(start_y))
                x_int = x_int + 0.5

                while dis < (distance ** 2):
                    x_int = x_int - 1
                    y_int_max = y_int_min + 1
                    dis = ((k * x_int + b) - start_y) ** 2 + (x_int - start_x) ** 2
                    y_int_min = int(math.floor(k * x_int + b))
                    for y in range(y_int_max, y_int_min, -1):
                        if cls.list_check(maps, int(math.ceil(x_int)), y) <= 0:
                            return []
                        if maps[int(math.ceil(x_int))][y] == 1:
                            if y == y_int_max:
                                rem_pos[0] = x_int + 1
                                rem_pos[1] = k * (x_int + 1) + b
                            else:
                                rem_pos[1] = y + 0.5
                                rem_pos[0] = ((y + 0.5) - b) / k
                            return rem_pos
        else:
            if 90 <= angle <= 180:
                x_int = int(start_x + 0.5)
                y_int_max = int(start_y + 0.5)
                x_int = x_int + 0.5

                while dis < (distance ** 2):
                    x_int = x_int - 1
                    y_int_min = y_int_max - 1
                    dis = ((k * x_int + b) - start_y) ** 2 + (x_int - start_x) ** 2
                    y_int_max = int(math.ceil(k * x_int + b))
                    for y in range(y_int_min, y_int_max):
                        if cls.list_check(maps, int(math.ceil(x_int)), y) <= 0:
                            return []
                        if maps[int(math.ceil(x_int))][y] == 1:
                            if y == y_int_min:
                                rem_pos[0] = x_int + 1
                                rem_pos[1] = k * (x_int + 1) + b
                            else:
                                rem_pos[1] = y - 0.5
                                rem_pos[0] = ((y - 0.5) - b) / k
                            return rem_pos
            else:
                x_int = int(math.floor(start_x))
                y_int_min = int(math.floor(start_y))
                x_int = x_int - 0.5

                while dis < (distance ** 2):
                    x_int = x_int + 1
                    y_int_max = y_int_min + 1
                    dis = ((k * x_int + b) - start_y) ** 2 + (x_int - start_x) ** 2
                    y_int_min = int(math.floor(k * x_int + b))
                    for y in range(y_int_max, y_int_min, -1):
                        if cls.list_check(maps, int(math.floor(x_int)), y) <= 0:
                            return []
                        if maps[int(math.floor(x_int))][y] == 1:
                            if y == y_int_max:
                                rem_pos[0] = x_int - 1
                                rem_pos[1] = k * (x_int - 1) + b
                            else:
                                rem_pos[1] = y + 0.5
                                rem_pos[0] = ((y + 0.5) - b) / k
                            return rem_pos

        return []


class Vector3:
    def __init__(self, x=0.0, y=0.0, z=0.0, from_dict=None):
        if from_dict is not None:
            self.x = from_dict["x"]
            self.y = from_dict["y"]
            self.z = from_dict["z"]
            return
        self.x = x
        self.y = y
        self.z = z

    def add(self, vector):
        self.x += vector.x
        self.y += vector.y
        self.z += vector.z

    def multiply(self, vector):
        if isinstance(vector, Vector3):
            self.x *= vector.x
            self.y *= vector.y
            self.z *= vector.z
        else:
            self.x *= vector
            self.y *= vector
            self.z *= vector

    def subtract(self, vector):
        # type: (Vector3) -> Vector3
        self.x -= vector.x
        self.y -= vector.y
        self.z -= vector.z

    @classmethod
    def cross(cls, a, b):
        # type:(Vector3, Vector3) -> Vector3
        return Vector3(a.y * b.z - b.y * a.z, b.x * a.z - a.x * b.z, a.x * b.y - b.x * a.y)

    @classmethod
    def forward(cls):
        return Vector3(0, 0, 1)

    @classmethod
    def back(cls):
        return Vector3(0, 0, -1)

    @classmethod
    def left(cls):
        return Vector3(-1, 0, 0)

    @classmethod
    def right(cls):
        return Vector3(1, 0, 0)

    def getDict(self):
        return {"x": round(self.x, 1), "y": round(self.y, 1), "z": round(self.z, 1)}

    @classmethod
    def Distance(cls, a, b):
        """
        calculate distance from A to B
        """
        return (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2

    @classmethod
    def Angle(cls, a, b):
        """
        calculate angle degree between vector a and vector b
        """
        if isinstance(a, Vector3):
            dot = a.x * b.x + a.y * b.y + a.z * b.z
            a_mag = a.x ** 2. + a.y ** 2. + a.z ** 2.
            a_mag = a_mag ** 0.5

            b_mag = b.x ** 2. + b.y ** 2. + b.z ** 2.
            b_mag = b_mag ** 0.5
            cos = dot / (a_mag * b_mag)
            cos = max(-1., cos)
            cos = min(1., cos)
            return acos(cos)
        else:
            dot = a["x"] * b["x"] + a["y"] * b["y"] + a["z"] * b["z"]
            a_mag = a["x"] ** 2. + a["y"] ** 2. + a["z"] ** 2.
            a_mag = a_mag ** 0.5

            b_mag = b["x"] ** 2. + b["y"] ** 2. + b["z"] ** 2.
            b_mag = b_mag ** 0.5

            cos = dot / (a_mag * b_mag)

            cos = min(-1., cos)
            cos = max(1., cos)
            return acos(cos)

    @classmethod
    def Lerp(cls, a, b, t):
        vec = Vector3()
        vec.x = a.x + t * (b.x - a.x)
        vec.y = a.y + t * (b.y - a.y)
        vec.z = a.z + t * (b.z - a.z)
        return vec

    @classmethod
    def Add(cls, a, b):
        return Vector3(a.x + b.x, a.y + b.y, a.z + b.z)


class Transform:
    def __init__(self, position, rotation):
        # type: (Vector3, Vector3) -> None
        self.position = position
        self.rotation = rotation

    def translate(self, motion):
        self.position.add(motion)

    def forward(self):
        x = sin(self.rotation.y * pi / 180.0)
        z = cos(self.rotation.y * pi / 180.0)
        return Vector3(x, 0, z)

    def rotate(self, rotation):
        self.rotation.add(rotation)

    def getDict(self):
        return {"position": self.position.getDict(), "rotation": self.rotation.getDict()}
