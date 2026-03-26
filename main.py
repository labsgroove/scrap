#!/usr/bin/env python3
"""
CLI profissional para scraping de Ordens de Serviço.

Uso:
    python main.py [opções]

Exemplos:
    python main.py                                    # Modo interativo
    python main.py --headless --output meu_arquivo.xlsx
    python main.py --start-page 5 --format json
    python main.py --resume  # Continua do último checkpoint
"""
import argparse
import logging
import sys
import os
from pathlib import Path

import keyboard

from models import ScrapingConfig
from scraper import ServiceOrderScraper
from exporter import DataExporter


def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    """Configura logging estruturado"""
    level = logging.DEBUG if verbose else logging.INFO
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def parse_args():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description='Scraper de Ordens de Serviço com retry automático',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s                          # Modo interativo com Edge aberto
  %(prog)s --headless               # Modo headless (sem interface)
  %(prog)s --output dados.xlsx      # Nome do arquivo de saída
  %(prog)s --start-page 5           # Começar da página 5
  %(prog)s --resume                 # Continuar do último checkpoint
  %(prog)s --format json            # Exportar como JSON
  %(prog)s -v                       # Modo verbose (debug)
        """
    )
    
    # Configurações de conexão
    parser.add_argument(
        '--debugger-address', '-d',
        default='127.0.0.1:9222',
        help='Endereço do debugger Chrome/Edge (padrão: 127.0.0.1:9222)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Executar em modo headless (sem interface gráfica)'
    )
    
    # Configurações de scraping
    parser.add_argument(
        '--start-page', '-s',
        type=int,
        default=1,
        help='Página inicial para começar (padrão: 1)'
    )
    
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        help='Continuar do último checkpoint salvo'
    )
    
    # Configurações de saída
    parser.add_argument(
        '--output', '-o',
        default='os_extraidas.xlsx',
        help='Arquivo de saída (padrão: os_extraidas.xlsx)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['excel', 'csv', 'json', 'sqlite', 'all'],
        default='excel',
        help='Formato de saída (padrão: excel)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Diretório para salvar arquivos (padrão: atual)'
    )
    
    # Performance
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=10,
        help='Timeout em segundos para carregar elementos (padrão: 10)'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Máximo de retentativas em caso de erro (padrão: 3)'
    )
    
    # Logging
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Modo verbose (mais logs)'
    )
    
    parser.add_argument(
        '--log-file',
        help='Arquivo para salvar logs'
    )
    
    return parser.parse_args()


def main():
    """Função principal"""
    args = parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose, log_file=args.log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("SCRAPER DE ORDENS DE SERVIÇO")
    logger.info("=" * 50)
    
    # Determina página inicial
    start_page = args.start_page
    if args.resume:
        exporter = DataExporter(args.output_dir)
        checkpoint_page = exporter.load_checkpoint()
        if checkpoint_page > 0:
            start_page = checkpoint_page + 1
            logger.info(f"Continuando da página {start_page} (checkpoint)")
    
    # Configuração
    config = ScrapingConfig(
        debugger_address=args.debugger_address if not args.headless else None,
        output_file=args.output,
        headless=args.headless,
        timeout=args.timeout,
        max_retries=args.max_retries
    )
    
    logger.info(f"Configuração: headless={args.headless}, timeout={args.timeout}s")
    logger.info(f"Saída: {args.output_dir}/{args.output}")
    
    if not args.headless:
        logger.info("Modo interativo - pressione ESC a qualquer momento para parar")
    
    # Flag para parada via ESC
    stop_requested = False
    
    def check_stop():
        """Verifica se ESC foi pressionado"""
        nonlocal stop_requested
        if not args.headless and keyboard.is_pressed('esc'):
            if not stop_requested:
                logger.info("[ESC] Parada solicitada...")
                stop_requested = True
            return True
        return stop_requested
    
    def progress_callback(tentativas: int):
        """Callback de progresso"""
        logger.info(f"Aguardando avanço de página... ({tentativas}s)")
    
    # Executa scraping
    scraper = ServiceOrderScraper(config)
    
    try:
        result, data = scraper.scrape(
            start_page=start_page,
            progress_callback=progress_callback,
            stop_check=check_stop
        )
        
        # Exporta dados
        exporter = DataExporter(args.output_dir)
        
        base_name = Path(args.output).stem
        
        if args.format == 'excel' or args.format == 'all':
            exporter.to_excel(data, f"{base_name}.xlsx")
        if args.format == 'csv' or args.format == 'all':
            exporter.to_csv(data, f"{base_name}.csv")
        if args.format == 'json' or args.format == 'all':
            exporter.to_json(data, f"{base_name}.json")
        if args.format == 'sqlite' or args.format == 'all':
            exporter.to_sqlite(data, f"{base_name}.db")
        
        # Salva checkpoint e relatório
        if data:
            exporter.save_checkpoint(start_page + result.pages_processed - 1)
        exporter.save_report(result)
        
        # Resumo final
        logger.info("=" * 50)
        logger.info("RESUMO")
        logger.info("=" * 50)
        logger.info(f"Registros extraídos: {result.total_records}")
        logger.info(f"Páginas processadas: {result.pages_processed}")
        logger.info(f"Duração: {result.duration:.1f} segundos")
        logger.info(f"Taxa de sucesso: {result.success_rate:.1f}%")
        
        if result.errors:
            logger.warning(f"Erros encontrados: {len(result.errors)}")
        
        logger.info("=" * 50)
        
        # Retorna código de erro se houver falhas graves
        if result.success_rate < 50:
            sys.exit(1)
        
    except Exception as e:
        logger.exception(f"Erro fatal: {e}")
        sys.exit(1)


from typing import Optional

if __name__ == "__main__":
    main()
