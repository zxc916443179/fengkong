#include "detaildialog.h"
#include "ui_detaildialog.h"
#include "mainwindow.h"

DetailDialog::DetailDialog(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::DetailDialog)
{
    ui->setupUi(this);
    ui->tableView->setModel(&detailModel);
    this->resize(QSize(900, 600));
    this->setWindowTitle("未平仓头寸详情");
}

DetailDialog::~DetailDialog()
{
    delete ui;
}

void DetailDialog::refresh(QStringList detail)
{
    detailModel.setDetail(detail);
}
