import asyncio
import logging
import time
import multiprocessing

from utils.print_progress_bar import print_progress_bar

from params import AMOUNT_USERS

class ClusterMigration:
    
    def __init__(self, backend_task, cluster_size):
        self.backend_task = backend_task
        self.cluster_size = cluster_size
        
        self.__worker_pipes = []
        self.__processes = []
        
        self.__progress = 0
        self.__count = 0
              
    
    def _start_worker_process(self, child_conn):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.backend_task(child_conn))
        loop.close()
            
    def _print_progress(self):
        print_progress_bar(self.__progress, AMOUNT_USERS,prefix = 'Progress:', suffix = 'Complete', length = 60)        

    async def initialize_processes(self):                
        for index in range(self.cluster_size):
            parent_conn, child_conn = multiprocessing.Pipe()
            
            proc = multiprocessing.Process(target= self._start_worker_process, 
                                           args=(child_conn,),
                                           name=f"worker-{index   + 1}")
            proc.start()
            self.__worker_pipes.append(parent_conn)
            self.__processes.append(proc)
            
            child_conn.close()
        await asyncio.sleep(2)
        
    async def start_process(self, data):
        # Enviar dados para os processos filhos usando o round-robin
        parent_conn = self.__worker_pipes[
            self.__count % len(self.__worker_pipes)
        ]
        parent_conn.send(data)
        
        self.__count += 1
        
        self._print_progress()
        
        self.__progress += len(data)    
            
    def awaiting_completion_processes(self):
        # Enviar uma mensagem vazia para os processos filhos pararem de esperar por dados
        for parent_conn in self.__worker_pipes:
            parent_conn.send([])
        
        # Esperar que todos os processos filhos terminem    
        for proc in self.__processes:
            proc.join()        
    