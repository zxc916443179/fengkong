#-------------------------------------------------
#
# Project created by QtCreator 2018-07-20T15:24:38
#
#-------------------------------------------------

QT       += core gui network

RC_ICONS = rcc256_X9m_icon.ico

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = RiskControlClient
TEMPLATE = app


SOURCES += main.cpp\
        mainwindow.cpp \
    my_model.cpp \
    detaildialog.cpp \
    socketworker.cpp

HEADERS  += mainwindow.h \
    my_model.h \
    detaildialog.h \
    socketworker.h

FORMS    += mainwindow.ui \
    detaildialog.ui

DISTFILES += \
    rcc256_X9m_icon.ico \
    app.rc \
    rcc.ini

RESOURCES = app.qrc \
    app.qrc

RC_FILE = app.rc

