#include "socketworker.h"
#include <QThread>
#include <QTime>

SocketWorker::SocketWorker(QObject *parent) : QObject(parent)
{
    socket = new QTcpSocket();
    connected = false;
    lastUpdate = QTime::currentTime();
}

void SocketWorker::initSocket()
{
    socket->abort();
    //连接服务器
    socket->connectToHost(ip, port);
    //等待连接成功
    if(!socket->waitForConnected(500))
    {
        qDebug() << "Connection failed!\n";
        return;
    }
    qDebug() << "Connect successfully!\n";
    connected = true;
    lastUpdate = QTime::currentTime();
    //initTimer(1000);
}

void SocketWorker::initTimer(int msec)
{
    timer = new QTimer();
    timer->setInterval(msec);
    connect(timer, &QTimer::timeout, this, &SocketWorker::readData);
    timer->start();
}

void SocketWorker::run()
{
    while(1)
    {
        readData();
        QThread::sleep(1);
    }
}

void SocketWorker::readData()
{
    QByteArray buffer;
    //读取缓冲区数据
    if (!connected) {
        initSocket();
    }
    if (!connected) {
        return;
    }
    socket->write("ver3");
    socket->flush();
    buffer = socket->readAll();
    QTime newTime = QTime::currentTime();
    if(!buffer.isEmpty())
    {
        QString str = tr(buffer);
        QJsonDocument doc = QJsonDocument::fromJson(str.toUtf8());
        QJsonObject obj = doc.object();

        QJsonArray b = obj.value("brief").toArray();
        QJsonArray::Iterator _it = b.begin();
        QStringList brief;
        while (_it != b.end())
        {
            QString _s = _it->toString();
            brief << _s;
            _it ++;
        }

        QJsonArray d = obj.value("detail").toArray();
        _it = d.begin();
        QStringList detail;
        while(_it != d.end())
        {
            QString _s = _it->toString();
            detail << _s;
            _it ++;
        }

        emit refresh(brief, detail);
        lastUpdate = newTime;
    }
    if ((newTime.second() - lastUpdate.second()) > 3)
    {
        qDebug() << "last update is 3 seconds before\n";
        connected = false;
    }
}
