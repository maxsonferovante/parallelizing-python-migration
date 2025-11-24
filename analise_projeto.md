# Análise do Projeto Parallelizing Python Migration

## Propósito do Código
- Migrar usuários do MongoDB para o PostgreSQL com alto throughput.
- Comparar ganhos entre processamento sequencial e paralelizado.
- Garantir consistência ao recriar a tabela destino antes de cada carga.

## Arquitetura e Fluxo
1. `app.py` orquestra a execução: conecta aos bancos, recria a tabela alvo e dispara páginas de usuários para o cluster.
2. `ClusterMigration` (`cluster/cluster.py`) cria processos filhos via `multiprocessing`, distribui lotes em round-robin e rastreia progresso com `print_progress_bar`.
3. `background_task.backend_task` roda em cada processo: recebe lotes pelo pipe, cria uma conexão dedicada ao PostgreSQL e insere cada usuário.
4. Repositórios (`models/repository`) isolam as operações específicas de cada banco, enquanto `models/settings/*/connection.py` encapsula a configuração de drivers.
5. Parâmetros operacionais (`params.py`) permitem ajustar tamanho de lote, número de processos e contagem esperada de usuários para manter o monitoramento coerente.

## Orquestração Técnica dos Processos
1. **Inicialização**  
   - `ClusterMigration.initialize_processes` cria `cluster_size` pares de pipes (`parent_conn`, `child_conn`), garantindo canais exclusivos para cada worker.
   - Cada processo é instanciado com `multiprocessing.Process`, apontando para `_start_worker_process`, que monta um loop `asyncio` próprio antes de executar `backend_task`. Isso evita conflitos entre loops diferentes.
2. **Distribuição dos Lotes**  
   - O método `start_process` recebe uma lista de usuários e seleciona o pipe usando `self.__count % len(self.__worker_pipes)`, implementando round-robin puro para balancear a carga.
   - Após o `send`, incrementa `__progress` com o tamanho do lote e atualiza a barra (`print_progress_bar`) para refletir o volume migrado.
3. **Processamento nos Workers**  
   - `backend_task` permanece em laço infinito aguardando mensagens via `child_conn.recv`, executado em `run_in_executor` para não bloquear o loop assíncrono.
   - Ao receber um lote, cria um `PostgresConnectionHandler`, abre conexão, persiste cada usuário via `UserPostgresRepository.insert_user` e fecha a conexão ao final, garantindo isolamento por processo.
   - Mensagens vazias (`[]`) sinalizam o encerramento do worker, quebrando o laço.
4. **Finalização Coordenada**  
   - `ClusterMigration.awaiting_completion_processes` envia `[]` para cada pipe, instruindo os workers a finalizar. Em seguida, invoca `proc.join()` para aguardar o término ordenado e liberar recursos.
   - O processo principal só imprime estatísticas finais após a confirmação de que todas as inserções foram concluídas.

## Tecnologias e Bibliotecas
- **asyncio**: coordena as operações assíncronas tanto no processo principal quanto nas tasks dos workers.
- **multiprocessing**: abre múltiplos processos para contornar limites do GIL e maximizar uso de CPU.
- **Motor (MongoDB Async Driver)**: provê acesso não-bloqueante ao MongoDB (`AsyncIOMotorClient`).
- **asyncpg**: driver assíncrono para PostgreSQL com boa performance ao inserir lotes.
- **Pydantic**: define o modelo `User`, garantindo tipos claros para os dados trafegados.
- **Ferramentas utilitárias**: barra de progresso customizada (`utils/print_progress_bar.py`) para acompanhar a quantidade de registros migrados.

## Considerações Importantes
- Cada worker estabelece sua própria conexão com o PostgreSQL para evitar contenção entre processos.
- A comunicação entre processos é feita por `multiprocessing.Pipe`, simplificando o envio de listas de usuários.
- O projeto assume que MongoDB e PostgreSQL já estão populados e acessíveis segundo `models/settings/config.py`.
- O script `seed.py` pode ser utilizado para gerar massa de dados no MongoDB antes da migração.

