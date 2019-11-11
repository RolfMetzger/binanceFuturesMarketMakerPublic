with open('config.json') as json_file:
    data = json.load(json_file)
    RISK_CHARGE_VOL = data['RISK_CHARGE_VOL']['current']
    EWMA_WGT_COV = data['EWMA_WGT_COV']['current']
    VOL_PRIOR = data['VOL_PRIOR']['current']
    binApi = data['binApi']
    binSecret = data['binSecret']

const binance = require('node-binance-api')().options({
  APIKEY: binApi,
  APISECRET: binSecret,
  useServerTime: true // If you get timestamp errors, synchronize to server time at startup
});
var btc = 0;
const ccxt = require('ccxt')
binance_futures = new ccxt.binance(
            {"apiKey": binApi,
            "secret": binSec,
            "options":{"defaultMarket":"futures"},
            'urls': {'api': {
                                     'public': 'https://fapi.binance.com/fapi/v1',
                                     'private': 'https://fapi.binance.com/fapi/v1',},}})
var btcstart = 53.21020949
var btcs = []
var ids = []
var vol = 0
setInterval(async function(){
trades = await binance_futures.fapiPrivateGetUserTrades({'symbol':'BTCUSDT', 'limit': 1000})
for (var t in trades){
  if (!ids.includes(trades[t].id)){
    ids.push(trades[t].id)
vol+=parseFloat(trades[t].qty)

  }

}
bal = await binance_futures.fetchBalance()
btc = (bal.info.totalMarginBalance)
}, 5500)

const express = require('express');
var cors = require('cors');
var app = express();
app.use(cors());
var request = require("request")
var bodyParser = require('body-parser')
app.set('view engine', 'ejs');
app.listen(process.env.PORT || 80, function() {});
app.get('/update', cors(), (req, res) => {
console.log(btc)
if (btc != 0){
btcs.push( [new Date().getTime(), -1 * (1-(btc / btcstart)) * 100])
}
console.log('start: ' + btcstart)
    res.json({btc: btcs, qty: vol})

})

app.get('/', (req, res) => {
        res.render('index.ejs', {
            btc: btc
        })

});
