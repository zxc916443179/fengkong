import numpy as np
import pandas as pd

def get_loss(filepath):
    data = pd.read_excel(filepath, encoding="gb2312")
    data = data.dropna(how="any")
    print(data)


def main():
    dic = get_loss("stop_loss.xlsx")
    print(dic)


if __name__ == "__main__":
    main()

