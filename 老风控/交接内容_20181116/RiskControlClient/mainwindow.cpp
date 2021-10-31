#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <Qtimer>
#include <QSize>

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    connect(ui->actionDetail, &QAction::triggered, this, &MainWindow::onActionDetailTriggered);
    ui->tableViewTraders->setModel(&briefModel);
    detailDialog = NULL;
    this->resize(QSize(450, 600));
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::onActionDetailTriggered()
{
    detailDialog = new DetailDialog(this);
    detailDialog->show();
}

void MainWindow::refresh(QStringList b, QStringList d)
{
    briefModel.setBrief(b);
    if(detailDialog && detailDialog->isVisible())
    {
        detailDialog->refresh(d);
    }
}
