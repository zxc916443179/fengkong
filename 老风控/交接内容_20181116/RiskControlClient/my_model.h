#ifndef MY_MODEL_H
#define MY_MODEL_H

#include <QAbstractTableModel>
#include <QBrush>

class BriefModel : public QAbstractTableModel
{
    Q_OBJECT
public:
    BriefModel(QObject *parent=0);
    void setBrief(const QStringList &b);
    int rowCount(const QModelIndex &parent = QModelIndex()) const Q_DECL_OVERRIDE ;
    int columnCount(const QModelIndex &parent = QModelIndex()) const Q_DECL_OVERRIDE;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const Q_DECL_OVERRIDE;
    QVariant headerData(int section, Qt::Orientation o, int role) const Q_DECL_OVERRIDE;
private:
    QStringList brief;
};


class DetailModel : public QAbstractTableModel
{
    Q_OBJECT
public:
    DetailModel(QObject *parent=0);
    void setDetail(const QStringList &d);
    int rowCount(const QModelIndex &parent = QModelIndex()) const Q_DECL_OVERRIDE ;
    int columnCount(const QModelIndex &parent = QModelIndex()) const Q_DECL_OVERRIDE;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const Q_DECL_OVERRIDE;
    QVariant headerData(int section, Qt::Orientation o, int role) const Q_DECL_OVERRIDE;
private:
    QStringList detail;
};

#endif // MY_MODEL_H
