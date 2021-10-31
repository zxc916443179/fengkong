// Copyright 2018 Chen Kaixiang <pythonshell@yeah.net>
// Author: Chen Kaixiang
// Date: 2018-08-10
// RiskControlClient main entry

/* STL */
#include <iostream>

/* QT5 */
#include <QApplication>
#include <QCommandLineOption>
#include <QCommandLineParser>
#include <QSettings>
#include <QDir>
#include <QMessageLogger>
#include <QTime>
#include <QTimer>
#include <QThread>

/* Project */
#include "my_model.h"
#include "mainwindow.h"
#include "socketworker.h"


FILE* LOG_FILE=0;


/**
 * @brief 重定向日志
 * @param tp: 日志级别
 * @param msg: 日志内容
 */
void myMessageHandler(QtMsgType tp, const QMessageLogContext &context, const QString &msg)
{
    QTime time = QDateTime::currentDateTime().toUTC().time();
    QString txtMessage;
    switch(tp)
    {
    case QtDebugMsg:
        txtMessage = QString("[%1|DEBUG] %2").arg(time.toString("HH:mm:ss.zzz")).arg(msg);
        break;
    case QtWarningMsg:
        txtMessage = QString("[%1|WARN] %2").arg(time.toString("HH:mm:ss.zzz")).arg(msg);
        break;
    case QtCriticalMsg:
        txtMessage = QString("[%1|ERROR] %2").arg(time.toString("HH:mm:ss.zzz")).arg(msg);
        break;
    case QtFatalMsg:
        txtMessage = QString("[%1|FATAL] %2").arg(time.toString("HH:mm:ss.zzz")).arg(msg);
        abort();
    default:
        txtMessage = QString("[%1|UNKNOWN] %2").arg(time.toString("HH:mm:ss.zzz")).arg(msg);
    }
    QByteArray logMsgBytes = txtMessage.toUtf8();
    fwrite(logMsgBytes.constData(), 1, logMsgBytes.size(), stderr);
    if (!LOG_FILE)
    {
        LOG_FILE = fopen("rcc.log", "a");
        //if(LOG_FILE->open(QIODevice::WriteOnly | QIODevice::Append)) {
            fwrite(logMsgBytes.constData(), 1, logMsgBytes.size(), LOG_FILE);
            fflush(LOG_FILE);
        //}
    }
    else
    {
        fwrite(logMsgBytes.constData(), 1, logMsgBytes.size(), LOG_FILE);
        fflush(LOG_FILE);
    }
}


int main(int argc, char *argv[])
{
    qInstallMessageHandler(myMessageHandler);
    QSettings settings("rcc.ini",QSettings::IniFormat);
    settings.setIniCodec("UTF-8");

    int port = settings.value("server/port", 50123).toInt();
    QString ip = settings.value("server/ip", "127.0.0.1").toString();
    QString name = settings.value("server/name", "TEST").toString();

    qDebug() << "Current Path: " << QDir::currentPath() << "\n";
    qDebug() << name << " " << ip << " " << port << "." << "\n";
    //std::cout << name.toStdString() << " " << ip.toStdString() << ":" << port << "." << std::endl;

    QApplication a(argc, argv);
    QString version = "0.1";
    //"PythonShellWorkshop", "RiskControlClient"
    a.setApplicationName("RiskControlClient");
    a.setApplicationVersion(version);

    /*
    int num = -1;
    QCommandLineParser parser;

    parser.addHelpOption();
    parser.addVersionOption();

    QCommandLineOption numOption("n", "The number argument", "number", "1");
    QCommandLineOption ipOption("ip", "The ip rcc listen", "ip", "127.0.0.1");
    parser.addOption(numOption);
    parser.addOption(ipOption);

    parser.process(a);

    num = parser.value(numOption).toInt();
    qDebug("Hello Qt World! Version: %s.", version.toStdString());
    qDebug("Hello Qt World! Number: %d.", num);
    */

    MainWindow w;

    QThread queryThread;
    queryThread.start();

    SocketWorker myworker;
    myworker.moveToThread(&queryThread);

    myworker.setIp(ip);
    myworker.setPort(port);
    myworker.initSocket();
    QObject::connect(&myworker, SocketWorker::refresh, &w, w.refresh);

    // start get data
    QTimer timer(&w);
    //timer.moveToThread(&queryThread);
    timer.setInterval(1000);
    QObject::connect(&timer, QTimer::timeout, &myworker, myworker.readData);
    timer.start();

    w.show();

    //myworker.run();

    /*
    TraderProfitModel traderProfitModel(0);
    MyModel myModel(0);
    QTableView tableView;
    tableView.setModel( &traderProfitModel );
    tableView.setModel( &myModel );
    tableView.show();
    */

    return a.exec();
}
