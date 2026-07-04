"""Fraud signal streaming to message brokers (e.g., Kafka)."""

from abc import ABC, abstractmethod
from typing import Optional, Callable, List
from datetime import datetime
import json

from .models import FraudSignal


class FraudSignalStream(ABC):
    """Abstract base class for fraud signal streaming."""
    
    @abstractmethod
    def emit(self, signal: FraudSignal) -> bool:
        """
        Emit a fraud signal to the stream.
        
        Args:
            signal: FraudSignal to emit
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def subscribe(self, callback: Callable[[FraudSignal], None]) -> None:
        """
        Subscribe to fraud signals.
        
        Args:
            callback: Function to call when signal is received
        """
        pass


class KafkaFraudStream(FraudSignalStream):
    """
    Kafka-based fraud signal streaming.
    
    Emits fraud signals to Kafka topics keyed by transaction ID.
    Topics:
    - fraud.signals: Main fraud signal topic
    - fraud.alerts: High-priority alerts
    - fraud.decisions: Case decisions
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic_prefix: str = "fraud",
        auto_create_topics: bool = True,
    ):
        """
        Initialize Kafka fraud stream.
        
        Args:
            bootstrap_servers: Kafka broker addresses
            topic_prefix: Prefix for Kafka topics
            auto_create_topics: Whether to auto-create topics
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.auto_create_topics = auto_create_topics
        self._producer = None
        self._consumer = None
        self._callbacks: List[Callable] = []
    
    def connect(self) -> bool:
        """
        Connect to Kafka broker.
        
        Note: In production, use kafka-python or confluent-kafka library.
        This is a placeholder implementation.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Placeholder: would actually connect to Kafka here
            # from kafka import KafkaProducer, KafkaConsumer
            # self._producer = KafkaProducer(bootstrap_servers=self.bootstrap_servers)
            # self._consumer = KafkaConsumer(bootstrap_servers=self.bootstrap_servers)
            return True
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}")
            return False
    
    def emit(self, signal: FraudSignal) -> bool:
        """
        Emit fraud signal to Kafka.
        
        Args:
            signal: FraudSignal to emit
            
        Returns:
            True if emitted successfully
        """
        if not self._producer:
            if not self.connect():
                return False
        
        try:
            # Determine topic based on risk level
            if signal.is_high_risk():
                topic = f"{self.topic_prefix}.alerts"
            else:
                topic = f"{self.topic_prefix}.signals"
            
            # Serialize signal
            message = signal.to_dict()
            message_json = json.dumps(message)
            
            # In production, would emit to Kafka:
            # self._producer.send(
            #     topic,
            #     key=signal.transaction_id.encode(),
            #     value=message_json.encode(),
            # )
            
            # Placeholder: just log
            print(f"[Kafka] {topic}: {signal.transaction_id} - {signal.risk_level.value}")
            
            # Emit decision topic
            if signal.decision.value != "approve":
                decision_topic = f"{self.topic_prefix}.decisions"
                # In production: self._producer.send(decision_topic, ...)
                print(f"[Kafka] {decision_topic}: {signal.transaction_id} - {signal.decision.value}")
            
            return True
        except Exception as e:
            print(f"Failed to emit fraud signal: {e}")
            return False
    
    def subscribe(self, callback: Callable[[FraudSignal], None]) -> None:
        """
        Subscribe to fraud signals.
        
        Args:
            callback: Function to call when signal received
        """
        self._callbacks.append(callback)
    
    def _process_message(self, message: dict) -> Optional[FraudSignal]:
        """
        Process a message from Kafka.
        
        Args:
            message: Raw message from Kafka
            
        Returns:
            FraudSignal or None if parsing fails
        """
        try:
            # Would parse message and reconstruct FraudSignal
            # This is a placeholder
            return None
        except Exception as e:
            print(f"Failed to process message: {e}")
            return None
    
    def close(self) -> None:
        """Close Kafka connections."""
        if self._producer:
            try:
                self._producer.close()
            except Exception:
                pass
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                pass


class InMemoryFraudStream(FraudSignalStream):
    """
    In-memory fraud signal stream (for testing/development).
    
    Stores signals in memory and supports subscriptions via callbacks.
    """
    
    def __init__(self):
        """Initialize in-memory stream."""
        self._signals: List[FraudSignal] = []
        self._callbacks: List[Callable[[FraudSignal], None]] = []
    
    def emit(self, signal: FraudSignal) -> bool:
        """
        Emit fraud signal to in-memory store.
        
        Args:
            signal: FraudSignal to emit
            
        Returns:
            True if emitted successfully
        """
        self._signals.append(signal)
        
        # Call all registered callbacks
        for callback in self._callbacks:
            try:
                callback(signal)
            except Exception as e:
                print(f"Callback error: {e}")
        
        return True
    
    def subscribe(self, callback: Callable[[FraudSignal], None]) -> None:
        """
        Subscribe to fraud signals.
        
        Args:
            callback: Function to call when signal received
        """
        self._callbacks.append(callback)
    
    def get_signals(self) -> List[FraudSignal]:
        """Get all emitted signals (for testing)."""
        return self._signals.copy()
    
    def get_signals_for_transaction(self, transaction_id: str) -> List[FraudSignal]:
        """Get signals for a specific transaction."""
        return [s for s in self._signals if s.transaction_id == transaction_id]
