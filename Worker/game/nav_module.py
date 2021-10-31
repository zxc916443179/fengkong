from common_server.data_module import DataCenter
from common.common_library_module import Singleton


class Point:
    def __init__(self, x, y, father=None, g=0):
        self.x = int(x)
        self.y = int(y)
        self.father = father
        self.f = 0
        self.g = g
        self.h = 0

    @classmethod
    def getPoint(cls, points, x, y):
        try:
            return next((point for point in points if point.x == x and point.y == y))
        except StopIteration:
            return None

    @classmethod
    def getMinFPointAndRemove(cls, points):  # get min f point and delete from open list
        if len(points) == 0:
            return None
        t = points[0]
        for p in points:
            if p.f < t.f:
                t = p
        points.remove(t)
        return t

    @classmethod
    def calH(cls, start, end):
        return abs(start.x - end.x) + abs(start.y - end.y)

    @classmethod
    def getAroundPoint(cls, point, dst, top, left, bottom, right, close_list, open_list, map_info, walkList):  # get around points
        around = [[point.x, point.y - 1, 1], [point.x, point.y + 1, 1], [point.x - 1, point.y - 1, 1],
                  [point.x - 1, point.y + 1, 1],
                  [point.x - 1, point.y, 1], [point.x + 1, point.y - 1, 1], [point.x + 1, point.y, 1],
                  [point.x + 1, point.y + 1, 1]]
        for p in around[::-1]:
            if p[0] >= right or p[0] < left or p[1] > bottom or p[1] <= top or p in close_list or not map_info[p[0]][p[1]] in walkList:
                # determine p is inside map and p is not wall and p not in close list
                around.remove(p)
        for t in around:
            p = Point.getPoint(open_list, t[0], t[1])
            if p is not None:
                # if p in open list, cal new F value
                new_G = point.g + t[2]
                new_H = Point.calH(p, dst)
                new_F = new_G + new_H
                if new_F > p.f:
                    p.f = new_F
                    p.g = t[2]
                    p.father = point
                    p.h = new_H
            else:
                # create new p and append to open list
                p = Point(t[0], t[1], point, t[2])
                p.h = Point.calH(p, dst)
                p.f = p.g + p.h
                open_list.append(p)
        return open_list

    def __str__(self):
        return "x:" + str(self.x) + " y:" + str(self.y)


@Singleton
class NavAgent(object):
    def __init__(self):
        self.data_center = DataCenter()
        self.map = []
        self.height = 0
        self.width = 0

    def SetDestination(self, start, end, room_id, step=None, walkList=None):
        room = self.data_center.getRoom(room_id)
        self.map = room.currentMap.mapList
        top = 0
        left = 0
        bottom = len(self.map)
        right = len(self.map[0])
        if walkList is None:
            walkList = [0]
        startPoint = Point(start.x - room.currentMap.left, start.z + room.currentMap.top)
        endPoint = Point(end.x - room.currentMap.left, end.z + room.currentMap.top)
        result = self._AStar(startPoint, endPoint, top, left, bottom, right, walkList, step)
        return result

    def _AStar(self, start_point, end_point, top, left, bottom, right, walkList, step=None):
        openList = [start_point]
        closeList = []
        resultList = []
        steps = 0
        while len(openList) > 0:
            cur = Point.getMinFPointAndRemove(openList)
            if cur.x == end_point.x and cur.y == end_point.y or step is not None and steps == step:
                resultList.append(cur)
                while True:
                    cur = cur.father
                    if cur is None:
                        break
                    resultList.append(cur)
                break
            # append to close list
            closeList.append([cur.x, cur.y])
            # calculate around points
            openList = Point.getAroundPoint(cur, end_point, top, left, bottom, right, closeList, openList, self.map, walkList)
            steps += 1
        return resultList
