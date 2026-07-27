#property strict

input string ApiUrl = "http://127.0.0.1:8011/local/mt5/h1";
input string CanonicalSymbol = "XAUUSD";
input string BrokerSymbol = "";
input string BrokerServer = "";
input int SendIntervalSeconds = 300;

datetime lastSendTime = 0;

string JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return value;
}

string IsoUtc(datetime value)
{
   MqlDateTime parts;
   TimeToStruct(value, parts);

   return StringFormat(
      "%04d-%02d-%02dT%02d:%02d:%02dZ",
      parts.year,
      parts.mon,
      parts.day,
      parts.hour,
      parts.min,
      parts.sec
   );
}

string ResolveBrokerSymbol()
{
   if(StringLen(BrokerSymbol) > 0)
      return BrokerSymbol;

   return _Symbol;
}

string ResolveBrokerServer()
{
   if(StringLen(BrokerServer) > 0)
      return BrokerServer;

   return AccountInfoString(ACCOUNT_SERVER);
}

bool SendCurrentH1()
{
   string symbol = ResolveBrokerSymbol();

   MqlRates rates[];
   ArraySetAsSeries(rates, true);

   if(CopyRates(symbol, PERIOD_H1, 0, 1, rates) != 1)
   {
      Print("MT5 H1 bridge: CopyRates failed.");
      return false;
   }

   datetime nowUtc = TimeGMT();
   string eventId = StringFormat(
      "%s-%I64d-%I64d",
      symbol,
      (long)rates[0].time,
      (long)nowUtc
   );

   string payload = StringFormat(
      "{\"broker_server\":\"%s\","
      "\"broker_symbol\":\"%s\","
      "\"candle_start_utc\":\"%s\","
      "\"close\":\"%.5f\","
      "\"high\":\"%.5f\","
      "\"low\":\"%.5f\","
      "\"open\":\"%.5f\","
      "\"source_event_id\":\"%s\","
      "\"symbol\":\"%s\","
      "\"timeframe\":\"H1\","
      "\"timestamp_utc\":\"%s\"}",
      JsonEscape(ResolveBrokerServer()),
      JsonEscape(symbol),
      IsoUtc(rates[0].time),
      rates[0].close,
      rates[0].high,
      rates[0].low,
      rates[0].open,
      JsonEscape(eventId),
      CanonicalSymbol,
      IsoUtc(nowUtc)
   );

   char body[];
   StringToCharArray(payload, body, 0, WHOLE_ARRAY, CP_UTF8);

   char response[];
   string responseHeaders;
   string headers =
      "Content-Type: application/json\r\n";

   ResetLastError();

   int status = WebRequest(
      "POST",
      ApiUrl,
      headers,
      10000,
      body,
      response,
      responseHeaders
   );

   if(status < 200 || status >= 300)
   {
      Print(
         "MT5 H1 bridge send failed. HTTP=",
         status,
         " error=",
         GetLastError()
      );
      return false;
   }

   Print(
      "MT5 H1 candle accepted. Candle start=",
      IsoUtc(rates[0].time)
   );

   return true;
}

int OnInit()
{
   EventSetTimer(30);
   Print("XAUUSD H1 market-data bridge loaded. No trade functions exist.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   datetime nowUtc = TimeGMT();

   if(lastSendTime != 0 &&
      nowUtc - lastSendTime < SendIntervalSeconds)
      return;

   if(SendCurrentH1())
      lastSendTime = nowUtc;
}
