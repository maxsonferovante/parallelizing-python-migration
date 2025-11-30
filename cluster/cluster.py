import asyncio
import logging
import multiprocessing
import threading
import queue
from abc import ABC, abstractmethod
from typing import Callable, Union

from utils.print_progress_bar import print_progress_bar
from params import AMOUNT_USERS, ITEMS_PER_PAGE, ClusterImplementation


class ClusterMigrationBase(ABC):
    """
    Classe base abstrata para implementações de cluster de migração.
    Define a interface comum para multiprocessing e threading.
    """

    def __init__(self, backend_task: Callable, cluster_size: int):
        self.backend_task = backend_task
        self.cluster_size = cluster_size
        self._progress = ITEMS_PER_PAGE
        self._count = 0

    def _print_progress(self):
        """Imprime a barra de progresso."""
        print_progress_bar(
            self._progress,
            AMOUNT_USERS,
            prefix="Progress:",
            suffix="Complete",
            length=60,
        )

    @abstractmethod
    async def initialize_processes(self):
        """Inicializa os workers (processos ou threads)."""
        pass

    async def start_process(self, data):
        """Envia dados para os workers usando round-robin."""
        self._send_data_to_worker(data)
        self._count += 1
        self._print_progress()
        self._progress += ITEMS_PER_PAGE

    @abstractmethod
    def _send_data_to_worker(self, data):
        """Envia dados para um worker específico."""
        pass

    @abstractmethod
    async def awaiting_completion_processes(self):
        """Aguarda todos os workers terminarem."""
        pass

    @abstractmethod
    async def _stop_all_workers(self):
        """Envia sinal de parada para todos os workers."""
        pass


class ClusterMigrationMultiprocessing(ClusterMigrationBase):
    """
    Implementação de cluster usando multiprocessing.
    Ideal para isolamento completo entre workers.
    """

    def __init__(self, backend_task: Callable, cluster_size: int):
        super().__init__(backend_task, cluster_size)
        self.__worker_pipes = []
        self.__processes = []

    def _start_worker_process(self, child_conn):
        """Inicia um processo worker com seu próprio event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.backend_task(child_conn))
        loop.close()

    async def initialize_processes(self):
        """Inicializa os processos workers."""
        logging.info(f"Initializing {self.cluster_size} processes")
        for index in range(self.cluster_size):
            parent_conn, child_conn = multiprocessing.Pipe()

            proc = multiprocessing.Process(
                target=self._start_worker_process,
                args=(child_conn,),
                name=f"worker-{index + 1}",
            )
            proc.start()
            self.__worker_pipes.append(parent_conn)
            self.__processes.append(proc)

            child_conn.close()
        await asyncio.sleep(2)

    def _send_data_to_worker(self, data):
        """Envia dados para um processo worker usando round-robin."""
        parent_conn = self.__worker_pipes[self._count % len(self.__worker_pipes)]
        parent_conn.send(data)

    async def _stop_all_workers(self):
        """Envia mensagem vazia para todos os processos pararem."""
        for parent_conn in self.__worker_pipes:
            parent_conn.send([])

    async def awaiting_completion_processes(self):
        """Aguarda todos os processos terminarem."""
        await self._stop_all_workers()
        for proc in self.__processes:
            proc.join()


class ClusterMigrationThreading(ClusterMigrationBase):
    """
    Implementação de cluster usando threading.
    Ideal para tarefas I/O-bound, com menor overhead e sem serialização.
    """

    def __init__(self, backend_task: Callable, cluster_size: int):
        super().__init__(backend_task, cluster_size)
        self.__worker_queues = []
        self.__threads = []

    def _start_worker_thread(self, data_queue: queue.Queue):
        """Inicia uma thread worker com seu próprio event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.backend_task(data_queue))
        loop.close()

    async def initialize_processes(self):
        """Inicializa as threads workers."""
        logging.info(f"Initializing {self.cluster_size} threads")
        for index in range(self.cluster_size):
            data_queue = queue.Queue()

            thread = threading.Thread(
                target=self._start_worker_thread,
                args=(data_queue,),
                name=f"worker-{index + 1}",
                daemon=False
            )
            thread.start()

            self.__worker_queues.append(data_queue)
            self.__threads.append(thread)

        await asyncio.sleep(2)

    def _send_data_to_worker(self, data):
        """Envia dados para uma thread worker usando round-robin."""
        worker_queue = self.__worker_queues[self._count % len(self.__worker_queues)]
        worker_queue.put(data)

    async def _stop_all_workers(self):
        """Envia mensagem vazia para todas as threads pararem."""
        for worker_queue in self.__worker_queues:
            worker_queue.put([])

    async def awaiting_completion_processes(self):
        """Aguarda todas as threads terminarem."""
        await self._stop_all_workers()
        for thread in self.__threads:
            thread.join()


