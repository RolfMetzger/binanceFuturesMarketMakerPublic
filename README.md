Binance Futures Market Maker, by Jarett Dunn


# Publicity


I won the recent BNB giveaway for spot + futures using this market maker. I traded more than 2 BTC in <2 hours with a balance of about $40. I even turned a 1.5% returns on equity trading BTCUSD futures.


https://medium.com/@jarettdunn/binance-hacked-two-trading-competitions-my-share-of-40k-and-10k-bnb-prize-in-jare-cloud-c9dca20f0ac6



# Edits


At the top of the market_maker.py file is a pair setting. If you copy this file, you can run other pairs, like BCH/USDT. Save this file something different and run python market_maker.py for your BTC/USDT and for your other file for other coins.


To enter more orders more often, reduce RISK_CHARGE_VOL. When it's higher, it's anticipating more volatility in the market and the difference between order entries will be more distance, allowing you to profit from more of the higher differences in assets being considered.



Support this open-source project organically, without subscription! Sign up to Binance here using this referral link: https://www.binance.com/en/register?ref=VZJQV7PR and for futures here: https://www.binance.com/en/futures/ref/neomenia


Support this open-source project! $1 or $5 a month from a crowd adds up! https://github.com/sponsors/dunncreativess


https://imgur.com/FxgIqrY


EDIT: GitHub repo has been made private. Subscribe to GitHub Sponsors $100 tier for access!


EDIT: Opensourced again!


Binance WAS running a competition as we speak for 50k BNB — 40k for spot/margin, 10k for futures — if you trade more than 1 BTC in notional value in either bucket! Be prepared for the next competition with my private market making repository for Binance futures and margin! IOTX Binance trading competition just concluded with another $90 000 to be won!


https://imgur.com/b97oLP9


https://drive.google.com/file/d/198dAxfEfmPxxe696t7wnsN3ijBLods4h/view?usp=sharing


Lucky for me I already have a Binance futures market maker — and with a wee bit of edits to the code, it ran fine on margin 5x, too! I ran the futures on 100x and orders of 0.002 BTC and it won the futures contest in ~1hr.


Check g543 for the total. Woo!


I was +0.5% for most of my bot run on futures, ended at -1% on equity.


I was down about 21% — of my whopping $46 — on margin.


https://imgur.com/undefined


Win Binance trading competitions! I won my share of 10k BNB for futures trading and 40k BNB for spot/margin trading 1+ BTC in <3 hours in this recent Binance giveaway: https://www.binance.com/en/support/articles/360040070651


Setup:


1. Clone or download repo
2. cd into dir
3. python3 setup.py install


For our competition run, Coindex Labs is optimizing these input variables using our proprietary AI. Note that the defaults here will probably lose funds, they're not optimized or recommended.



binApi is your api key (futures enabled...)


binSecret is your api secret...


5. python3 market_maker.py
6. fun and profit!


https://hackernoon.com/porting-a-bot-to-binance-futures-market-making-competition-6v6a31qh


Track our bot's delta in real-time (after the test bot's run is complete) here: http://coindexbot.duckdns.org


Original README.md as follows:


Sample market maker bot
===

Strategy
---

The bot layers bids and offers around the market mid, which it attempts to calculate from the order book. The spread between quoted bids and offers is determined by a user-set risk charge on volatility. Volatility is estimated by an EWMA (Exponentially Weighted Moving Average Process) with frequency and parameters that may also be set by the user.

Set up
---

This bot requires python3 and the [Deribit api wrapper](https://pypi.org/project/deribit_api/).

To set up the bot, edit the `KEY` and `SECRET` variables in the code to your credentials. You can obtain those from the [Deribit account](https://www.deribit.com/main#/account?scrollTo=api).

To start the bot, run `python3 market_maker.py`.

Disclaimer
---

Different market conditions will produce different results. This code is for sample purposes only. It comes as is, with no warranty or guarantee of performance.
