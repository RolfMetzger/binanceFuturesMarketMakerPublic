# This code is for sample purposes only, comes as is and with no warranty or guarantee of performance

from collections    import OrderedDict
from datetime       import datetime
from os.path        import getmtime
from time           import sleep
from utils          import ( get_logger, lag, print_dict, print_dict_of_dicts, sort_by_key,
                             ticksize_ceil, ticksize_floor, ticksize_round )
import json
from binance.enums import *

import copy as cp
import argparse, logging, math, os, pathlib, sys, time, traceback
import ccxt
try:
    from deribit_api    import RestClient
except ImportError:
    print("Please install the deribit_api pacakge", file=sys.stderr)
    print("    pip3 install deribit_api", file=sys.stderr)
    exit(1)

# Add command line switches
parser  = argparse.ArgumentParser( description = 'Bot' )

# Use production platform/account
parser.add_argument( '-p',
                     dest   = 'use_prod',
                     action = 'store_true' )

# Do not display regular status updates to terminal
parser.add_argument( '--no-output',
                     dest   = 'output',
                     action = 'store_false' )

# Monitor account only, do not send trades
parser.add_argument( '-m',
                     dest   = 'monitor',
                     action = 'store_true' )

# Do not restart bot on errors
parser.add_argument( '--no-restart',
                     dest   = 'restart',
                     action = 'store_false' )

args    = parser.parse_args()

if not args.use_prod:
    KEY     = ''
    SECRET  = ''
    URL     = 'https://test.deribit.com'
else:
    KEY     = ''
    SECRET  = ''
    URL     = 'https://www.deribit.com'
    
BP                  = 1e-4      # one basis point
BTC_SYMBOL          = 'btc'
CONTRACT_SIZE       = 10     # USD
COV_RETURN_CAP      = 100       # cap on variance for vol estimate
DECAY_POS_LIM       = 0.1       # position lim decay factor toward expiry
EWMA_WGT_COV        = 4         # parameter in % points for EWMA volatility estimate
EWMA_WGT_LOOPTIME   = 0.1       # parameter for EWMA looptime estimate
FORECAST_RETURN_CAP = 20        # cap on returns for vol estimate
LOG_LEVEL           = logging.INFO
MIN_ORDER_SIZE      = 15
MAX_LAYERS          =  5        # max orders to layer the ob with on each side
MKT_IMPACT          =  0.01   # base 1-sided spread between bid/offer
NLAGS               =  2        # number of lags in time series
PCT                 = 100 * BP  # one percentage point
PCT_LIM_LONG        = 200    # % position limit long
PCT_LIM_SHORT       = 100       # % position limit short
PCT_QTY_BASE        = 0.05       # pct order qty in bps as pct of acct on each order
MIN_LOOP_TIME       =   14.6     # Minimum time between loops
RISK_CHARGE_VOL     =   1.25    # vol risk charge in bps per 100 vol
SECONDS_IN_DAY      = 3600 * 24
SECONDS_IN_YEAR     = 365 * SECONDS_IN_DAY
WAVELEN_MTIME_CHK   = 15        # time in seconds between check for file change
WAVELEN_OUT         = 15        # time in seconds between output to terminal
WAVELEN_TS          = 15        # time in seconds between time series update
VOL_PRIOR           = 100       # vol estimation starting level in percentage pts

with open('config.json') as json_file:
    data = json.load(json_file)
    #RISK_CHARGE_VOL = data['RISK_CHARGE_VOL']['current']
    #EWMA_WGT_COV = data['EWMA_WGT_COV']['current']
    #VOL_PRIOR = data['VOL_PRIOR']['current']
    binApi = data['binApi']
    binSecret = data['binSecret']

    #DECAY_POS_LIM = data['RISK_CHARGE_VOL']['current']
    
EWMA_WGT_COV        *= PCT
MKT_IMPACT          *= BP
PCT_LIM_LONG        *= PCT
PCT_LIM_SHORT       *= PCT
PCT_QTY_BASE        *= BP
VOL_PRIOR           *= PCT


