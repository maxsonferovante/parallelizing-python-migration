"""
This module contains the configuration parameters for the application.
"""
import multiprocessing

# Calcula o número de cores físicos da máquina
CPU_CORES = multiprocessing.cpu_count()

# Para tarefas intensivas de I/O (como migração de dados), o ideal é usar
# entre 2x e 4x o número de cores físicos para evitar context switching excessivo.
# Usando 3x como padrão (meio termo entre 2x e 4x)
CLUSTER_SIZE_MULTIPLIER = 3

"""
The size of the cluster used for parallel processing.
Calculado automaticamente baseado no número de cores da CPU (3x o número de cores).
Para tarefas I/O intensivas, isso evita context switching excessivo enquanto
maximiza o paralelismo.
"""
CLUSTER_SIZE = CPU_CORES * CLUSTER_SIZE_MULTIPLIER


ITEMS_PER_PAGE = 10000
"""
The number of items to display per page in the application.
"""

AMOUNT_USERS = 1000000
"""
The total number of users in the system.
"""

AMOUNT_USERS_SEED = 100000
"""
The seed value used for generating random user data.
"""
