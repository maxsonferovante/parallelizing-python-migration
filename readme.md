# Parallelizing Python Migration - MongoDB for PostgreSQL

## Descrição do Projeto

Este projeto foi inspirado no vídeo de [Erick Wendel](https://www.youtube.com/watch?v=EnK8-x8L9TY&t=932s), em que implementa um sistema de migração projetado para transferir dados de usuários de um banco de dados MongoDB para um banco de dados PostgreSQL. Ele utiliza processamento assíncrono, multiprocessamento e uma abordagem baseada em cluster para lidar eficientemente com grandes conjuntos de dados, neste caso, até 1.000.000 de usuários. O sistema aproveita o processamento paralelo e técnicas de processamento em lotes. O projeto base usa (Javascript) NodeJs e solução proposta neste repositório usa Python 3.11.


## Pré-requisitos
- Python 3.7+
- Servidor MongoDB
- Servidor PostgreSQL
- Bibliotecas Python: `asyncio`, `multiprocessing`, `pymongo`, `asyncpg`

## Como usar

Para executar a migração, certifique-se de que o MongoDB e o PostgreSQL estejam corretamente configurados e acessíveis. Em seguida, simplesmente execute o script:

1. Clone este repositório: `git clone https://github.com/seu-usuario/parallelizing-python-migration.git`
2. Navegue até o diretório do projeto: `cd parallelizing-python-migration`
3. Execute o script principal: `python app.py`
4. Acompanhe o tempo de execução e compare com a versão sequencial para verificar o ganho de desempenho.

## Configuração

O comportamento do sistema pode ser personalizado através dos seguintes parâmetros em `params.py`:

- `ITEMS_PER_PAGE`: Controla o número de itens processados por lote. O padrão é definido como 8000.
- `CLUSTER_SIZE`: Define o número de processos de trabalho paralelos no cluster. Configurado para 90.
- `AMOUNT_USERS`: Especifica o número total de usuários esperados para serem processados, usado para rastreamento de progresso. O padrão é 1.000.000.
- `AMOUNT_USERS_SEED`: Usado como um valor de semente para gerar dados de usuário aleatórios, facilitando testes e desenvolvimento.


## Componentes Principais

### Migração em Cluster

`ClusterMigration` lida com a distribuição de dados para os processos de trabalho e garante que todos os processos estejam corretamente sincronizados e gerenciados:

- Inicializa os processos de trabalho e configura os canais de comunicação.
- Implementa a distribuição de dados para os processos de trabalho em round-robin.
- Monitora e relata o progresso da migração.

```python
clusterMigration = ClusterMigration(backend_task=backend_task, cluster_size=CLUSTER_SIZE)
await clusterMigration.initialize_processes()
```

### Lógica Principal de Migração

A funcionalidade central está encapsulada na função `main()` em `app.py` que orquestra todo o processo de migração:

1. **Conexões de Banco de Dados**: Estabelece conexões tanto com o MongoDB quanto com o PostgreSQL.
2. **Inicialização de Repositórios**: Inicializa os repositórios de acesso a dados para ambos os bancos de dados.
3. **Gerenciamento de Tabelas**: Apaga e recria a tabela de usuários no PostgreSQL para começar do zero.
4. **Migração de Dados**:
   - Recupera dados do MongoDB em forma paginada.
   - Distribui dados por um cluster de processos de trabalho para inserção no PostgreSQL.

```python
async for page_of_users in user_mongo_repository.get_all_paginated(skip=0, limit=ITEMS_PER_PAGE):
    users = [user for user in page_of_users]
    await clusterMigration.start_process(users)
```

### Processos de Trabalho

Cada processo de trabalho executa uma instância de `backend_task`, que recebe continuamente lotes de dados de usuários e os insere no PostgreSQL:

```python
while True:
    message = await asyncio.get_event_loop().run_in_executor(None, child_conn.recv)
    if message == []:
        break
    # Insere dados de usuário no PostgreSQL
```

## Contribuição
Contribuições são bem-vindas! Sinta-se à vontade para abrir uma issue ou enviar um pull request com melhorias, correções de bugs ou novas funcionalidades.

## Licença
Este projeto está licenciado sob a [MIT License](LICENSE).