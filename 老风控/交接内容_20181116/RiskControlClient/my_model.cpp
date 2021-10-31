// my_model.cpp
#include "my_model.h"

BriefModel::BriefModel(QObject *parent)
    :QAbstractTableModel(parent)
{
}

void BriefModel::setBrief(const QStringList &b)
{
    beginResetModel();
    brief = b;
    endResetModel();
}

int BriefModel::rowCount(const QModelIndex & /*parent*/) const
{
   return brief.count() / columnCount();
}

int BriefModel::columnCount(const QModelIndex & /*parent*/) const
{
    return 5;
}

QVariant BriefModel::data(const QModelIndex &index, int role) const
{
    int _i = index.row() * columnCount() + index.column();
    switch (role) {
    case Qt::DisplayRole:
        return brief.at(_i);
    case Qt::BackgroundRole:
        if (index.column()==4 && brief.at(_i)=="***")
        {
            QBrush bg(Qt::red);
            return bg;
        }
        else if (index.column()==4 && brief.at(_i)=="**")
        {
            QBrush bg(Qt::yellow);
            return bg;
        }
        break;
    default:
        break;
    }
    return QVariant();
}

QVariant BriefModel::headerData(int section, Qt::Orientation o, int role) const
{
    if (role == Qt::DisplayRole && o == Qt::Horizontal)
    {
        switch(section)
        {
        case 0:
            return QString("交易员");
        case 1:
            return QString("落地盈亏");
        case 2:
            return QString("浮动盈亏");
        case 3:
            return QString("警示线");
        case 4:
            return QString("警示信息");
        }
        return QString("测试");
    }
    return QVariant();
}


DetailModel::DetailModel(QObject *parent)
    :QAbstractTableModel(parent)
{
}

void DetailModel::setDetail(const QStringList &d)
{
    beginResetModel();
    detail = d;
    endResetModel();
}

int DetailModel::rowCount(const QModelIndex & /*parent*/) const
{
   return detail.count() / columnCount();
}

int DetailModel::columnCount(const QModelIndex & /*parent*/) const
{
    return 11;
}

QVariant DetailModel::data(const QModelIndex &index, int role) const
{
    int _i = index.row() * columnCount() + index.column();
    switch (role) {
    case Qt::DisplayRole:
        return detail.at(_i);
    case Qt::BackgroundRole:
        if (index.column()==10 && detail.at(_i)=="***")
        {
            QBrush bg(Qt::red);
            return bg;
        }
        else if (index.column()==10 && detail.at(_i)=="**")
        {
            QBrush bg(Qt::yellow);
            return bg;
        }
        break;
    default:
        break;
    }
    return QVariant();
}

QVariant DetailModel::headerData(int section, Qt::Orientation o, int role) const
{
    if (role == Qt::DisplayRole && o == Qt::Horizontal)
    {
        switch(section)
        {
        case 0:
            return QString("多空");
        case 1:
            return QString("姓名");
        case 2:
            return QString("代码");
        case 3:
            return QString("名称");
        case 4:
            return QString("暴露头寸");
        case 5:
            return QString("现价");
        case 6:
            return QString("市值");
        case 7:
            return QString("成本金额");
        case 8:
            return QString("浮动盈亏");
        case 9:
            return QString("浮动盈亏比率(%)");
        case 10:
            return QString("警示信息");
        }
        return QString("测试");
    }
    return QVariant();
}
