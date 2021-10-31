#ifndef DETAILDIALOG_H
#define DETAILDIALOG_H

#include <QDialog>
#include "my_model.h"

namespace Ui {
class DetailDialog;
}

class DetailDialog : public QDialog
{
    Q_OBJECT

public slots:
    void refresh(QStringList detail);

public:
    explicit DetailDialog(QWidget *parent = 0);
    ~DetailDialog();

private:
    Ui::DetailDialog *ui;
    DetailModel detailModel;
};

#endif // DETAILDIALOG_H
