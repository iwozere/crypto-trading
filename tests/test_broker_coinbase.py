import pytest
from unittest.mock import patch, MagicMock
from src.trading.coinbase_broker import CoinbaseBroker

@pytest.fixture
def broker():
    with patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient') as MockClient:
        mock_client = MockClient.return_value
        yield CoinbaseBroker('fake_key', 'fake_secret', 'fake_pass')

@patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient')
def test_place_market_order(mock_client_class, broker):
    mock_client = mock_client_class.return_value
    mock_client.place_market_order.return_value = {'id': 'order123'}
    result = broker.place_order('BTC-USD', 'buy', 0.01)
    assert result['id'] == 'order123'
    mock_client.place_market_order.assert_called_once()

@patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient')
def test_place_limit_order(mock_client_class, broker):
    mock_client = mock_client_class.return_value
    mock_client.place_limit_order.return_value = {'id': 'order456'}
    result = broker.place_order('BTC-USD', 'sell', 0.01, order_type='limit', price=30000)
    assert result['id'] == 'order456'
    mock_client.place_limit_order.assert_called_once()

@patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient')
def test_cancel_order(mock_client_class, broker):
    mock_client = mock_client_class.return_value
    mock_client.cancel_order.return_value = {'status': 'canceled'}
    result = broker.cancel_order('order123')
    assert result['status'] == 'canceled'
    mock_client.cancel_order.assert_called_once()

@patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient')
def test_get_balance(mock_client_class, broker):
    mock_client = mock_client_class.return_value
    mock_client.get_accounts.return_value = [{'currency': 'BTC', 'balance': '1.0'}]
    result = broker.get_balance('BTC')
    assert result['currency'] == 'BTC'

@patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient')
def test_get_open_orders(mock_client_class, broker):
    mock_client = mock_client_class.return_value
    mock_client.get_orders.return_value = [{'id': 'order1'}]
    result = broker.get_open_orders('BTC-USD')
    assert result[0]['id'] == 'order1'

@patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient')
def test_get_order_status(mock_client_class, broker):
    mock_client = mock_client_class.return_value
    mock_client.get_order.return_value = {'id': 'order1', 'status': 'done'}
    result = broker.get_order_status('order1')
    assert result['status'] == 'done'

@patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient')
def test_fetch_ohlcv(mock_client_class, broker):
    mock_client = mock_client_class.return_value
    mock_client.get_product_historic_rates.return_value = [[1625097600, 33000, 35000, 34000, 34500, 100]]
    df = broker.fetch_ohlcv('BTC-USD', '60', limit=1)
    assert not df.empty
    assert 'open' in df.columns

@patch('src.trading.coinbase_broker.cbpro.AuthenticatedClient')
def test_api_exception_handling(mock_client_class, broker):
    mock_client = mock_client_class.return_value
    mock_client.place_market_order.side_effect = Exception('error')
    result = broker.place_order('BTC-USD', 'buy', 0.01)
    assert 'error' in result 