class ClusterMigrationAsyncio(ClusterMigrationBase):
    """
    Implementação de cluster usando apenas asyncio.
    Ideal para tarefas I/O-bound, com menor overhead e máxima simplicidade.
    Todas as tasks rodam no mesmo event loop.
    """

    def __init__(self, backend_task: Callable, cluster_size: int):
        super().__init__(backend_task, cluster_size)
        self.__worker_queues: list[asyncio.Queue] = []
        self.__worker_tasks: list[asyncio.Task] = []

    async def initialize_processes(self):
        """Inicializa as tasks assíncronas workers."""
        logging.info(f"Initializing {self.cluster_size} asyncio tasks")
        
        for index in range(self.cluster_size):
            # Cria uma queue assíncrona para cada worker
            data_queue = asyncio.Queue()
            
            # Cria uma task assíncrona que roda o backend_task
            task = asyncio.create_task(
                self.backend_task(data_queue),
                name=f"worker-{index + 1}"
            )
            
            self.__worker_queues.append(data_queue)
            self.__worker_tasks.append(task)
        
        # Pequeno delay para garantir que todas as tasks iniciaram
        await asyncio.sleep(0.1)

    def _send_data_to_worker(self, data):
        """Envia dados para um worker usando round-robin."""
        # Seleciona a queue do worker usando round-robin
        worker_queue = self.__worker_queues[
            self._count % len(self.__worker_queues)
        ]
        # Put_nowait é não-bloqueante e adequado para este caso
        worker_queue.put_nowait(data)

    async def _stop_all_workers(self):
        """Envia mensagem vazia para todos os workers pararem."""
        for worker_queue in self.__worker_queues:
            await worker_queue.put([])

    async def awaiting_completion_processes(self):
        """Aguarda todas as tasks terminarem."""
        await self._stop_all_workers()
        # Aguarda todas as tasks completarem
        await asyncio.gather(*self.__worker_tasks, return_exceptions=True)


class ClusterMigrationFactory:
    """
    Factory para criar instâncias de ClusterMigration.
    Suporta 'multiprocessing', 'threading' e 'asyncio'.
    """

    @staticmethod
    def create(
        backend_task: Callable,
        cluster_size: int,
        implementation: Union[ClusterImplementation, str] = ClusterImplementation.ASYNCIO
    ) -> ClusterMigrationBase:
        """
        Cria uma instância de ClusterMigration baseada no tipo especificado.

        Args:
            backend_task: Função async a ser executada pelos workers
            cluster_size: Número de workers
            implementation: ClusterImplementation enum ou string ('multiprocessing', 'threading' ou 'asyncio')

        Returns:
            Instância de ClusterMigrationBase

        Raises:
            ValueError: Se o tipo de implementação não for suportado
        """
        # Converte enum para string se necessário
        if isinstance(implementation, ClusterImplementation):
            implementation_value = implementation.value
        else:
            implementation_value = implementation.lower()

        if implementation_value == "multiprocessing":
            return ClusterMigrationMultiprocessing(backend_task, cluster_size)
        elif implementation_value == "threading":
            return ClusterMigrationThreading(backend_task, cluster_size)
        elif implementation_value == "asyncio":
            return ClusterMigrationAsyncio(backend_task, cluster_size)
        else:
            raise ValueError(
                f"Implementação '{implementation_value}' não suportada. "
                "Use ClusterImplementation.MULTIPROCESSING, ClusterImplementation.THREADING, "
                "ClusterImplementation.ASYNCIO, ou strings correspondentes."
            )
