"""Test suite for fraud detection module."""

import pytest
from decimal import Decimal
from datetime import datetime

from src.models import Payment, PaymentMethod, PaymentStatus
from src.fraud import (
    FraudSignal,
    RiskLevel,
    AlertType,
    CaseDecision,
    CaseStatus,
    SimpleFraudEngine,
    MLFraudEngine,
    InMemoryFraudStream,
    KafkaFraudStream,
)


class TestFraudSignal:
    """Tests for fraud signal model."""
    
    def test_create_fraud_signal(self):
        """Test creating a fraud signal."""
        signal = FraudSignal(
            transaction_id="txn_123",
            risk_score=Decimal("0.75"),
            risk_level=RiskLevel.HIGH,
            merchant_id="merchant_1",
            customer_id="customer_1",
            amount=Decimal("100.00"),
            currency="USD",
        )
        
        assert signal.transaction_id == "txn_123"
        assert signal.risk_score == Decimal("0.75")
        assert signal.risk_level == RiskLevel.HIGH
    
    def test_fraud_signal_validation(self):
        """Test fraud signal validation."""
        with pytest.raises(ValueError):
            FraudSignal(
                transaction_id="txn_123",
                risk_score=Decimal("1.5"),  # Invalid: > 1
                risk_level=RiskLevel.HIGH,
            )
        
        with pytest.raises(ValueError):
            FraudSignal(
                transaction_id="txn_123",
                risk_score=Decimal("0.5"),
                risk_level=RiskLevel.HIGH,
                amount=Decimal("-10.00"),  # Invalid: negative
            )
    
    def test_is_high_risk(self):
        """Test high risk detection."""
        high_risk = FraudSignal(
            transaction_id="txn_1",
            risk_score=Decimal("0.8"),
            risk_level=RiskLevel.HIGH,
        )
        assert high_risk.is_high_risk()
        
        critical_risk = FraudSignal(
            transaction_id="txn_2",
            risk_score=Decimal("0.9"),
            risk_level=RiskLevel.CRITICAL,
        )
        assert critical_risk.is_high_risk()
        
        low_risk = FraudSignal(
            transaction_id="txn_3",
            risk_score=Decimal("0.1"),
            risk_level=RiskLevel.LOW,
        )
        assert not low_risk.is_high_risk()
    
    def test_should_decline(self):
        """Test decline decision detection."""
        decline = FraudSignal(
            transaction_id="txn_1",
            risk_score=Decimal("0.5"),
            risk_level=RiskLevel.HIGH,
            decision=CaseDecision.DECLINE,
        )
        assert decline.should_decline()
        
        block = FraudSignal(
            transaction_id="txn_2",
            risk_score=Decimal("0.9"),
            risk_level=RiskLevel.CRITICAL,
            decision=CaseDecision.BLOCK,
        )
        assert block.should_decline()
        
        approve = FraudSignal(
            transaction_id="txn_3",
            risk_score=Decimal("0.1"),
            risk_level=RiskLevel.LOW,
            decision=CaseDecision.APPROVE,
        )
        assert not approve.should_decline()
    
    def test_to_dict(self):
        """Test converting signal to dictionary."""
        signal = FraudSignal(
            transaction_id="txn_123",
            risk_score=Decimal("0.5"),
            risk_level=RiskLevel.MEDIUM,
            alerts=[AlertType.AMOUNT_ANOMALY],
            merchant_id="merchant_1",
            customer_id="customer_1",
        )
        
        signal_dict = signal.to_dict()
        
        assert signal_dict["transaction_id"] == "txn_123"
        assert signal_dict["risk_score"] == "0.5"
        assert signal_dict["risk_level"] == "medium"
        assert signal_dict["alerts"] == ["amount_anomaly"]


