//const url = //'wss://fstream.binance.com/ws/BTCUSDT@aggTrade'//BTCUSDT@depth20@100ms'
const WebSocket = require('ws');

const ws = new WebSocket('wss://fstream.binance.com/ws/btcusdt@trade');

ws.on('message', function incoming(data) {
    console.log(data);
});
const ws2 = new WebSocket('wss://fstream.binance.com/ws/btcusdt@depth20@100ms');

ws2.on('message', function incoming(data) {
    console.log(data);
});

ws.onerror = error => {
  console.log(`WebSocket1 error: ${error}`)
}

ws2.onerror = error => {
  console.log(`WebSocket2 error: ${error}`)
}
