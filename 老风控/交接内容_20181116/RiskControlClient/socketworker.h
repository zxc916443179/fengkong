#ifndef SOCKETWORKER_H
#define SOCKETWORKER_H

#include <QObject>
#include <QThread>
#include <QTime>
#include <Qtimer>
#include <QTcpSocket>
#include <QJsonValue>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonDocument>

class SocketWorker : public QObject
{
    Q_OBJECT
public:
    explicit SocketWorker(QObject *parent = nullptr);
    void setIp(QString iip){ip=iip;}
    void setPort(int iport){port = iport;}
    void run();
    void initTimer(int msec);

signals:
    void refresh(QStringList data1, QStringList data2);

public slots:
    void readData();
    void initSocket();

private:
    QString ip;
    int port;
    bool connected;
    QTcpSocket *socket;
    QTime lastUpdate;
    QTimer * timer;
};

#endif // SOCKETWORKER_H