class TestSimpleFraudEngine:
    """Tests for simple fraud engine."""
    
    def test_evaluate_low_risk(self):
        """Test evaluation of low-risk transaction."""
        engine = SimpleFraudEngine()
        payment = Payment(
            id="pay_1",
            amount=Decimal("50.00"),
            currency="USD",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.AUTHORIZED,
            merchant_id="merchant_1",
            customer_id="customer_1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        signal = engine.evaluate(payment)
        
        assert signal.risk_level == RiskLevel.LOW
        assert signal.decision == CaseDecision.APPROVE
        assert len(signal.alerts) == 0
    
    def test_evaluate_amount_anomaly(self):
        """Test amount anomaly detection."""
        engine = SimpleFraudEngine(max_transaction_amount=Decimal("1000.00"))
        payment = Payment(
            id="pay_2",
            amount=Decimal("5000.00"),
            currency="USD",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.AUTHORIZED,
            merchant_id="merchant_1",
            customer_id="customer_1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        signal = engine.evaluate(payment)
        
        assert AlertType.AMOUNT_ANOMALY in signal.alerts
        assert signal.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
    
    def test_evaluate_with_context(self):
        """Test evaluation with additional context."""
        engine = SimpleFraudEngine()
        payment = Payment(
            id="pay_3",
            amount=Decimal("100.00"),
            currency="USD",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.AUTHORIZED,
            merchant_id="merchant_1",
            customer_id="customer_1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        context = {
            "previous_location": "New York",
            "current_location": "Tokyo",
            "device_mismatch": True,
        }
        
        signal = engine.evaluate(payment, context)
        
        assert AlertType.UNUSUAL_LOCATION in signal.alerts
        assert AlertType.DEVICE_FINGERPRINT_MISMATCH in signal.alerts
        assert signal.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)


class TestMLFraudEngine:
    """Tests for ML fraud engine."""
    
    def test_evaluate_with_ml(self):
        """Test ML-based evaluation."""
        engine = MLFraudEngine(model_path="/models/fraud_model.pkl")
        payment = Payment(
            id="pay_4",
            amount=Decimal("100.00"),
            currency="USD",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.AUTHORIZED,
            merchant_id="merchant_1",
            customer_id="customer_1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        signal = engine.evaluate(payment)
        
        assert signal.transaction_id == payment.id
        assert AlertType.ML_PREDICTION in signal.alerts
        assert "model_score" in signal.ml_scores
        assert "confidence" in signal.ml_scores


class TestInMemoryFraudStream:
    """Tests for in-memory fraud stream."""
    
    def test_emit_signal(self):
        """Test emitting a fraud signal."""
        stream = InMemoryFraudStream()
        signal = FraudSignal(
            transaction_id="txn_1",
            risk_score=Decimal("0.5"),
            risk_level=RiskLevel.MEDIUM,
            merchant_id="merchant_1",
            customer_id="customer_1",
        )
        
        result = stream.emit(signal)
        
        assert result is True
        assert len(stream.get_signals()) == 1
    
    def test_subscribe_and_callback(self):
        """Test subscription and callback."""
        stream = InMemoryFraudStream()
        received_signals = []
        
        def callback(signal: FraudSignal):
            received_signals.append(signal)
        
        stream.subscribe(callback)
        
        signal = FraudSignal(
            transaction_id="txn_2",
            risk_score=Decimal("0.7"),
            risk_level=RiskLevel.HIGH,
        )
        
        stream.emit(signal)
        
        assert len(received_signals) == 1
        assert received_signals[0].transaction_id == "txn_2"
    
    def test_get_signals_for_transaction(self):
        """Test retrieving signals for a transaction."""
        stream = InMemoryFraudStream()
        
        signal1 = FraudSignal(
            transaction_id="txn_100",
            risk_score=Decimal("0.3"),
            risk_level=RiskLevel.MEDIUM,
        )
        signal2 = FraudSignal(
            transaction_id="txn_100",
            risk_score=Decimal("0.5"),
            risk_level=RiskLevel.HIGH,
        )
        signal3 = FraudSignal(
            transaction_id="txn_200",
            risk_score=Decimal("0.1"),
            risk_level=RiskLevel.LOW,
        )
        
        stream.emit(signal1)
        stream.emit(signal2)
        stream.emit(signal3)
        
        txn_100_signals = stream.get_signals_for_transaction("txn_100")
        assert len(txn_100_signals) == 2
        
        txn_200_signals = stream.get_signals_for_transaction("txn_200")
        assert len(txn_200_signals) == 1


class TestKafkaFraudStream:
    """Tests for Kafka fraud stream."""
    
    def test_init(self):
        """Test Kafka stream initialization."""
        stream = KafkaFraudStream(
            bootstrap_servers="localhost:9092",
            topic_prefix="fraud_events",
        )
        
        assert stream.bootstrap_servers == "localhost:9092"
        assert stream.topic_prefix == "fraud_events"
    
    def test_emit_high_risk_signal(self):
        """Test emitting high-risk signal (would go to alerts topic)."""
        stream = KafkaFraudStream()
        signal = FraudSignal(
            transaction_id="txn_300",
            risk_score=Decimal("0.8"),
            risk_level=RiskLevel.HIGH,
            decision=CaseDecision.REVIEW,
        )
        
        # In real implementation, would verify Kafka emission
        result = stream.emit(signal)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
