"""
Data Loader para TASK-005 — Carrega histórico de trades Sprint 1.

Este módulo funciona como interface para carregar e validar dados de
histórico de trades, convertendo entre formatos (JSON ↔ OHLCV).

Módulos:
    json: Leitura de arquivos JSON
    pathlib: Manipulação de caminhos
    numpy: Operações numéricas
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np


class TradeHistoryLoader:
    """
    Carregador de histórico de trades para treinamento PPO.
    
    Responsabilidades:
    - Carregar trades de data/trades_history.json
    - Validar schema de cada trade
    - Converter para formato OHLCV se necessário
    """
    
    REQUIRED_FIELDS = ['entry_price', 'exit_price', 'qty', 'direction']
    DEFAULT_FILEPATH = "data/trades_history.json"
    
    def __init__(self, filepath: str = DEFAULT_FILEPATH):
        """
        Inicializa o carregador.
        
        Args:
            filepath (str): Caminho do arquivo de trades
        """
        self.filepath = filepath
        self.trades = []
        self.is_loaded = False
    
    def load(self) -> List[Dict]:
        """
        Carrega trades do arquivo JSON.
        
        Returns:
            list: Lista de trades validados
            
        Raises:
            FileNotFoundError: Se o arquivo não existir
            json.JSONDecodeError: Se o JSON é inválido
            ValueError: Se algum trade tem campos faltosos
        """
        fpath = Path(self.filepath)
        
        if not fpath.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.filepath}")
        
        with open(fpath, 'r') as f:
            self.trades = json.load(f)
        
        # Valida cada trade
        for i, trade in enumerate(self.trades):
            self._validate_trade(trade, index=i)
        
        self.is_loaded = True
        return self.trades
    
    def _validate_trade(self, trade: Dict, index: int = 0) -> None:
        """
        Valida um trade individual.
        
        Args:
            trade (dict): Dados do trade
            index (int): Índice do trade (para mensagens de erro)
            
        Raises:
            ValueError: Se algum campo obrigatório está faltando ou inválido
        """
        # Verifica campos obrigatórios
        missing_fields = [f for f in self.REQUIRED_FIELDS if f not in trade]
        if missing_fields:
            raise ValueError(
                f"Trade #{index}: campos faltosos: {missing_fields}"
            )
        
        # Valida tipos e valores
        try:
            entry_price = float(trade['entry_price'])
            exit_price = float(trade['exit_price'])
            qty = float(trade['qty'])
            direction = str(trade['direction']).upper()
            
            # Validações de negócio
            if entry_price <= 0:
                raise ValueError(f"entry_price deve ser > 0")
            if exit_price <= 0:
                raise ValueError(f"exit_price deve ser > 0")
            if qty <= 0:
                raise ValueError(f"qty deve ser > 0")
            if direction not in ['LONG', 'SHORT']:
                raise ValueError(f"direction deve ser LONG ou SHORT")
        
        except (TypeError, ValueError) as e:
            raise ValueError(f"Trade #{index}: {str(e)}")
    
    def get_trades(self) -> List[Dict]:
        """
        Retorna os trades carregados.
        
        Returns:
            list: Lista de trades
        """
        if not self.is_loaded:
            self.load()
        
        return self.trades
    
    def get_statistics(self) -> Dict:
        """
        Calcula estatísticas dos trades carregados.
        
        Returns:
            dict: Dicionário com estatísticas
        """
        if not self.is_loaded:
            self.load()
        
        if not self.trades:
            return {}
        
        pnls = []
        rewards = []
        long_count = 0
        short_count = 0
        
        for trade in self.trades:
            entry = float(trade['entry_price'])
            exit_val = float(trade['exit_price'])
            qty = float(trade['qty'])
            direction = str(trade['direction']).upper()
            
            # Calcula PnL
            if direction == 'LONG':
                pnl = (exit_val - entry) * qty
                long_count += 1
            else:  # SHORT
                pnl = (entry - exit_val) * qty
                short_count += 1
            
            pnls.append(pnl)
            
            # Reward normalizado
            reward = pnl / (entry * qty) if (entry * qty) != 0 else 0
            rewards.append(reward)
        
        pnls_arr = np.array(pnls)
        rewards_arr = np.array(rewards)
        
        stats = {
            'total_trades': len(self.trades),
            'long_trades': long_count,
            'short_trades': short_count,
            'total_pnl': float(np.sum(pnls_arr)),
            'mean_pnl': float(np.mean(pnls_arr)),
            'std_pnl': float(np.std(pnls_arr)),
            'mean_reward': float(np.mean(rewards_arr)),
            'std_reward': float(np.std(rewards_arr)),
            'winning_trades': int(np.sum(pnls_arr > 0)),
            'losing_trades': int(np.sum(pnls_arr < 0)),
            'win_rate': float(np.sum(pnls_arr > 0) / len(pnls_arr)) if pnls else 0,
            'profit_factor': float(
                np.sum(pnls_arr[pnls_arr > 0]) / 
                abs(np.sum(pnls_arr[pnls_arr < 0]))
            ) if np.sum(pnls_arr[pnls_arr < 0]) != 0 else 0,
        }
        
        return stats
    
    def print_statistics(self) -> None:
        """Imprime estatísticas de forma amigável."""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 TRADE HISTORY STATISTICS")
        print("="*60)
        print(f"Total Trades:     {stats.get('total_trades', 0)}")
        print(f"  ├─ LONG:        {stats.get('long_trades', 0)}")
        print(f"  └─ SHORT:       {stats.get('short_trades', 0)}")
        print(f"\nPnL:")
        print(f"  ├─ Total:       ${stats.get('total_pnl', 0):.2f}")
        print(f"  ├─ Mean:        ${stats.get('mean_pnl', 0):.2f}")
        print(f"  └─ Std Dev:     ${stats.get('std_pnl', 0):.2f}")
        print(f"\nWin Rate:")
        print(f"  ├─ Winning:     {stats.get('winning_trades', 0)} trades")
        print(f"  ├─ Losing:      {stats.get('losing_trades', 0)} trades")
        print(f"  └─ Rate:        {stats.get('win_rate', 0)*100:.1f}%")
        print(f"\nProfit Factor:    {stats.get('profit_factor', 0):.2f}")
        print("="*60 + "\n")


def load_trade_history(
    filepath: str = "data/trades_history.json"
) -> List[Dict]:
    """
    Função convenience para carregar histórico de trades.
    
    Args:
        filepath (str): Caminho do arquivo de trades
        
    Returns:
        list: Lista de trades carregados
    """
    loader = TradeHistoryLoader(filepath)
    return loader.load()


def convert_trades_to_ohlcv(trades: List[Dict]) -> List[Dict]:
    """
    Converte histórico de trades para sequência OHLCV.
    
    Cada trade é representado como um candle onde:
    - open = entry_price
    - close = exit_price
    - high = max(entry, exit)
    - low = min(entry, exit)
    - volume = qty (simulado)
    
    Args:
        trades (list): Lista de trades
        
    Returns:
        list: Lista de dicts OHLCV
    """
    ohlcv_list = []
    
    for trade in trades:
        entry = float(trade['entry_price'])
        exit_val = float(trade['exit_price'])
        qty = float(trade.get('qty', 1.0))
        
        candle = {
            'open': entry,
            'high': max(entry, exit_val),
            'low': min(entry, exit_val),
            'close': exit_val,
            'volume': qty * 10,  # Simulação: qty * multiplicador
        }
        
        ohlcv_list.append(candle)
    
    return ohlcv_list


if __name__ == "__main__":
    # Teste do carregador
    loader = TradeHistoryLoader()
    trades = loader.load()
    print(f"✅ Carregados {len(trades)} trades")
    loader.print_statistics()
