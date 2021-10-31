#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QTableView>

#include "my_model.h"
#include "detaildialog.h"

namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();

public slots:
    void onActionDetailTriggered();
    void refresh(QStringList brief, QStringList detail);

private:
    Ui::MainWindow *ui;
    DetailDialog * detailDialog;
    BriefModel briefModel;
};

#endif // MAINWINDOW_H
