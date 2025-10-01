#!/usr/bin/env python3

import os
import sys

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app, db

def init_database():
    """Inicializa o banco de dados criando todas as tabelas"""
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        print('Banco de dados criado com sucesso!')
        print('Tabelas criadas:')
        
        # Listar tabelas criadas
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        for table in tables:
            print(f'  - {table}')

if __name__ == '__main__':
    init_database()
