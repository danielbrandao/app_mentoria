import csv
import sqlite3
from datetime import datetime

# Nome do arquivo do banco de dados
DATABASE = 'aplicacao.db'

def criar_tabelas():
    """Cria as tabelas do banco de dados se não existirem."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Tabela de Monitores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monitores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        whatsapp TEXT,
        resumo TEXT,
        perfil TEXT
    );
    """)

    # Tabela de Turmas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turmas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_turma TEXT NOT NULL,
        descricao TEXT,
        data_inicio DATE,
        data_fim DATE,
        status TEXT DEFAULT 'Planejamento'
    );
    """)

    # Tabela de Registros (Mentorados)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        fone TEXT,
        perfil TEXT,
        desafio TEXT,
        disponibilidade TEXT,
        mensagem TEXT,
        data_inscricao DATETIME,
        status TEXT DEFAULT 'Inscrito',
        turma_id INTEGER,
        FOREIGN KEY (turma_id) REFERENCES turmas (id)
    );
    """)

    # Tabela de Encontros
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS encontros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descricao TEXT,
        data_encontro DATETIME,
        link_meet TEXT,
        status TEXT DEFAULT 'Agendado',
        turma_id INTEGER NOT NULL,
        monitor_id INTEGER NOT NULL,
        FOREIGN KEY (turma_id) REFERENCES turmas (id),
        FOREIGN KEY (monitor_id) REFERENCES monitores (id)
    );
    """)
    
    # Tabela de Associação Turma-Monitores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turma_monitores (
        turma_id INTEGER NOT NULL,
        monitor_id INTEGER NOT NULL,
        PRIMARY KEY (turma_id, monitor_id),
        FOREIGN KEY (turma_id) REFERENCES turmas (id),
        FOREIGN KEY (monitor_id) REFERENCES monitores (id)
    );
    """)

    print("Tabelas criadas com sucesso!")
    conn.commit()
    conn.close()


def importar_csv_para_registros():
    """
    Lê o arquivo dados.csv e insere na tabela de registros,
    com depuração detalhada para cada linha.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    registros_inseridos = 0
    linha_atual_no_arquivo = 1 # Começamos na linha 1 (cabeçalho)

    try:
        with open('Dados_mentoria_pre.csv', mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            print("--- Iniciando leitura detalhada do CSV ---")
            
            for row in csv_reader:
                linha_atual_no_arquivo += 1
                print(f"\nLendo linha {linha_atual_no_arquivo} do arquivo...")
                
                try:
                    # Tenta processar e inserir uma única linha
                    data_str = row['_date']
                    if not data_str or not data_str.strip():
                        print(f"  -> AVISO: Campo de data vazio na linha {linha_atual_no_arquivo}. Pulando registro.")
                        continue

                    # Converte a data do CSV para um formato de data/hora
                    data_obj = datetime.strptime(data_str, '%d/%m/%Y %H:%M:%S')
                    
                    # Insere na tabela
                    cursor.execute("""
                        INSERT OR IGNORE INTO registros (nome, email, fone, perfil, desafio, disponibilidade, mensagem, data_inscricao)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (row['nome'], row['email'], row['fone'], row['perfil'], row['desafio'], row['disponibilidade'], row['mensagem'], data_obj))
                    
                    # conn.commit() # Commit a cada inserção para salvar o progresso
                    if cursor.rowcount > 0:
                        registros_inseridos += 1
                        print(f"  -> SUCESSO: Registro '{row['nome']}' inserido.")
                    else:
                        print(f"  -> AVISO: Registro '{row['nome']}' (email: {row['email']}) já existe no banco de dados. Ignorando.")

                except Exception as e:
                    # Se ocorrer um erro em uma linha específica, informa qual é e continua
                    print(f"  -> ERRO na linha {linha_atual_no_arquivo}: Não foi possível processar este registro.")
                    print(f"     Motivo: {e}")
                    print(f"     Dados da linha com problema: {row}")
                    print("     Continuando para a próxima linha...")
        
        conn.commit() # Commit final de todas as transações bem sucedidas
        print("\n--- Leitura do CSV finalizada ---")

    except FileNotFoundError:
        print("ERRO CRÍTICO: Arquivo 'dados.csv' não foi encontrado na pasta do projeto.")
    except Exception as e:
        print(f"Ocorreu um erro geral e inesperado ao processar o arquivo: {e}")
    finally:
        print(f"\nTotal de registros novos inseridos com sucesso nesta execução: {registros_inseridos}")
        conn.close()


if __name__ == '__main__':
    print("Iniciando a configuração do banco de dados...")
    criar_tabelas()
    print("\nTentando importar dados do CSV para a tabela 'registros'...")
    importar_csv_para_registros()
    print("\nConfiguração finalizada.")