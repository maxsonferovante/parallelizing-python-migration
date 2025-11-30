# Parallelizing Python Migration - MongoDB para PostgreSQL

## Descrição do Projeto

Este projeto implementa um sistema de migração de dados otimizado para transferir grandes volumes de dados do MongoDB para PostgreSQL. Inspirado no vídeo de [Erick Wendel](https://www.youtube.com/watch?v=EnK8-x8L9TY&t=932s), a solução utiliza processamento paralelo assíncrono com suporte a **asyncio**, **multiprocessing** e **threading**, processamento em lotes (batch) e otimizações de performance para lidar eficientemente com milhões de registros.

### Características Principais

- ✅ **Processamento Paralelo**: Suporte a asyncio (padrão), multiprocessing e threading via Factory Pattern
- ✅ **Otimizações de Performance**: Bulk insert usando [`COPY`](https://magicstack.github.io/asyncpg/current/api/index.html) do PostgreSQL
- ✅ **Cálculo Automático**: Tamanho do cluster calculado automaticamente baseado no número de cores da CPU
- ✅ **Implementação Asyncio**: Versão simplificada usando apenas asyncio, ideal para tarefas I/O-bound

## Pré-requisitos

- Python 3.11+
- Servidor MongoDB
- Servidor PostgreSQL
- Bibliotecas Python: `asyncio`, `multiprocessing`, `threading`, `pymongo`, `asyncpg`

## Instalação

1. Clone este repositório:
```bash
git clone https://github.com/seu-usuario/parallelizing-python-migration.git
cd parallelizing-python-migration
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
# ou usando uv
uv sync
```

3. Configure as conexões de banco de dados em `models/settings/config.py`

## Como Usar

### Executando a Migração

1. Certifique-se de que o MongoDB e PostgreSQL estão rodando e acessíveis
2. Execute o script principal:
```bash
    uv run app.py
```

3. Acompanhe o progresso através da barra de progresso exibida no terminal

### Populando Dados de Teste

Para gerar dados de teste no MongoDB:
```bash
    uv run seed.py
```

### Executando Benchmark de Performance

Para comparar o desempenho dos três modos de implementação (ASYNCIO, THREADING, MULTIPROCESSING):

```bash
    uv run benchmark.py
```

O script executa cada modo sequencialmente e exibe:
- Tempo de execução de cada modo
- Número de usuários migrados
- Comparação de performance entre os modos
- Resultados salvos em `benchmark_results.json`

**Nota:** O benchmark limpa e recria a tabela do PostgreSQL antes de cada execução para garantir condições iguais.

## Configuração

O comportamento do sistema pode ser personalizado através dos parâmetros em `params.py`:

### Parâmetros Principais

- **`CLUSTER_IMPLEMENTATION`**: Tipo de implementação do cluster
  - `ClusterImplementation.ASYNCIO` (padrão): Usa apenas asyncio - recomendado para tarefas I/O-bound, menor overhead
  - `ClusterImplementation.THREADING`: Usa threads - menor overhead, sem serialização
  - `ClusterImplementation.MULTIPROCESSING`: Usa processos - maior isolamento entre workers
  
- **`CLUSTER_SIZE`**: Número de workers paralelos (calculado automaticamente)
  - Fórmula: `CPU_CORES * CLUSTER_SIZE_MULTIPLIER` (padrão: 3x o número de cores)
  - Para tarefas I/O intensivas, o ideal é entre 2x e 4x o número de cores físicos

- **`ITEMS_PER_PAGE`**: Número de itens processados por lote (padrão: 10.000)

- **`AMOUNT_USERS`**: Número total de usuários esperados (padrão: 1.000.000)

- **`AMOUNT_USERS_SEED`**: Número de usuários para gerar no seed (padrão: 100.000)

### Exemplo de Configuração

```python
# params.py
CLUSTER_IMPLEMENTATION = ClusterImplementation.ASYNCIO  # Padrão: asyncio
CLUSTER_SIZE_MULTIPLIER = 3  # 3x o número de cores
ITEMS_PER_PAGE = 10000
```

## Arquitetura

### Estrutura de Classes

O projeto utiliza um padrão **Factory** com classes base abstratas:

```
ClusterMigrationBase (ABC)
├── ClusterMigrationAsyncio (padrão)
├── ClusterMigrationThreading
└── ClusterMigrationMultiprocessing

ClusterMigrationFactory
└── create() -> ClusterMigrationBase
```

### Componentes Principais

#### Factory Pattern (`ClusterMigrationFactory`)

Cria instâncias do cluster baseado na configuração:

```python
from cluster.cluster import ClusterMigrationFactory
from params import CLUSTER_IMPLEMENTATION, CLUSTER_SIZE

cluster = ClusterMigrationFactory.create(
    backend_task=backend_task,
    cluster_size=CLUSTER_SIZE,
    implementation=CLUSTER_IMPLEMENTATION
)
```

#### Cluster de Migração

**ClusterMigrationAsyncio** (Padrão - Recomendado para I/O-bound):
- Usa `asyncio.create_task()` e `asyncio.Queue`
- Menor overhead de criação
- Sem necessidade de serialização (pickle)
- Todas as tasks rodam no mesmo event loop
- Comunicação assíncrona nativa
- Máxima simplicidade e performance para I/O-bound

**ClusterMigrationThreading**:
- Usa `threading.Thread` e `queue.Queue`
- Menor overhead de criação
- Sem necessidade de serialização (pickle)
- Compartilhamento de memória
- Cada thread tem seu próprio event loop

**ClusterMigrationMultiprocessing**:
- Usa `multiprocessing.Process` e `multiprocessing.Pipe`
- Maior isolamento entre workers
- Requer serialização dos dados
- Melhor para tarefas CPU-bound
- Cada processo tem seu próprio event loop

#### Workers (`background_task.py`)

Cada worker executa de forma assíncrona:

```python
async def backend_task(communication_channel):
    # Conexão persistente (aberta uma vez)
    connection = PostgresConnectionHandler()
    await connection.connect_to_db()
    
    try:
        while True:
            # Recebe lote de dados
            message = await receive_data(communication_channel)
            
            # Bulk insert usando COPY (muito mais rápido)
            await repository.insert_many_users(message)
    finally:
        await connection.close_connection()
```

#### Lógica Principal (`app.py`)

Orquestra todo o processo de migração:

```python
async def main():
    # 1. Conecta aos bancos de dados
    # 2. Inicializa repositórios
    # 3. Cria tabela no PostgreSQL
    # 4. Cria cluster usando Factory
    cluster = ClusterMigrationFactory.create(...)
    
    # 5. Processa dados paginados do MongoDB
    async for page_of_users in mongo_repo.get_all_paginated(...):
        users_tuples = [(u["username"], u["email"], u["age"]) for u in page]
        await cluster.start_process(users_tuples)
    
    # 6. Aguarda conclusão
    await cluster.awaiting_completion_processes()
```

## Otimizações de Performance

### Cálculo Automático do Cluster Size

O tamanho do cluster é calculado automaticamente baseado no hardware:

```python
CPU_CORES = multiprocessing.cpu_count()
CLUSTER_SIZE = CPU_CORES * 3  # 3x para I/O-bound tasks
```

Evita context switching excessivo enquanto maximiza paralelismo.

## Comparação: Asyncio vs Threading vs Multiprocessing

| Aspecto | **Asyncio** | Threading | Multiprocessing |
|--------|-------------|-----------|----------------|
| **Overhead** | **Muito Baixo** | Baixo | Alto |
| **Serialização** | **Não necessária** | Não necessária | Necessária (pickle) |
| **Isolamento** | Baixo (mesmo processo) | Baixo | Alto |
| **Memória** | **Compartilhada** | Compartilhada | Separada |
| **Event Loop** | **Um único** | Múltiplos | Múltiplos |
| **Comunicação** | **asyncio.Queue (nativo)** | queue.Queue | multiprocessing.Pipe |
| **Ideal para** | **I/O-bound** | I/O-bound | CPU-bound |
| **Simplicidade** | **Máxima** | Média | Baixa |
| **Recomendado** | **✅✅ Sim (padrão)** | ✅ Sim | Para casos específicos |

## Estrutura do Projeto

```
parallelizing-python-migration/
├── app.py                      # Script principal
├── benchmark.py                # Script de benchmark de performance
├── background_task.py          # Worker assíncrono
├── seed.py                     # Geração de dados de teste
├── params.py                   # Configurações e enums
├── cluster/
│   ├── __init__.py
│   └── cluster.py              # Factory e implementações
├── models/
│   ├── entities/               # Entidades de domínio
│   ├── repository/             # Repositórios de dados
│   └── settings/               # Configurações de conexão
└── utils/                      # Utilitários
```

## Exemplo de Uso

```python
from cluster.cluster import ClusterMigrationFactory
from background_task import backend_task
from params import CLUSTER_SIZE, CLUSTER_IMPLEMENTATION

# Factory cria a implementação correta automaticamente
cluster = ClusterMigrationFactory.create(
    backend_task=backend_task,
    cluster_size=CLUSTER_SIZE,
    implementation=CLUSTER_IMPLEMENTATION
)

await cluster.initialize_processes()

# Envia dados para processamento paralelo
for data_batch in data_batches:
    await cluster.start_process(data_batch)

# Aguarda conclusão
await cluster.awaiting_completion_processes()
```

## Performance

Com as otimizações implementadas, o sistema pode processar milhões de registros de forma eficiente:

- **Bulk Insert**: Redução de 10x a 50x no tempo de inserção
- **Paralelismo**: Escalabilidade baseada no hardware disponível

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para:

- Abrir issues para reportar bugs ou sugerir melhorias
- Enviar pull requests com correções ou novas funcionalidades
- Melhorar a documentação

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## Referências

- [Erick Wendel - Parallelizing Node.js](https://www.youtube.com/watch?v=EnK8-x8L9TY&t=932s)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [PostgreSQL COPY Documentation](https://www.postgresql.org/docs/current/sql-copy.html)
