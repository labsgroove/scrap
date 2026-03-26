"""
Módulo de exportação de dados com suporte a múltiplos formatos.
"""
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import List, Optional

import pandas as pd
from datetime import datetime

from models import ServiceOrder, ScrapingResult

logger = logging.getLogger(__name__)


class DataExporter:
    """Exporta dados de scraping para múltiplos formatos"""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def to_excel(self, data: List[ServiceOrder], filename: str = "os_extraidas.xlsx") -> str:
        """Exporta para Excel"""
        if not data:
            logger.warning("Nenhum dado para exportar")
            return ""
        
        filepath = self.output_dir / filename
        
        try:
            records = [item.to_dict() for item in data]
            df = pd.DataFrame(records)
            df.to_excel(filepath, index=False, engine='openpyxl')
            logger.info(f"Exportado Excel: {filepath} ({len(data)} registros)")
            return str(filepath)
        except Exception as e:
            logger.error(f"Erro ao exportar Excel: {e}")
            raise
    
    def to_csv(self, data: List[ServiceOrder], filename: str = "os_extraidas.csv") -> str:
        """Exporta para CSV"""
        if not data:
            logger.warning("Nenhum dado para exportar")
            return ""
        
        filepath = self.output_dir / filename
        
        try:
            records = [item.to_dict() for item in data]
            df = pd.DataFrame(records)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"Exportado CSV: {filepath} ({len(data)} registros)")
            return str(filepath)
        except Exception as e:
            logger.error(f"Erro ao exportar CSV: {e}")
            raise
    
    def to_json(self, data: List[ServiceOrder], filename: str = "os_extraidas.json") -> str:
        """Exporta para JSON"""
        if not data:
            logger.warning("Nenhum dado para exportar")
            return ""
        
        filepath = self.output_dir / filename
        
        try:
            records = [item.to_dict() for item in data]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            logger.info(f"Exportado JSON: {filepath} ({len(data)} registros)")
            return str(filepath)
        except Exception as e:
            logger.error(f"Erro ao exportar JSON: {e}")
            raise
    
    def to_sqlite(self, data: List[ServiceOrder], filename: str = "os_extraidas.db") -> str:
        """Exporta para SQLite"""
        if not data:
            logger.warning("Nenhum dado para exportar")
            return ""
        
        filepath = self.output_dir / filename
        
        try:
            conn = sqlite3.connect(filepath)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS service_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    os_number TEXT,
                    cliente TEXT,
                    vendedor TEXT,
                    data_abertura TEXT,
                    status TEXT,
                    equipamento TEXT,
                    observacao TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            for item in data:
                cursor.execute('''
                    INSERT INTO service_orders 
                    (os_number, cliente, vendedor, data_abertura, status, equipamento, observacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item.os_number, item.cliente, item.vendedor,
                    item.data_abertura, item.status, item.equipamento, item.observacao
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Exportado SQLite: {filepath} ({len(data)} registros)")
            return str(filepath)
        except Exception as e:
            logger.error(f"Erro ao exportar SQLite: {e}")
            raise
    
    def save_checkpoint(self, page: int, filename: str = "ultima_pagina.txt"):
        """Salva checkpoint da última página processada"""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(str(page))
        logger.debug(f"Checkpoint salvo: página {page}")
    
    def load_checkpoint(self, filename: str = "ultima_pagina.txt") -> int:
        """Carrega checkpoint da última página processada"""
        filepath = self.output_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    return int(f.read().strip())
            except (ValueError, IOError):
                pass
        return 0
    
    def save_report(self, result: ScrapingResult, filename: str = "report.txt"):
        """Salva relatório do scraping"""
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("RELATÓRIO DE SCRAPING\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Data: {result.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duração: {result.duration:.1f} segundos\n")
            f.write(f"Páginas processadas: {result.pages_processed}\n")
            f.write(f"Registros extraídos: {result.total_records}\n")
            f.write(f"Taxa de sucesso: {result.success_rate:.1f}%\n\n")
            
            if result.errors:
                f.write(f"Erros ({len(result.errors)}):\n")
                for i, error in enumerate(result.errors[:10], 1):
                    f.write(f"  {i}. {error}\n")
                if len(result.errors) > 10:
                    f.write(f"  ... e mais {len(result.errors) - 10} erros\n")
            else:
                f.write("Nenhum erro registrado.\n")
        
        logger.info(f"Relatório salvo: {filepath}")
        return str(filepath)
