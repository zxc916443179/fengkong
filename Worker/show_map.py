import turtle as t
from PIL import Image
import math
def show_map(map,point1,point2=(0,0)):
    t.pen(speed=0)
    t.penup()
    t.tracer(False)
    length = 20
    t.screensize(canvwidth=(length+1)*len(map), canvheight=(length+1)*len(map[0]))
    init_y=(length+1)*len(map)/2
    init_x=-(length+1)*len(map[0])/2
    t.goto(init_x,init_y)
    t.pendown()
    t.seth(0)
    color=["blue","yellow","red","green","black"]
    y=init_y
    for i in map:
        for j in i:
            t.pencolor(color[j])
            t.fillcolor(color[j])
            t.begin_fill()
            t.fd(length)
            t.right(90)
            t.fd(length)
            t.right(90)
            t.fd(length)
            t.right(90)
            t.fd(length)
            t.right(90)
            t.end_fill()
            t.penup()
            t.fd(length+1)
            t.pendown()
        t.penup()
        y=y-length-1
        t.goto(init_x,y)
        t.pendown()
    t.pencolor("purple")
    t.fillcolor("purple")
    t.penup()
    t.goto(init_x+(length+1)*point1[1]+10,init_y-(length+1)*point1[0]-15)
    t.pendown()
    t.begin_fill()
    t.circle(5)
    t.end_fill()
    t.penup()
    t.pencolor("purple")
    t.fillcolor("purple")
    t.penup()
    t.goto(init_x+(length+1)*point2[1]+10,init_y-(length+1)*point2[0]-15)
    t.pendown()
    t.begin_fill()
    t.circle(5)
    t.end_fill()
    t.penup()
    img = t.getscreen()
    img.getcanvas().postscript(file="work.eps")
    im = Image.open("work.eps")
    im.show()