class MarketMaker( object ):
    
    def __init__( self, monitor = True, output = True ):
        self.equity_usd         = None
        self.equity_btc         = None
        self.equity_usd_init    = None
        self.equity_btc_init    = None
        self.con_size           = float( CONTRACT_SIZE )
        self.client             = None
        self.client3             = None
        self.usdtbalance = 46.18
        self.client2 = None
        self.deltas             = OrderedDict()
        self.futures            = OrderedDict()
        self.futures_prv        = OrderedDict()
        self.logger             = None
        self.mean_looptime      = 1
        self.monitor            = monitor
        self.output             = output or monitor
        self.positions          = OrderedDict()
        self.spread_data        = None
        self.this_mtime         = None
        self.ts                 = None
        self.vols               = OrderedDict()
    
    def create_client( self ):
        #self.client = RestClient( KEY, SECRET, URL )
        #print(binApi)
        from binance.client import Client
        self.client3 = Client(binApi, binSecret)

        binance_futures = ccxt.binance(
            {"apiKey": binApi,
            "secret": binSecret
 })
        self.client2 = ccxt.binance({    "apiKey": binApi,
    "secret": binSecret})
        self.client = binance_futures
        #print(dir(self.client))           

    
    def get_bbo( self, contract ): # Get best b/o excluding own orders
        
        # Get orderbook
        ob      = self.client.fetchOrderBook( contract )
        bids    = ob[ 'bids' ]
        asks    = ob[ 'asks' ]
        
        ords        = self.client.fetchOpenOrders( contract )
        #print(ords)
        bid_ords    = [ o for o in ords if o ['info'] [ 'side' ] == 'buy'  ]
        ask_ords    = [ o for o in ords if o ['info'] [ 'side' ] == 'sell' ]
        best_bid    = None
        best_ask    = None

        err = 10 ** -( self.get_precision( contract ) + 1 )
        
        for b in bids:
            match_qty   = sum( [ 
                o[1] for o in bid_ords 
                if math.fabs( b[0] - o[0] ) < err
            ] )
            if match_qty < b[1]:
                best_bid = b[0]
                break
        
        for a in asks:
            match_qty   = sum( [ 
                o[1] for o in ask_ords 
                if math.fabs( a[0] - o[0] ) < err
            ] )
            if match_qty < a[1]:
                best_ask = a[0]
                break
        
        return { 'bid': best_bid, 'ask': best_ask }
    
        
    def get_futures( self ): # Get all current futures instruments
        
        self.futures_prv    = cp.deepcopy( self.futures )
        insts               = self.client.fetchMarkets()
        #print(insts[0])
        self.futures        = sort_by_key( { 
            i[ 'symbol' ]: i for i in insts if i['symbol'] == 'BTC/USDT'
        } )
        #print(self.futures)
        #for k, v in self.futures.items():
            #self.futures[ k ][ 'expi_dt' ] = datetime.strptime( 
            #                                   v[ 'expiration' ][ : -4 ], 
            #                                   '%Y-%m-%d %H:%M:%S' )
                        
        
    def get_pct_delta( self ):         
        self.update_status()
        return sum( self.deltas.values()) / float(self.equity_btc)

    
    def get_spot( self ):
        #print(self.client2.fetchTicker( 'BTC/USDT' )['bid'])
        return self.client2.fetchTicker( 'BTC/USDT' )['bid']

    
    def get_precision( self, contract ):
        return 2

    
    def get_ticksize( self, contract ):
        return 0.01000000
    
    
    def output_status( self ):
        
        if not self.output:
            return None
        self.cancelall()
        orders = self.client3.get_open_margin_orders(symbol='BTCUSDT')
        for o in orders:
            print(o)
            result = self.client3.cancel_margin_order(
    symbol='BTCUSDT',
    orderId=o['orderId'])

        self.update_status()
        
        now     = datetime.utcnow()
        days    = ( now - self.start_time ).total_seconds() / SECONDS_IN_DAY
        print( '********************************************************************' )
        print( 'Start Time:        %s' % self.start_time.strftime( '%Y-%m-%d %H:%M:%S' ))
        print( 'Current Time:      %s' % now.strftime( '%Y-%m-%d %H:%M:%S' ))
        print( 'Days:              %s' % round( days, 1 ))
        print( 'Hours:             %s' % round( days * 24, 1 ))
        print( 'Spot Price:        %s' % self.get_spot())
        
        
        pnl_usd = self.equity_usd - self.equity_usd_init
        pnl_btc = self.equity_btc - self.equity_btc_init
        
        print( 'Equity ($):        %7.2f'   % self.equity_usd)
        print( 'P&L ($)            %7.2f'   % pnl_usd)
        print( 'Equity (BTC):      %7.4f'   % self.equity_btc)
        print( 'P&L (BTC)          %7.4f'   % pnl_btc)
        print( '%% Delta:           %s%%'% round( self.get_pct_delta() / PCT, 1 ))
        print( 'Total Delta (BTC): %s'   % round( sum( self.deltas.values()), 2 ))        
        print_dict_of_dicts( {
            k: {
                'BTC': self.deltas[ k ]
            } for k in self.deltas.keys()
            }, 
            roundto = 2, title = 'Deltas' )
        
        #print(self.positions)
        print_dict_of_dicts( {
            k: {
                'Contracts': self.positions[ k ][ 'positionAmt' ]
            } for k in self.positions.keys()
            }, 
            title = 'Positions' )
        
        if not self.monitor:
            print_dict_of_dicts( {
                k: {
                    '%': self.vols[ k ]
                } for k in self.vols.keys()
                }, 
                multiple = 100, title = 'Vols' )
            print( '\nMean Loop Time: %s' % round( self.mean_looptime, 2 ))
            self.cancelall()
        print( '' )

        
    def place_orders( self ):

        if self.monitor:
            return None
        
        con_sz  = self.con_size        
        
        for fut in self.futures.keys():
            
            account         = self.client.fetchBalance()
            spot            = self.get_spot()
            bal_btc         = self.usdtbalance / spot 
            pos             = float(self.positions[ fut ][ 'positionAmt' ])
            pos_lim_long    = bal_btc * PCT_LIM_LONG * 125 #/ len(self.futures)
            pos_lim_short   = bal_btc * PCT_LIM_SHORT * 125 #/ len(self.futures)
            #print(pos_lim_long)
            #expi            = self.futures[ fut ][ 'expi_dt' ]
            #tte             = max( 0, ( expi - datetime.utcnow()).total_seconds() / SECONDS_IN_DAY )
            pos_decay       = 1.0 - math.exp( -DECAY_POS_LIM * 8035200 )
            pos_lim_long   *= pos_decay
            pos_lim_short  *= pos_decay
            pos_lim_long   -= pos
            pos_lim_short  += pos
            pos_lim_long    = max( 0, pos_lim_long  )
            pos_lim_short   = max( 0, pos_lim_short )
            
            min_order_size_btc = (MIN_ORDER_SIZE * CONTRACT_SIZE) / spot
            print(min_order_size_btc) #0.0006833471711135484 0.08546200188472201
            qtybtc  = bal_btc * 125 / 25

            nbids   = min( math.trunc( pos_lim_long  / qtybtc ), MAX_LAYERS )
            nasks   = min( math.trunc( pos_lim_short / qtybtc ), MAX_LAYERS )
            
            place_bids = nbids > 0
            place_asks = nasks > 0
            
            if not place_bids and not place_asks:
                print( 'No bid no offer for %s' % fut, min_order_size_btc )
                continue
                
            tsz = float(self.get_ticksize( fut ))            
            # Perform pricing
            vol = max( self.vols[ BTC_SYMBOL ], self.vols[ fut ] )

            eps         = BP * vol * RISK_CHARGE_VOL
            riskfac     = math.exp( eps )

            bbo     = self.get_bbo( fut )
            bid_mkt = bbo[ 'bid' ]
            ask_mkt = bbo[ 'ask' ]
            
            if bid_mkt is None and ask_mkt is None:
                bid_mkt = ask_mkt = spot
            elif bid_mkt is None:
                bid_mkt = min( spot, ask_mkt )
            elif ask_mkt is None:
                ask_mkt = max( spot, bid_mkt )
            mid_mkt = 0.5 * ( bid_mkt + ask_mkt )
            
            ords        = self.client.fetchOpenOrders( fut )
            cancel_oids = []
            bid_ords    = ask_ords = []
            
            if place_bids:
                
                bid_ords        = [ o for o in ords if o['info']['side'] == 'buy'  ]
                len_bid_ords    = min( len( bid_ords ), nbids )
                bid0            = mid_mkt * math.exp( -MKT_IMPACT )
                
                bids    = [ bid0 * riskfac ** -i for i in range( 1, nbids + 1 ) ]

                bids[ 0 ]   = ticksize_floor( bids[ 0 ], tsz )
                
            if place_asks:
                
                ask_ords        = [ o for o in ords if o['info']['side'] == 'sell' ]    
                len_ask_ords    = min( len( ask_ords ), nasks )
                ask0            = mid_mkt * math.exp(  MKT_IMPACT )
                
                asks    = [ ask0 * riskfac ** i for i in range( 1, nasks + 1 ) ]
                
                asks[ 0 ]   = ticksize_ceil( asks[ 0 ], tsz  )
                
            for i in range( max( nbids, nasks )):
                # BIDS
                if place_bids and i < nbids:

                    if i > 0:
                        prc = ticksize_floor( min( bids[ i ], bids[ i - 1 ] - tsz ), tsz )
                    else:
                        prc = bids[ 0 ]

                    qty = round( prc * qtybtc / con_sz )   / spot                     
                        
                    if i < len_bid_ords:    

                        oid = bid_ords[ i ]['info']['side']['orderId']
                        print(oid)
                        try:
                            self.client.editOrder( oid, qty, prc , {'leverage': 5})
                        except (SystemExit, KeyboardInterrupt):
                            raise
                        except Excetion as e:
                            print(e)
                    else:
                        try:
                            print(float("{0:.2f}".format(qty)))
                            order = self.client3.create_margin_order(
                                symbol='BTCUSDT',
                                side=SIDE_BUY,
                                type=ORDER_TYPE_LIMIT,
                                timeInForce=TIME_IN_FORCE_GTC,
                                quantity=0.0012,
                                price=prc)

