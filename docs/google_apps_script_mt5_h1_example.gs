/**
 * MT5-only XAUUSD H1 fetch example.
 *
 * This is documentation/example code only.
 * Do not paste into the live Apps Script until the staging API is ready.
 */
function fetchLatestMt5H1Example() {
  const apiUrl =
    'https://YOUR-STAGING-API.example/market-data/mt5/h1/latest';

  const response = UrlFetchApp.fetch(apiUrl, {
    method: 'get',
    muteHttpExceptions: true,
    followRedirects: false,
    headers: {
      Accept: 'application/json'
    }
  });

  const status = response.getResponseCode();

  if (status !== 200) {
    throw new Error(
      'MT5 H1 feed unavailable. HTTP ' + status
    );
  }

  const data = JSON.parse(response.getContentText());

  if (
    data.symbol !== 'XAUUSD' ||
    data.timeframe !== 'H1' ||
    data.source !== 'MT5' ||
    data.fresh !== true
  ) {
    throw new Error('Invalid or stale MT5 H1 response.');
  }

  return {
    candleStartUtc: data.candle_start_utc,
    open: Number(data.open),
    high: Number(data.high),
    low: Number(data.low),
    close: Number(data.close),
    source: data.source,
    brokerSymbol: data.broker_symbol,
    brokerServer: data.broker_server,
    receivedAtUtc: data.received_at_utc
  };
}
