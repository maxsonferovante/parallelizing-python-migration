"""
Script para benchmark de performance dos três modos de implementação:
- ASYNCIO
- THREADING
- MULTIPROCESSING

Executa cada modo sequencialmente e coleta os tempos de execução.
"""
import asyncio
import time
import json
from datetime import datetime
from typing import Dict, List

from models.settings.postgres.connection import db_postgres_connection_handler
from models.settings.mongo.connection import db_mongo_connection_handler

from models.repository.user_mongo_repository import UserMongoRepository
from models.repository.user_postgres_repository import UserPostgresRepository
from models.entities.user import User
from cluster.cluster import ClusterMigrationFactory
from background_task import backend_task
from params import CLUSTER_SIZE, ITEMS_PER_PAGE, ClusterImplementation


async def run_migration(implementation: ClusterImplementation) -> Dict[str, any]:
    """
    Executa a migração com um modo específico e retorna métricas.

    Args:
        implementation: Modo de implementação a ser testado

    Returns:
        Dicionário com métricas de execução
    """
    print(f"\n{'='*60}")
    print(f"Iniciando migração com {implementation.name}")
    print(f"{'='*60}\n")

    start_time = time.time()
    users_migrated = 0
    error_occurred = False
    error_message = None

    try:
        # Conecta aos bancos de dados
        db_mongo_connection_handler.connect_to_db()

        user_mongo_repository = UserMongoRepository(
            db_mongo_connection_handler.get_db_collenction(User.__name__)
        )

        await db_postgres_connection_handler.connect_to_db()

        user_postgres_repository = UserPostgresRepository(
            db_postgres_connection_handler.get_connection()
        )

        # Limpa e cria tabela
        await user_postgres_repository.drop_table()
        await user_postgres_repository.create_table()

        total_users_mongo = await user_mongo_repository.count_documents()
        print(f"Total de usuários no MongoDB: {total_users_mongo}")

        # Cria cluster com o modo especificado
        cluster_migration = ClusterMigrationFactory.create(
            backend_task=backend_task,
            cluster_size=CLUSTER_SIZE,
            implementation=implementation
        )

        print(f"Usando implementação: {implementation.name} com {CLUSTER_SIZE} workers")

        # Inicializa workers
        await cluster_migration.initialize_processes()

        # Processa dados paginados
        async for page_of_users in user_mongo_repository.get_all_paginated(
            skip=0, limit=ITEMS_PER_PAGE
        ):
            users_tuples = [
                (user["username"], user["email"], user["age"])
                for user in page_of_users
            ]

            await cluster_migration.start_process(users_tuples)

        # Aguarda conclusão
        await cluster_migration.awaiting_completion_processes()

        # Conta usuários migrados
        users_migrated = await user_postgres_repository.count_users()

        execution_time = time.time() - start_time

        print(f"\n✅ Migração concluída!")
        print(f"Tempo de execução: {execution_time:.2f} segundos")
        print(f"Usuários migrados: {users_migrated}")

    except Exception as e:
        error_occurred = True
        error_message = str(e)
        execution_time = time.time() - start_time
        print(f"\n❌ Erro durante a migração: {e}")

    finally:
        # Fecha conexões
        try:
            await db_mongo_connection_handler.close_connection()
            await db_postgres_connection_handler.close_connection()
        except:
            pass

    return {
        "implementation": implementation.name,
        "execution_time": round(execution_time, 2),
        "users_migrated": users_migrated,
        "cluster_size": CLUSTER_SIZE,
        "items_per_page": ITEMS_PER_PAGE,
        "error": error_occurred,
        "error_message": error_message,
        "timestamp": datetime.now().isoformat()
    }


async def run_benchmark() -> List[Dict[str, any]]:
    """
    Executa benchmark sequencial dos três modos de implementação.

    Returns:
        Lista com resultados de cada execução
    """
    results = []

    # Ordem de execução: ASYNCIO, THREADING, MULTIPROCESSING
    implementations = [
        ClusterImplementation.ASYNCIO,
        ClusterImplementation.THREADING,
        ClusterImplementation.MULTIPROCESSING
    ]

    print("\n" + "="*60)
    print("BENCHMARK DE PERFORMANCE - MIGRAÇÃO MONGODB → POSTGRESQL")
    print("="*60)
    print(f"\nConfigurações:")
    print(f"  - Cluster Size: {CLUSTER_SIZE} workers")
    print(f"  - Items per Page: {ITEMS_PER_PAGE}")
    print(f"  - Modos a testar: {[impl.name for impl in implementations]}")

    for implementation in implementations:
        result = await run_migration(implementation)
        results.append(result)

        # Pequeno delay entre execuções para estabilizar recursos
        if implementation != implementations[-1]:
            print(f"\nAguardando 3 segundos antes do próximo teste...")
            await asyncio.sleep(3)

    return results


def print_results_summary(results: List[Dict[str, any]]):
    """
    Imprime resumo comparativo dos resultados.

    Args:
        results: Lista com resultados de cada execução
    """
    print("\n" + "="*60)
    print("RESUMO DOS RESULTADOS")
    print("="*60 + "\n")

    # Ordena por tempo de execução
    sorted_results = sorted(results, key=lambda x: x["execution_time"])

    print(f"{'Modo':<20} {'Tempo (s)':<15} {'Usuários':<15} {'Status':<10}")
    print("-" * 60)

    for result in sorted_results:
        status = "✅ OK" if not result["error"] else "❌ ERRO"
        print(
            f"{result['implementation']:<20} "
            f"{result['execution_time']:<15.2f} "
            f"{result['users_migrated']:<15} "
            f"{status:<10}"
        )

    print("\n" + "-" * 60)

    # Análise comparativa
    if len(sorted_results) > 1 and not any(r["error"] for r in sorted_results):
        fastest = sorted_results[0]
        slowest = sorted_results[-1]

        speedup = slowest["execution_time"] / fastest["execution_time"]

        print(f"\n📊 Análise Comparativa:")
        print(f"  - Mais rápido: {fastest['implementation']} ({fastest['execution_time']:.2f}s)")
        print(f"  - Mais lento: {slowest['implementation']} ({slowest['execution_time']:.2f}s)")
        print(f"  - Diferença: {speedup:.2f}x mais rápido")

        # Comparação individual
        print(f"\n📈 Comparação com {fastest['implementation']}:")
        for result in sorted_results:
            if result != fastest:
                ratio = result["execution_time"] / fastest["execution_time"]
                diff = result["execution_time"] - fastest["execution_time"]
                print(
                    f"  - {result['implementation']}: "
                    f"{ratio:.2f}x ({diff:+.2f}s)"
                )


def save_results(results: List[Dict[str, any]], filename: str = "benchmark_results.json"):
    """
    Salva resultados em arquivo JSON.

    Args:
        results: Lista com resultados de cada execução
        filename: Nome do arquivo para salvar
    """
    output = {
        "benchmark_date": datetime.now().isoformat(),
        "config": {
            "cluster_size": CLUSTER_SIZE,
            "items_per_page": ITEMS_PER_PAGE
        },
        "results": results
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados salvos em: {filename}")


async def main():
    """
    Função principal que executa o benchmark completo.
    """
    try:
        results = await run_benchmark()
        print_results_summary(results)
        save_results(results)

        print("\n" + "="*60)
        print("BENCHMARK CONCLUÍDO!")
        print("="*60 + "\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro durante o benchmark: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

