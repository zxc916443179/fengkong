import logging
from threading import Thread
from typing import List, Optional, Union
from common.common_library_module import Singleton
import time
import queue
from pandas import DataFrame

ts = None

TIMEOUT = 60

@Singleton
class TuShare(Thread):
    
    def importPackage(self):
        global ts
        import tushare as ts
    
    def __init__(self):
        super(TuShare, self).__init__()
        self.shares = {}
        self.codes = {}
        self.logger = logging.getLogger(__name__)
        self.append_queue = queue.Queue()
        self.my_time = time.time()
        self.update_frequency = 1.2
        self.last_update_time = self.my_time
        self.importPackage()
    
    def checkOutdateCodes(self):
        now = self.my_time
        remove_list = []
        for key, code in self.codes.items():
            if now - code['time'] > TIMEOUT:
                code["expired"] = True
                self.logger.debug(f"code[{key}] expired")
                remove_list.append(key)
        
        for key in remove_list:
            if self.codes[key]['expired']:
                self.codes.pop(key)
                self.shares.pop(key)
    
    def run(self) -> None:
        while 1:
            self.my_time = time.time()
            self.checkOutdateCodes()
            self.checkAppendList()
            codes = list(self.codes.keys())
            if self.my_time - self.last_update_time > self.update_frequency:
                self.last_update_time = self.my_time
                try:
                    data = ts.get_realtime_quotes(codes)
                    if data is not None:
                        data.index = data['code']
                        for code in codes:
                            self.shares[code] = data.loc[code, :]
                except Exception as e:
                    self.logger.error("", exc_info=True)
    
    def checkAppendList(self):
        while not self.append_queue.empty():
            code = self.append_queue.get()
            self.codes[code] = {'time': self.my_time, 'expired': False}
            self.shares[code] = None

    def getRealTimeQuotes(self, codes, time_out = 5) -> tuple[bool, DataFrame]:
        start_time = self.my_time
        codes_ = [c for c in codes]
        while 1:
            if self.my_time - start_time > time_out:
                return False, None
            gather_list = []
            gathered = True
            new_gather_indices = []
            for i, code in enumerate(codes_):
                if code not in self.codes:
                    self.logger.debug(f"add gather code {code}")
                    self.append_queue.put(code)
                    new_gather_indices.append(i)
                    gathered = False
                    break
                if self.codes[code]['expired']:
                    gathered = False
                    break
            for i in new_gather_indices:
                codes_.pop(i)
            if gathered:
                for code in codes:
                    if self.shares.get(code, None) is None:
                        gathered = False
                        break
                    gather_list.append(self.shares[code])
            if gathered:
                gather = DataFrame()
                for i, ga in enumerate(gather_list):
                    self.codes[codes[i]]['expired'] = False
                    self.codes[codes[i]]['time'] = self.my_time
                    gather.insert(i, codes[i], ga)
                return True, gather.T