#                            self.client.sapiPostMarginOrder( {'symbol':fut,'side': 'BUY', 'type':"LIMIT",'timeInForce':  "GTC", 'quantity':qty,'price': prc,'recvWindow': "5000",'timestamp': str(math.floor(time.time())* 1000)})
                        except (SystemExit, KeyboardInterrupt):
                            raise
                        except Exception as e:
                            print(e)
                            self.logger.warn( 'Bid order failed: %s bid for %s'
                                                % ( prc, qty ))

                # OFFERS

                if place_asks and i < nasks:

                    if i > 0:
                        prc = ticksize_ceil( max( asks[ i ], asks[ i - 1 ] + tsz ), tsz )
                    else:
                        prc = asks[ 0 ]
                        
                    qty = round( prc * qtybtc / con_sz ) / spot
                    
                    if i < len_ask_ords:
                        oid = ask_ords[ i ]['info']['side']['orderId']
                        print(oid)
                        try:
                            self.client.editOrder( oid, qty, prc , {'leverage': 5})
                        except (SystemExit, KeyboardInterrupt):
                            raise
                        except Exeption as e:
                            print(e)

                    else:
                        try:
                            order = self.client3.create_margin_order(
                                symbol='BTCUSDT',
                                side=SIDE_SELL,
                                type=ORDER_TYPE_LIMIT,
                                timeInForce=TIME_IN_FORCE_GTC,
                                quantity=0.0012,
                                price=prc)

                            #self.client.sapiPostMarginOrder( {'symbol':fut,'side': 'SELL', 'type':"LIMIT",'timeInForce':  "GTC", 'quantity':qty,'price': prc,'recvWindow': "5000",'timestamp': str(math.floor(time.time())* 1000) })
                        except (SystemExit, KeyboardInterrupt):
                            raise
                        except Exception as e:
                            self.logger.warn( 'Offer order failed: %s at %s'
                                                % ( qty, prc ))


            if nbids < len( bid_ords ):
                cancel_oids += [ o['info']['side']['orderId'] for o in bid_ords[ nbids : ]]
            if nasks < len( ask_ords ):
                cancel_oids += [ o['info']['side']['orderId'] for o in ask_ords[ nasks : ]]
            for oid in cancel_oids:
                try:
                    self.client.cancelOrder( oid , 'BTC/USDT' )
                except:
                    self.logger.warn( 'Order cancellations failed: %s' % oid )
                                        
    def cancelall(self):
        ords        = self.client.fetchOpenOrders( 'BTC/USDT' )
        for order in ords:
            #print(order)
            oid = order ['info'] ['orderId']
           # print(order)
            try:
                self.client.cancelOrder( oid , 'BTC/USDT' )
            except Exception as e:
                print(e)
    def restart( self ):        
        try:
            strMsg = 'RESTARTING'
            print( strMsg )
            self.cancelall()
            strMsg += ' '
            for i in range( 0, 5 ):
                strMsg += '.'
                print( strMsg )
                sleep( 1 )
        except:
            pass
        finally:
            os.execv( sys.executable, [ sys.executable ] + sys.argv )        
            

    def run( self ):
        
        self.run_first()
        self.output_status()

        t_ts = t_out = t_loop = t_mtime = datetime.utcnow()

        while True:
            bal = self.client.sapiGetMarginAccount()
            for b in bal["userAssets"]:
                if b["asset"] == 'USDT':
                    self.usdtbalance = float(b["netAsset"])
              
            
            self.get_futures()
            
            # Restart if a new contract is listed
            if len( self.futures ) != len( self.futures_prv ):
                self.restart()
            
            self.update_positions()
            
            t_now   = datetime.utcnow()
            
            # Update time series and vols
            if ( t_now - t_ts ).total_seconds() >= WAVELEN_TS:
                t_ts = t_now
                self.update_timeseries()
                self.update_vols()
    
            self.place_orders()
            
            # Display status to terminal
            if self.output:    
                t_now   = datetime.utcnow()
                if ( t_now - t_out ).total_seconds() >= WAVELEN_OUT:
                    self.output_status(); t_out = t_now
            
            # Restart if file change detected
            t_now   = datetime.utcnow()
            if ( t_now - t_mtime ).total_seconds() > WAVELEN_MTIME_CHK:
                t_mtime = t_now
                if getmtime( __file__ ) > self.this_mtime:
                    self.restart()
            
            t_now       = datetime.utcnow()
            looptime    = ( t_now - t_loop ).total_seconds()
            
            # Estimate mean looptime
            w1  = EWMA_WGT_LOOPTIME
            w2  = 1.0 - w1
            t1  = looptime
            t2  = self.mean_looptime
            
            self.mean_looptime = w1 * t1 + w2 * t2
            
            t_loop      = t_now
            sleep_time  = MIN_LOOP_TIME - looptime
            if sleep_time > 0:
                time.sleep( sleep_time )
            if self.monitor:
                time.sleep( WAVELEN_OUT )

            
    def run_first( self ):
        
        self.create_client()
        self.cancelall()
        self.logger = get_logger( 'root', LOG_LEVEL )
        # Get all futures contracts
        self.get_futures()
        self.this_mtime = getmtime( __file__ )
        self.symbols    = [ BTC_SYMBOL ] + list( self.futures.keys()); self.symbols.sort()
        self.deltas     = OrderedDict( { s: None for s in self.symbols } )
        
        # Create historical time series data for estimating vol
        ts_keys = self.symbols + [ 'timestamp' ]; ts_keys.sort()
        
        self.ts = [
            OrderedDict( { f: None for f in ts_keys } ) for i in range( NLAGS + 1 )
        ]
        
        self.vols   = OrderedDict( { s: VOL_PRIOR for s in self.symbols } )
        
        self.start_time         = datetime.utcnow()
        self.update_status()
        self.equity_usd_init    = self.equity_usd
        self.equity_btc_init    = self.equity_btc
    
    
    def update_status( self ):
        
        account = self.client.fetchBalance()
        spot    = self.get_spot()

        #print(account)  
        self.equity_btc = self.usdtbalance / spot
        self.equity_usd = self.equity_btc * spot
                
        self.update_positions()
                
        self.deltas = OrderedDict( 
            { k: float(self.positions[ k ][ 'positionAmt' ]) for k in self.futures.keys()}
        )
        self.deltas[ BTC_SYMBOL ] = self.usdtbalance         
        
        
    def update_positions( self ):

        self.positions  = OrderedDict( { f: {
            'size':         0,
            'positionAmt':      0,
            'indexPrice':   None,
            'markPrice':    None
        } for f in self.futures.keys() } )
        positions       = self.client.fapiPrivateGetPositionRisk()
        #print('lala')
        #print(positions)
        
        for pos in positions:
            if 'BTC/USDT' in self.futures:
                self.positions[ 'BTC/USDT'] = pos
        
    
    def update_timeseries( self ):
        
        if self.monitor:
            return None
        
        for t in range( NLAGS, 0, -1 ):
            self.ts[ t ]    = cp.deepcopy( self.ts[ t - 1 ] )
        
        spot                    = self.get_spot()
        self.ts[ 0 ][ BTC_SYMBOL ]    = spot
        
        for c in self.futures.keys():
            
            bbo = self.get_bbo( c )
            bid = bbo[ 'bid' ]
            ask = bbo[ 'ask' ]

            if not bid is None and not ask is None:
                mid = 0.5 * ( bbo[ 'bid' ] + bbo[ 'ask' ] )
            else:
                continue
            self.ts[ 0 ][ c ]               = mid
                
        self.ts[ 0 ][ 'timestamp' ]  = datetime.utcnow()

        
    def update_vols( self ):
        
        if self.monitor:
            return None
        
        w   = EWMA_WGT_COV
        ts  = self.ts
        
        t   = [ ts[ i ][ 'timestamp' ] for i in range( NLAGS + 1 ) ]
        p   = { c: None for c in self.vols.keys() }
        for c in ts[ 0 ].keys():
            p[ c ] = [ ts[ i ][ c ] for i in range( NLAGS + 1 ) ]
        
        if any( x is None for x in t ):
            return None
        for c in self.vols.keys():
            if any( x is None for x in p[ c ] ):
                return None
        
        NSECS   = SECONDS_IN_YEAR
        cov_cap = COV_RETURN_CAP / NSECS
        
        for s in self.vols.keys():
            
            x   = p[ s ]            
            dx  = x[ 0 ] / x[ 1 ] - 1
            dt  = ( t[ 0 ] - t[ 1 ] ).total_seconds()
            v   = min( dx ** 2 / dt, cov_cap ) * NSECS
            v   = w * v + ( 1 - w ) * self.vols[ s ] ** 2
            
            self.vols[ s ] = math.sqrt( v )
                            
        
if __name__ == '__main__':
    
    try:
        mmbot = MarketMaker( monitor = args.monitor, output = args.output )
        mmbot.run()
    except( KeyboardInterrupt, SystemExit ):
        print( "Cancelling open orders" )
        mmbot.cancelall()
        sys.exit()
    except:
        print( traceback.format_exc())
        if args.restart:
            mmbot.restart()
        
